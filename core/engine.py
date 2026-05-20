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
from core.permissions import PermissionManager


class Engine:
    """
    Central orchestrator for Caz.

    Coordinates between:
    - Config (what settings are active)
    - Permissions (what Caz is allowed to do)
    - Models (where to send messages for processing)
    - Memory (what to remember)

    Teaching note: Keeping the engine thin and delegating to
    specialized modules makes the code easier to understand
    and extend. Each piece has one job.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize Caz engine with configuration."""
        self.config = load_config(config_path)
        self.permissions = PermissionManager(self.config)
        self.teaching_mode = self.config["caz"].get(
            "teaching_mode", True
        )

    def process_message(self, message: str) -> str:
        """
        Process a user message and return Caz's response.

        For Phase 1, this is a placeholder that echoes back.
        In Phase 2, this will route to local models via Ollama.

        Parameters:
            message: The user's input text.

        Returns:
            Caz's response as a string.
        """
        # Phase 1: Simple echo with personality
        # This will be replaced with model calls in Phase 2
        if message.lower() in ("quit", "exit", "bye"):
            return "__EXIT__"

        if message.lower() in ("help", "?"):
            return self._help_text()

        if message.lower() == "permissions":
            return self._show_permissions()

        if message.lower() == "config":
            return self._show_config()

        # Placeholder response until we connect a model
        return (
            "✨ I heard you! But my mind hasn't fully awakened yet — "
            "I'm waiting for my OLMo 2 brain to be connected in Phase 2. "
            "For now, I can show you `help`, `permissions`, or `config`."
        )

    def _help_text(self) -> str:
        """Return help text with available commands."""
        return """
🌱 Caz — Available Commands

  help         Show this message
  permissions  View current permission grants
  config       View active configuration
  quit/exit    Leave the greenhouse

More capabilities coming as Caz grows through each phase.
Currently: Phase 1 (Foundation)
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
        """.strip()
