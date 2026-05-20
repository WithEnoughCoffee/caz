"""
Caz — The Engine (Orchestrator)

This is the brain of Caz. It receives messages, decides what to do,
and coordinates between models, plugins, and memory.

Teaching note: This is the "controller" in MVC-like architecture.
It doesn't DO the work — it routes and coordinates.
"""

import sys
from pathlib import Path
from typing import Optional

from core.config import load as load_config
from core.logging import CazLogger
from core.model_client import ModelClient
from core.permissions import PermissionManager
from core.web_search import WebSearch, format_search_results


class Engine:
    """
    Central orchestrator for Caz.

    Coordinates between:
    - Config (what settings are active)
    - Permissions (what Caz is allowed to do)
    - Models (where to send messages for processing)
    - Logging (record everything for transparency)
    - Memory (what to remember) [Phase 2]

    Teaching note: Keeping the engine thin and delegating to
    specialized modules makes the code easier to understand
    and extend. Each piece has one job.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize Caz engine with configuration."""
        self.config = load_config(config_path)
        self.permissions = PermissionManager(self.config)
        self.logger = CazLogger(self.config)
        self.model = ModelClient(self.config)
        self.search = WebSearch()
        self._network_granted = False
        self._pending_search: Optional[str] = None
        self.teaching_mode = self.config["caz"].get(
            "teaching_mode", True
        )

        # Log startup
        self.logger.system(
            "Engine initialized",
            model=self.model.model,
            model_configured=self.model.is_configured,
            teaching_mode=self.teaching_mode,
        )

    def process_message(self, message: str) -> str:
        """
        Process a user message and return Caz's response.

        Routes to built-in commands first, then to the model.

        Parameters:
            message: The user's input text.

        Returns:
            Caz's response as a string.
        """
        # Log user message
        self.logger.interaction("user", message)

        # Built-in commands (don't need a model)
        if message.lower() in ("quit", "exit", "bye"):
            return "__EXIT__"

        if message.lower() in ("help", "?"):
            response = self._help_text()
            self.logger.interaction("caz", response)
            return response

        if message.lower() == "permissions":
            response = self._show_permissions()
            self.logger.interaction("caz", response)
            return response

        if message.lower() == "config":
            response = self._show_config()
            self.logger.interaction("caz", response)
            return response

        if message.lower() == "clear":
            self.model.clear_history()
            response = "🌿 Memory cleared — fresh conversation, fresh soil."
            self.logger.interaction("caz", response)
            return response

        # Search command: /search <query> or "search for <query>"
        search_query = self._extract_search_query(message)
        if search_query:
            response = self._handle_search(search_query)
            self.logger.interaction("caz", response)
            return response

        # "yes" in response to a search suggestion
        if message.lower() in ("yes", "y", "yeah", "sure", "do it"):
            if self._pending_search:
                self.grant_network_permission()
                response = self._execute_search(self._pending_search)
                self._pending_search = None
                self.logger.interaction("caz", response)
                return response

        # Route to model
        return self._ask_model(message)

    def _ask_model(self, message: str) -> str:
        """
        Send a message to the configured model and return response.

        If no model is configured (remote without API key),
        returns a helpful message explaining how to set up.
        """
        if not self.model.is_configured:
            return (
                "🌱 My mind hasn't fully awakened yet — I need an API key "
                "to think.\n\n"
                "Set it with:\n"
                "  export CAZ_API_KEY='your-api-key'\n\n"
                "Or switch to local Ollama (free, no key needed):\n"
                "  Set provider = \"ollama\" in config.toml"
            )

        try:
            result = self.model.chat(message)

            # Log the response with metadata
            self.logger.interaction(
                "caz",
                result["content"],
                model=result["model"],
                tokens=result["tokens"],
                duration_ms=result["duration_ms"],
            )

            # Log energy/performance data
            self.logger.system(
                "Model response",
                level="debug",
                model=result["model"],
                tokens=result["tokens"],
                duration_ms=result["duration_ms"],
            )

            return result["content"]

        except ConnectionError as e:
            error_msg = f"🌧️ Couldn't reach the model: {e}"
            self.logger.error("Model connection failed", error=str(e))
            return error_msg

        except Exception as e:
            error_msg = f"🌧️ Something unexpected happened: {e}"
            self.logger.error("Unexpected error", error=str(e))
            return error_msg

    def shutdown(self) -> None:
        """Clean shutdown — close logs, save state."""
        self.logger.system("Engine shutting down")
        self.logger.close()

    def _help_text(self) -> str:
        """Return help text with available commands."""
        return """
🌱 Caz — Available Commands

  help             Show this message
  /search <query>  Search the web (requires permission)
  permissions      View current permission grants
  config           View active configuration
  clear            Reset conversation (fresh soil)
  quit/exit        Leave the greenhouse

Just type naturally to chat! Say "search for ..." to look things up.
Caz uses OLMo 2 (truly open, Apache 2.0) running locally via Ollama.
        """.strip()

    def _show_permissions(self) -> str:
        """Show current permission state."""
        grants = self.permissions.get_session_grants()
        if not grants:
            lines = [
                "🔐 Permissions (this session):",
                "   No session grants active.",
                "   Config pre-approvals:",
            ]
            perms = self.config.get("permissions", {})
            lines.append(
                f"     Network: {'✓' if perms.get('allow_network') else '✗'}"
            )
            lines.append(
                f"     Shell:   {'✓' if perms.get('allow_shell') else '✗'}"
            )
            lines.append(
                f"     Read:    {perms.get('allow_file_read', []) or 'none'}"
            )
            lines.append(
                f"     Write:   {perms.get('allow_file_write', []) or 'none'}"
            )
            return "\n".join(lines)
        else:
            lines = ["🔐 Session grants:"]
            for g in grants:
                lines.append(
                    f"   ✓ {g.permission_type.value}: {g.resource}"
                )
            return "\n".join(lines)

    def _show_config(self) -> str:
        """Show active configuration (safe values only)."""
        c = self.config
        return f"""
⚙️  Active Configuration:
   Model (primary): {c['models']['primary']}
   Model (heavy):   {c['models']['heavy']}
   Provider:        {c['models']['provider']}
   Energy mode:     {c['models']['energy_mode']}
   Teaching mode:   {c['caz']['teaching_mode']}
   Memory:          {c['memory']['enabled']}
   Guardrails:      {c['ethics']['guardrails_enabled']}
   Admit uncertainty: {c['ethics']['admit_uncertainty']}
   Cite sources:    {c['ethics']['cite_sources']}
   Network (this session): {'✓ granted' if self._network_granted else '✗ not granted'}
        """.strip()

    # --- Search Methods ---

    def _extract_search_query(self, message: str) -> Optional[str]:
        """
        Check if the user is asking to search.

        Recognizes:
          /search python asyncio
          search for python asyncio
          look up python asyncio
          google python asyncio
        """
        lower = message.lower().strip()

        # /search command
        if lower.startswith("/search "):
            return message[8:].strip()

        # Natural language triggers
        prefixes = [
            "search for ",
            "search ",
            "look up ",
            "google ",
            "find me info on ",
            "find info on ",
        ]
        for prefix in prefixes:
            if lower.startswith(prefix):
                return message[len(prefix):].strip()

        return None

    def _handle_search(self, query: str) -> str:
        """
        Execute a web search with permission checking.

        Flow:
        1. Check if network permission is granted this session
        2. If not → return a permission request (user must confirm)
        3. If yes → search, format results, log the action
        """
        if not self._network_granted:
            # Store the pending search so we can execute after "yes"
            self._pending_search = query
            self.logger.audit(
                "network_permission_requested",
                reason="web_search",
                query=query,
            )
            return (
                f"🔐 I'd like to search the web for: \"{query}\"\n\n"
                "This requires network access (currently denied by default).\n"
                "Grant network permission for this session?\n\n"
                "  Type 'yes' to allow  |  anything else to deny"
            )

        # Permission granted — execute search
        return self._execute_search(query)

    def _execute_search(self, query: str) -> str:
        """Actually perform the search and return formatted results."""
        self.logger.audit(
            "web_search_executed",
            query=query,
        )
        self.logger.system(
            "Executing web search",
            query=query,
        )

        try:
            results = self.search.query(query)
            formatted = format_search_results(results)
            self.logger.system(
                "Search completed",
                query=query,
                result_count=len(results),
            )
            return formatted

        except ConnectionError as e:
            self.logger.error("Search failed", error=str(e))
            return f"🌧️ Search failed: {e}"
        except ValueError as e:
            return f"🌧️ Invalid search: {e}"

    def grant_network_permission(self) -> str:
        """Grant network access for this session."""
        self._network_granted = True
        self.logger.audit(
            "network_permission_granted",
            scope="session",
        )
        return "✓ Network access granted for this session."
