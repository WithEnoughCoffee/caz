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


# System prompt for synthesizing search results
SEARCH_SYNTHESIS_PROMPT = """You are Caz, a knowledgeable AI assistant in an enchanted greenhouse. \
You've just searched the web for the user. Your job is to:

1. Give a CONCISE answer (3-5 sentences max) synthesized from the search results
2. Cite sources using [1], [2], etc. matching the numbered results
3. Be honest — if the results don't fully answer the question, say so briefly
4. Lead with the direct answer. No preamble.
5. Keep your tone warm and slightly whimsical but BRIEF

RULES:
- Never summarize each source individually. Synthesize into ONE coherent answer.
- Never make up information that isn't in the search results.
- Never pad the response. Short and accurate beats long and rambly.
- If results are irrelevant to what the user actually wanted, say so."""


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
            return self._enrich_search_query(message[8:].strip())

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
                return self._enrich_search_query(
                    message[len(prefix):].strip()
                )

        return None

    def _enrich_search_query(self, query: str) -> str:
        """
        Add conversation context to a search query when it's vague.

        Teaching note: If the user says "search for the weather today"
        after asking about Hawaii, the query alone is too vague.
        We look at the last few messages for important context
        (nouns, topics) that should be included in the search.

        This is a simple heuristic — not full NLP — but it catches
        the most common case: the user refers to something they
        just mentioned.
        """
        # If the query already seems specific (has proper nouns,
        # is long enough), use it as-is
        if len(query.split()) >= 5:
            return query

        # Look at recent conversation history for context
        history = self.model._history
        if not history:
            return query

        # Get the last few user messages for context
        recent_user_msgs = [
            msg["content"] for msg in history[-6:]
            if msg["role"] == "user"
        ]

        if not recent_user_msgs:
            return query

        # Simple approach: ask the model to build a better query
        # But that's slow. Instead, just prepend the topic from
        # the most recent exchange if the query looks incomplete.
        # A query is "incomplete" if it's very short or uses
        # demonstratives (this, that, it, the) without a clear subject.
        vague_indicators = [
            "the ", "that ", "this ", "it ", "those ",
            "today", "now", "current", "latest",
        ]

        is_vague = any(
            query.lower().startswith(v) or query.lower() == v.strip()
            for v in vague_indicators
        ) and len(query.split()) < 5

        if is_vague and recent_user_msgs:
            # Extract likely topic from recent user message
            last_msg = recent_user_msgs[-1]
            # Combine: use the last user message topic + current query
            enriched = f"{last_msg} {query}"
            # Cap at reasonable length
            return enriched[:200]

        return query

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
        """
        Search the web and synthesize results through the model.

        Flow:
        1. Search DuckDuckGo for raw results
        2. Feed results into OLMo as context
        3. OLMo generates a conversational answer with citations
        4. Return the synthesized response

        Teaching note: This is "Retrieval-Augmented Generation" (RAG)
        in its simplest form. Instead of the model hallucinating facts,
        we give it real search results and ask it to synthesize an
        answer from them. The model's job becomes summarization and
        explanation — things it's good at — rather than fact recall.
        """
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
            self.logger.system(
                "Search completed",
                query=query,
                result_count=len(results),
            )

            if not results:
                return "🔍 I searched but found no results. Try rephrasing?"

            # Build context from search results for the model
            context = self._build_search_context(query, results)

            # Ask the model to synthesize an answer
            try:
                synthesis = self.model.chat(
                    context,
                    system_prompt=SEARCH_SYNTHESIS_PROMPT,
                )
                response = synthesis["content"]

                # Append source list so user can verify
                source_list = "\n\n📚 Sources:\n"
                for i, r in enumerate(results, 1):
                    source_list += f"  [{i}] {r.title}\n"
                    source_list += f"      {r.url}\n"
                source_list += "\n  ⚠️  Verify claims against sources — I may misinterpret."

                full_response = response + source_list

                self.logger.interaction(
                    "caz",
                    full_response,
                    model=synthesis.get("model"),
                    tokens=synthesis.get("tokens"),
                    duration_ms=synthesis.get("duration_ms"),
                )
                return full_response

            except ConnectionError:
                # Model unavailable — fall back to raw results
                formatted = format_search_results(results)
                return formatted

        except ConnectionError as e:
            self.logger.error("Search failed", error=str(e))
            return f"🌧️ Search failed: {e}"
        except ValueError as e:
            return f"🌧️ Invalid search: {e}"

    def _build_search_context(self, query: str, results: list) -> str:
        """
        Format search results as context for the model.

        Teaching note: How you format context for a model matters.
        Clear structure helps the model understand what's a source
        vs what's the question. We number sources so the model
        can reference them as [1], [2], etc.
        """
        context = f"The user asked: \"{query}\"\n\n"
        context += "Here are search results from the web:\n\n"

        for i, r in enumerate(results, 1):
            context += f"[{i}] {r.title}\n"
            context += f"    URL: {r.url}\n"
            if r.snippet:
                context += f"    Content: {r.snippet}\n"
            context += "\n"

        context += (
            "Based on these search results, provide a helpful answer. "
            "Cite sources using [1], [2], etc. "
            "If the results don't fully answer the question, say so."
        )
        return context

    def grant_network_permission(self) -> str:
        """Grant network access for this session."""
        self._network_granted = True
        self.logger.audit(
            "network_permission_granted",
            scope="session",
        )
        return "✓ Network access granted for this session."
