"""
Tests for Caz's logging framework.

Verifies that:
- Log files are created in the correct directory
- Interaction logs capture conversation turns with metadata
- Audit logs record security events
- System logs capture diagnostics at proper levels
- JSONL format is valid (one JSON object per line)
- Closing the logger flushes and closes files properly
"""

import json
import tempfile
from pathlib import Path

from core.logging import CazLogger


def make_test_config(tmp_dir: str) -> dict:
    """Create a test config pointing logs to a temp directory."""
    return {
        "caz": {"log_level": "debug"},
        "logging": {
            "directory": tmp_dir,
            "audit_enabled": True,
        },
    }


def test_log_directory_created():
    """Log directory is created if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmp:
        log_dir = str(Path(tmp) / "nested" / "logs")
        config = make_test_config(log_dir)
        logger = CazLogger(config)
        assert Path(log_dir).exists()
        logger.close()


def test_interaction_log_records_user_message():
    """User messages are logged with role and content."""
    with tempfile.TemporaryDirectory() as tmp:
        config = make_test_config(tmp)
        logger = CazLogger(config)

        logger.interaction("user", "What is recursion?")
        logger.close()

        log_file = Path(tmp) / "interactions.jsonl"
        assert log_file.exists()

        entries = _read_jsonl(log_file)
        assert len(entries) == 1
        assert entries[0]["role"] == "user"
        assert entries[0]["content"] == "What is recursion?"
        assert entries[0]["event"] == "conversation_turn"
        assert "timestamp" in entries[0]


def test_interaction_log_records_caz_response_with_metadata():
    """Caz responses include model, tokens, and duration."""
    with tempfile.TemporaryDirectory() as tmp:
        config = make_test_config(tmp)
        logger = CazLogger(config)

        logger.interaction(
            "caz",
            "Recursion is when a function calls itself.",
            model="olmo2:7b",
            tokens=42,
            duration_ms=312.5,
        )
        logger.close()

        entries = _read_jsonl(Path(tmp) / "interactions.jsonl")
        assert entries[0]["role"] == "caz"
        assert entries[0]["model"] == "olmo2:7b"
        assert entries[0]["tokens"] == 42
        assert entries[0]["duration_ms"] == 312.5


def test_audit_log_records_security_events():
    """Security events are logged with details."""
    with tempfile.TemporaryDirectory() as tmp:
        config = make_test_config(tmp)
        logger = CazLogger(config)

        logger.audit(
            "permission_granted",
            resource="/tmp/test.txt",
            action="read",
            scope="session",
        )
        logger.close()

        entries = _read_jsonl(Path(tmp) / "audit.jsonl")
        assert len(entries) == 1
        assert entries[0]["event"] == "permission_granted"
        assert entries[0]["resource"] == "/tmp/test.txt"
        assert entries[0]["action"] == "read"
        assert entries[0]["scope"] == "session"


def test_audit_log_respects_disabled_flag():
    """Audit logging can be disabled via config."""
    with tempfile.TemporaryDirectory() as tmp:
        config = make_test_config(tmp)
        config["logging"]["audit_enabled"] = False
        logger = CazLogger(config)

        logger.audit("permission_granted", resource="/test")
        logger.close()

        entries = _read_jsonl(Path(tmp) / "audit.jsonl")
        assert len(entries) == 0


def test_system_log_records_diagnostics():
    """System events are logged with level."""
    with tempfile.TemporaryDirectory() as tmp:
        config = make_test_config(tmp)
        logger = CazLogger(config)

        logger.system("Engine initialized", component="engine")
        logger.error("Model connection failed", reason="timeout")
        logger.warning("High memory usage", percent=87)
        logger.debug("Token count", tokens=150)
        logger.close()

        entries = _read_jsonl(Path(tmp) / "system.jsonl")
        assert len(entries) == 4
        assert entries[0]["level"] == "info"
        assert entries[0]["event"] == "Engine initialized"
        assert entries[1]["level"] == "error"
        assert entries[2]["level"] == "warning"
        assert entries[3]["level"] == "debug"


def test_jsonl_format_valid():
    """Each line is valid independent JSON."""
    with tempfile.TemporaryDirectory() as tmp:
        config = make_test_config(tmp)
        logger = CazLogger(config)

        logger.interaction("user", "Hello")
        logger.interaction("caz", "Hi there!")
        logger.interaction("user", "Bye")
        logger.close()

        log_file = Path(tmp) / "interactions.jsonl"
        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 3
        # Each line must be valid JSON
        for line in lines:
            parsed = json.loads(line.strip())
            assert isinstance(parsed, dict)


def test_unicode_content_preserved():
    """Unicode in messages is preserved correctly."""
    with tempfile.TemporaryDirectory() as tmp:
        config = make_test_config(tmp)
        logger = CazLogger(config)

        logger.interaction("user", "What about 日本語? 🌱")
        logger.close()

        entries = _read_jsonl(Path(tmp) / "interactions.jsonl")
        assert entries[0]["content"] == "What about 日本語? 🌱"


def test_multiple_entries_appended():
    """Multiple log entries append, not overwrite."""
    with tempfile.TemporaryDirectory() as tmp:
        config = make_test_config(tmp)

        # First session
        logger1 = CazLogger(config)
        logger1.interaction("user", "First session")
        logger1.close()

        # Second session
        logger2 = CazLogger(config)
        logger2.interaction("user", "Second session")
        logger2.close()

        entries = _read_jsonl(Path(tmp) / "interactions.jsonl")
        assert len(entries) == 2
        assert entries[0]["content"] == "First session"
        assert entries[1]["content"] == "Second session"


# --- Helper ---

def _read_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file and return list of parsed dicts."""
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


if __name__ == "__main__":
    test_log_directory_created()
    test_interaction_log_records_user_message()
    test_interaction_log_records_caz_response_with_metadata()
    test_audit_log_records_security_events()
    test_audit_log_respects_disabled_flag()
    test_system_log_records_diagnostics()
    test_jsonl_format_valid()
    test_unicode_content_preserved()
    test_multiple_entries_appended()
    print("✅ All logging tests passed!")
