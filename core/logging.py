"""
Caz Logging Framework

Provides structured logging for interactions, security audits,
and system diagnostics. Zero external dependencies — uses only
Python's built-in `json` and `pathlib`.

Teaching note: "Structured logging" means each log entry is a
dictionary/JSON object with consistent fields, not just a plain
text string. This makes logs:
  - Searchable (grep for "event": "permission_granted")
  - Parseable (tools can read JSON automatically)
  - Contextual (every entry carries its own metadata)

We write logs in JSONL format (one JSON object per line) because:
  - Easy to append (just add a line)
  - Easy to parse (read line by line)
  - Easy to grep/search
  - Never corrupts the whole file (one bad line ≠ broken file)

Design choice — zero dependencies:
  Python's `json` module + file I/O gives us everything we need
  for structured logging. No need for structlog or loguru. This
  keeps Caz's dependency tree at zero for the core framework,
  which means faster installs, fewer supply-chain risks, and
  one less thing that can break.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class CazLogger:
    """
    Caz's logging interface — zero external dependencies.

    Provides three purpose-specific logging methods:
    - interaction() — conversation turns
    - audit() — security events
    - system() — technical diagnostics

    Teaching note: This is the "Facade" pattern — it provides
    a simple interface to the logging subsystem. Users of this
    class just call logger.interaction("user", "hello") and
    the right file gets the right structured JSON entry.

    Usage:
        logger = CazLogger(config)
        logger.interaction("user", "What is recursion?")
        logger.interaction("caz", "Recursion is when...")
        logger.audit("permission_granted", resource="/tmp/file")
        logger.system("Engine initialized successfully")
    """

    def __init__(self, config: dict):
        """
        Initialize Caz's logger.

        Parameters:
            config: The full Caz config dict.
        """
        log_config = config.get("logging", {})
        self.log_dir = Path(log_config.get("directory", "logs"))
        self.audit_enabled = log_config.get("audit_enabled", True)

        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Open log files for writing (append mode)
        self._interaction_file = open(
            self.log_dir / "interactions.jsonl", "a", encoding="utf-8"
        )
        self._audit_file = open(
            self.log_dir / "audit.jsonl", "a", encoding="utf-8"
        )
        self._system_file = open(
            self.log_dir / "system.jsonl", "a", encoding="utf-8"
        )

    def interaction(
        self,
        role: str,
        content: str,
        model: Optional[str] = None,
        tokens: Optional[int] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """
        Log a conversation turn.

        Parameters:
            role: "user" or "caz"
            content: The message text
            model: Which model generated the response (if caz)
            tokens: Token count (for efficiency tracking)
            duration_ms: Response time in milliseconds

        Teaching note: We log both sides of the conversation.
        This creates a complete record you can review later
        to understand how Caz behaves and improve it.
        """
        entry = {
            "event": "conversation_turn",
            "role": role,
            "content": content,
        }
        if model:
            entry["model"] = model
        if tokens:
            entry["tokens"] = tokens
        if duration_ms:
            entry["duration_ms"] = duration_ms

        # Write to file
        self._write_jsonl(self._interaction_file, entry)

    def audit(self, event: str, **details) -> None:
        """
        Log a security-relevant event.

        Parameters:
            event: What happened (e.g., "permission_granted",
                   "permission_denied", "config_loaded")
            **details: Any additional context as keyword arguments

        Teaching note: Audit logs are your security paper trail.
        If something goes wrong, these tell you exactly what
        was allowed, denied, and when. Never skip audit logging.
        """
        if not self.audit_enabled:
            return

        entry = {"event": event, **details}
        self._write_jsonl(self._audit_file, entry)

    def system(
        self, message: str, level: str = "info", **details
    ) -> None:
        """
        Log a system/diagnostic message.

        Parameters:
            message: What happened
            level: Severity (debug, info, warning, error)
            **details: Additional context

        Teaching note: System logs help you troubleshoot.
        When the model won't connect or a file can't be read,
        these logs tell you why.
        """
        entry = {
            "event": message,
            "level": level,
            **details,
        }
        self._write_jsonl(self._system_file, entry)

    def error(self, message: str, **details) -> None:
        """Convenience: log an error."""
        self.system(message, level="error", **details)

    def warning(self, message: str, **details) -> None:
        """Convenience: log a warning."""
        self.system(message, level="warning", **details)

    def debug(self, message: str, **details) -> None:
        """Convenience: log a debug message."""
        self.system(message, level="debug", **details)

    def _write_jsonl(self, file, entry: dict) -> None:
        """
        Write a single JSON entry to a .jsonl file.

        Teaching note: JSONL (JSON Lines) is one JSON object per
        line. It's the standard for log files because:
        - Easy to append (just add a line)
        - Easy to parse (read line by line)
        - Easy to grep/search
        - Never corrupts the whole file (one bad line ≠ broken file)
        """
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        file.flush()  # Write immediately, don't buffer

    def close(self) -> None:
        """Close all log files cleanly."""
        self._interaction_file.close()
        self._audit_file.close()
        self._system_file.close()
