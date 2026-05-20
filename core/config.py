"""
Caz Configuration Module

Handles loading, validating, and accessing configuration.
Uses layered approach: defaults → config.toml → env vars → CLI flags.

Teaching note: This uses Python's built-in tomllib (3.11+) so we need
zero external dependencies for config parsing.
"""

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# --- Defaults ---
# These are the hardcoded fallbacks if config.toml is missing or incomplete.
# Every setting MUST have a safe default.

DEFAULTS = {
    "caz": {
        "name": "Caz",
        "teaching_mode": True,
        "log_level": "info",
    },
    "models": {
        "primary": "olmo2:7b",
        "heavy": "olmo2:13b",
        "provider": "ollama",
        "energy_mode": "efficient",
        "remote": {
            "endpoint": "",
            "model": "",
        },
    },
    "memory": {
        "enabled": True,
        "db_path": "data/memory.db",
        "max_conversations": 1000,
    },
    "permissions": {
        "allow_network": False,
        "allow_file_read": [],
        "allow_file_write": [],
        "allow_shell": False,
    },
    "logging": {
        "directory": "logs",
        "audit_enabled": True,
        "retain_days": 90,
    },
    "ethics": {
        "guardrails_enabled": True,
        "admit_uncertainty": True,
        "cite_sources": True,
    },
}

# --- Allowed values for validation ---
VALID_LOG_LEVELS = {"debug", "info", "warn", "error"}
VALID_ENERGY_MODES = {"efficient", "balanced", "performance"}
VALID_PROVIDERS = {"ollama", "remote"}


def _deep_merge(base: dict, override: dict) -> dict:
    """
    Recursively merge override dict into base dict.
    Override values win. Base provides defaults for missing keys.

    Teaching note: This is how layered config works — we start with
    defaults and layer user settings on top, key by key.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _apply_env_overrides(config: dict) -> dict:
    """
    Apply environment variable overrides.

    Convention: CAZ_SECTION_KEY (uppercase, underscore-separated)
    Example: CAZ_MODELS_PROVIDER=remote overrides [models] provider

    Security note: API keys are ONLY read from env vars, never config files.
    This prevents accidental commits of secrets to Git.
    """
    env_mappings = {
        "CAZ_LOG_LEVEL": ("caz", "log_level"),
        "CAZ_MODELS_PROVIDER": ("models", "provider"),
        "CAZ_MODELS_PRIMARY": ("models", "primary"),
        "CAZ_ENERGY_MODE": ("models", "energy_mode"),
        "CAZ_API_KEY": None,  # Handled separately, never stored in config dict
    }

    for env_var, path in env_mappings.items():
        value = os.environ.get(env_var)
        if value is not None and path is not None:
            section, key = path
            if section in config:
                config[section][key] = value

    return config


def validate(config: dict) -> list[str]:
    """
    Validate configuration values. Returns list of error messages.
    Empty list means config is valid.

    Security note: We validate EVERYTHING. Unexpected values are rejected,
    not silently accepted. This prevents injection via config manipulation.
    """
    errors = []

    # Validate log level
    log_level = config.get("caz", {}).get("log_level", "")
    if log_level not in VALID_LOG_LEVELS:
        errors.append(
            f"Invalid log_level '{log_level}'. Must be one of: {VALID_LOG_LEVELS}"
        )

    # Validate energy mode
    energy_mode = config.get("models", {}).get("energy_mode", "")
    if energy_mode not in VALID_ENERGY_MODES:
        errors.append(
            f"Invalid energy_mode '{energy_mode}'. Must be one of: {VALID_ENERGY_MODES}"
        )

    # Validate provider
    provider = config.get("models", {}).get("provider", "")
    if provider not in VALID_PROVIDERS:
        errors.append(
            f"Invalid provider '{provider}'. Must be one of: {VALID_PROVIDERS}"
        )

    # Validate permissions are correct types
    perms = config.get("permissions", {})
    if not isinstance(perms.get("allow_file_read", []), list):
        errors.append("permissions.allow_file_read must be a list")
    if not isinstance(perms.get("allow_file_write", []), list):
        errors.append("permissions.allow_file_write must be a list")
    if not isinstance(perms.get("allow_network", False), bool):
        errors.append("permissions.allow_network must be true or false")
    if not isinstance(perms.get("allow_shell", False), bool):
        errors.append("permissions.allow_shell must be true or false")

    # Validate retain_days is positive
    retain_days = config.get("logging", {}).get("retain_days", 90)
    if not isinstance(retain_days, int) or retain_days < 1:
        errors.append("logging.retain_days must be a positive integer")

    return errors


def load(config_path: Optional[Path] = None) -> dict:
    """
    Load configuration with full layering:
    1. Start with defaults
    2. Merge config.toml on top (if it exists)
    3. Apply environment variable overrides
    4. Validate everything

    Returns the final merged config dict.
    Raises ValueError if validation fails.
    """
    # Start with safe defaults
    config = DEFAULTS.copy()

    # Layer 2: Load config file if it exists
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.toml"

    if config_path.exists():
        with open(config_path, "rb") as f:
            file_config = tomllib.load(f)
        config = _deep_merge(config, file_config)

    # Layer 3: Environment variable overrides
    config = _apply_env_overrides(config)

    # Validate
    errors = validate(config)
    if errors:
        raise ValueError(
            "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    return config


def get_api_key() -> Optional[str]:
    """
    Retrieve API key from environment variable ONLY.

    Security note: This is intentionally separate from the config dict.
    API keys are never stored in config files or logged.
    """
    return os.environ.get("CAZ_API_KEY")
