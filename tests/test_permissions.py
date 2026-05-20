"""
Tests for the permission system.

Teaching note: Permission systems need thorough testing because
security bugs here have the highest impact. We test:
- Default deny behavior
- Config grants work
- Session grants are ephemeral
- Path traversal is blocked
- Denials are remembered (no re-prompting)
"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.permissions import (
    PermissionManager,
    PermissionRequest,
    PermissionType,
    PermissionDecision,
)


def make_config(
    allow_network=False,
    allow_shell=False,
    allow_file_read=None,
    allow_file_write=None,
):
    """Helper to build a config dict for testing."""
    return {
        "permissions": {
            "allow_network": allow_network,
            "allow_shell": allow_shell,
            "allow_file_read": allow_file_read or [],
            "allow_file_write": allow_file_write or [],
        }
    }


def test_default_deny():
    """Everything is denied by default with empty config."""
    pm = PermissionManager(make_config())

    request = PermissionRequest(
        permission_type=PermissionType.FILE_READ,
        resource="/some/path",
        reason="testing",
    )
    decision = pm.check(request)
    assert decision == PermissionDecision.DENIED_BY_DEFAULT
    print("✓ Default deny works — nothing allowed without explicit grant")


def test_config_grants_network():
    """Network access works when pre-approved in config."""
    pm = PermissionManager(make_config(allow_network=True))

    request = PermissionRequest(
        permission_type=PermissionType.NETWORK,
        resource="https://example.com",
        reason="testing",
    )
    decision = pm.check(request)
    assert decision == PermissionDecision.ALLOWED_BY_CONFIG
    print("✓ Config network grant works")


def test_config_grants_file_read():
    """File read works for pre-approved directories."""
    pm = PermissionManager(make_config(allow_file_read=["/tmp/allowed"]))

    # File within allowed directory — should pass
    request = PermissionRequest(
        permission_type=PermissionType.FILE_READ,
        resource="/tmp/allowed/subdir/file.txt",
        reason="testing",
    )
    decision = pm.check(request)
    assert decision == PermissionDecision.ALLOWED_BY_CONFIG

    # File OUTSIDE allowed directory — should deny
    request_outside = PermissionRequest(
        permission_type=PermissionType.FILE_READ,
        resource="/tmp/secrets/password.txt",
        reason="testing",
    )
    decision_outside = pm.check(request_outside)
    assert decision_outside == PermissionDecision.DENIED_BY_DEFAULT
    print("✓ File read grants are scoped to specified directories")


def test_path_traversal_blocked():
    """Path traversal attacks (../../) are blocked by resolve()."""
    pm = PermissionManager(make_config(allow_file_read=["/tmp/allowed"]))

    # Attempt traversal — trying to escape allowed directory
    request = PermissionRequest(
        permission_type=PermissionType.FILE_READ,
        resource="/tmp/allowed/../../etc/passwd",
        reason="sneaky traversal attempt",
    )
    decision = pm.check(request)
    assert decision == PermissionDecision.DENIED_BY_DEFAULT
    print("✓ Path traversal attacks are blocked")


def test_session_grant_via_prompt():
    """User can grant permission at runtime (session-scoped)."""
    pm = PermissionManager(make_config())

    request = PermissionRequest(
        permission_type=PermissionType.FILE_READ,
        resource="/tmp/somefile.txt",
        reason="Need to read your notes",
    )

    # Simulate user typing "y"
    with patch("builtins.input", return_value="y"):
        decision = pm.request_permission(request)

    assert decision == PermissionDecision.ALLOWED_BY_SESSION

    # Now it should be granted without re-prompting
    decision_again = pm.check(request)
    assert decision_again == PermissionDecision.ALLOWED_BY_SESSION
    print("✓ Session grants work and persist within session")


def test_denial_remembered():
    """Once denied, Caz doesn't ask again for same resource this session."""
    pm = PermissionManager(make_config())

    request = PermissionRequest(
        permission_type=PermissionType.FILE_READ,
        resource="/tmp/denied.txt",
        reason="testing",
    )

    # User denies
    with patch("builtins.input", return_value="n"):
        decision = pm.request_permission(request)
    assert decision == PermissionDecision.DENIED_BY_USER

    # Subsequent check returns denied without prompting
    decision_again = pm.check(request)
    assert decision_again == PermissionDecision.DENIED_BY_USER
    print("✓ Denials are remembered — no nagging")


def test_revoke_session_grant():
    """User can revoke a session grant."""
    pm = PermissionManager(make_config())

    request = PermissionRequest(
        permission_type=PermissionType.NETWORK,
        resource="https://api.example.com",
        reason="testing",
    )

    # Grant it
    with patch("builtins.input", return_value="y"):
        pm.request_permission(request)

    # Verify granted
    assert pm.check(request) == PermissionDecision.ALLOWED_BY_SESSION

    # Revoke it
    revoked = pm.revoke_session_grant(PermissionType.NETWORK, "https://api.example.com")
    assert revoked is True

    # Verify no longer granted
    assert pm.check(request) == PermissionDecision.DENIED_BY_DEFAULT
    print("✓ Session grants can be revoked")


def test_audit_log():
    """All permission checks are logged for transparency."""
    pm = PermissionManager(make_config(allow_network=True))

    request = PermissionRequest(
        permission_type=PermissionType.NETWORK,
        resource="https://example.com",
        reason="fetching data",
    )
    pm.check(request)

    log = pm.get_audit_log()
    assert len(log) == 1
    assert log[0]["type"] == "network"
    assert log[0]["decision"] == "allowed_by_config"
    print("✓ Audit log records all permission decisions")


def test_shell_denied_by_default():
    """Shell access is denied even if other permissions are granted."""
    pm = PermissionManager(make_config(allow_network=True, allow_file_read=["/tmp"]))

    request = PermissionRequest(
        permission_type=PermissionType.SHELL,
        resource="ls -la",
        reason="list files",
    )
    decision = pm.check(request)
    assert decision == PermissionDecision.DENIED_BY_DEFAULT
    print("✓ Shell access denied by default (highest risk)")


if __name__ == "__main__":
    test_default_deny()
    test_config_grants_network()
    test_config_grants_file_read()
    test_path_traversal_blocked()
    test_session_grant_via_prompt()
    test_denial_remembered()
    test_revoke_session_grant()
    test_audit_log()
    test_shell_denied_by_default()
    print("\n🌱 All permission tests passed!")
