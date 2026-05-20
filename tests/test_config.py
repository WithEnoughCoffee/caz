"""
Tests for the configuration module.

Teaching note: We test config loading because it's a security boundary.
Bad config should NEVER silently pass — it must fail loudly.
"""

import os
import tempfile
from pathlib import Path

# Add project root to path so we can import core
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import load, validate, _deep_merge, get_api_key


def test_defaults_load_without_config_file():
    """Config loads with safe defaults even if no config.toml exists."""
    fake_path = Path("/nonexistent/config.toml")
    config = load(config_path=fake_path)

    assert config["caz"]["name"] == "Caz"
    assert config["caz"]["teaching_mode"] is True
    assert config["models"]["primary"] == "olmo2:7b"
    assert config["permissions"]["allow_network"] is False
    assert config["permissions"]["allow_shell"] is False
    assert config["ethics"]["admit_uncertainty"] is True
    print("✓ Defaults load correctly without config file")


def test_config_file_overrides_defaults():
    """Values in config.toml override defaults."""
    toml_content = b"""
[caz]
teaching_mode = false
log_level = "debug"

[models]
primary = "olmo2:13b"
"""
    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
        f.write(toml_content)
        f.flush()
        config = load(config_path=Path(f.name))

    assert config["caz"]["teaching_mode"] is False
    assert config["caz"]["log_level"] == "debug"
    assert config["models"]["primary"] == "olmo2:13b"
    # Defaults still present for unspecified values
    assert config["permissions"]["allow_network"] is False
    print("✓ Config file correctly overrides defaults")


def test_validation_catches_bad_log_level():
    """Invalid log_level is rejected."""
    bad_config = {
        "caz": {"log_level": "verbose"},  # Not valid!
        "models": {"energy_mode": "efficient", "provider": "ollama"},
        "permissions": {
            "allow_network": False,
            "allow_file_read": [],
            "allow_file_write": [],
            "allow_shell": False,
        },
        "logging": {"retain_days": 90},
    }
    errors = validate(bad_config)
    assert any("log_level" in e for e in errors)
    print("✓ Validation catches invalid log_level")


def test_validation_catches_bad_energy_mode():
    """Invalid energy_mode is rejected."""
    bad_config = {
        "caz": {"log_level": "info"},
        "models": {"energy_mode": "turbo", "provider": "ollama"},
        "permissions": {
            "allow_network": False,
            "allow_file_read": [],
            "allow_file_write": [],
            "allow_shell": False,
        },
        "logging": {"retain_days": 90},
    }
    errors = validate(bad_config)
    assert any("energy_mode" in e for e in errors)
    print("✓ Validation catches invalid energy_mode")


def test_env_var_overrides():
    """Environment variables override config file values."""
    os.environ["CAZ_LOG_LEVEL"] = "debug"
    try:
        config = load(config_path=Path("/nonexistent/config.toml"))
        assert config["caz"]["log_level"] == "debug"
        print("✓ Environment variables override correctly")
    finally:
        del os.environ["CAZ_LOG_LEVEL"]


def test_api_key_only_from_env():
    """API key is only readable from environment, never config."""
    os.environ["CAZ_API_KEY"] = "test-secret-key"
    try:
        key = get_api_key()
        assert key == "test-secret-key"
        # Verify it's NOT in the config dict
        config = load(config_path=Path("/nonexistent/config.toml"))
        assert "CAZ_API_KEY" not in str(config)
        print("✓ API key isolated from config (env-only)")
    finally:
        del os.environ["CAZ_API_KEY"]


def test_deep_merge():
    """Deep merge layers override onto base correctly."""
    base = {"a": {"x": 1, "y": 2}, "b": 3}
    override = {"a": {"x": 99}, "c": 4}
    result = _deep_merge(base, override)

    assert result["a"]["x"] == 99   # Overridden
    assert result["a"]["y"] == 2    # Preserved from base
    assert result["b"] == 3         # Preserved from base
    assert result["c"] == 4         # Added from override
    print("✓ Deep merge works correctly")


if __name__ == "__main__":
    test_defaults_load_without_config_file()
    test_config_file_overrides_defaults()
    test_validation_catches_bad_log_level()
    test_validation_catches_bad_energy_mode()
    test_env_var_overrides()
    test_api_key_only_from_env()
    test_deep_merge()
    print("\n🌱 All config tests passed!")
