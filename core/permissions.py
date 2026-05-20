"""
Caz Permission System

Implements least-privilege access control with session-scoped grants.

How it works:
1. Check config.toml pre-approvals (persistent across sessions)
2. Check session grants (given at runtime, expire when Caz exits)
3. If neither, prompt the user for permission
4. If user denies, action is blocked — no workarounds

Teaching note: This is the "deny by default" security pattern.
Every action must pass through this module. No shortcuts.
The permission system is the gatekeeper — if it says no, nothing happens.

Security note: Session grants are intentionally NOT persisted to disk.
They live only in memory and die when the process exits.
This limits blast radius if something goes wrong.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class PermissionType(Enum):
    """Types of permissions Caz can request."""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    NETWORK = "network"
    SHELL = "shell"


class PermissionDecision(Enum):
    """Result of a permission check."""
    ALLOWED_BY_CONFIG = "allowed_by_config"     # Pre-approved in config.toml
    ALLOWED_BY_SESSION = "allowed_by_session"   # User granted this session
    DENIED_BY_USER = "denied_by_user"           # User said no
    DENIED_BY_DEFAULT = "denied_by_default"     # Never asked / no grant exists


@dataclass
class PermissionRequest:
    """
    A request for Caz to do something that requires permission.

    Includes context so the user knows exactly WHY Caz wants access.
    Transparency is non-negotiable — never ask without explaining.
    """
    permission_type: PermissionType
    resource: str               # What specifically (path, URL, command)
    reason: str                 # Why Caz needs this (shown to user)
    scope: str = "session"      # "session" (default) or "persistent"


@dataclass
class PermissionGrant:
    """A record that permission was granted."""
    permission_type: PermissionType
    resource: str
    scope: str                  # "session" or "persistent"


class PermissionManager:
    """
    Central permission authority for Caz.

    All access requests go through here. Nothing bypasses this.

    Teaching note on the design:
    - _config_grants: loaded from config.toml at startup (persistent)
    - _session_grants: accumulated during runtime (ephemeral)
    - _session_denials: tracks what user said no to (don't re-ask)
    """

    def __init__(self, config: dict):
        """
        Initialize with config dict from core.config.load().

        Only config.toml pre-approvals are loaded here.
        Session grants start EMPTY — that's the point.
        """
        self._config_grants: list[PermissionGrant] = []
        self._session_grants: list[PermissionGrant] = []
        self._session_denials: list[str] = []  # Resources user denied
        self._audit_log: list[dict] = []

        # Load persistent grants from config
        self._load_config_grants(config)

    def _load_config_grants(self, config: dict) -> None:
        """Parse config.toml permissions into grant objects."""
        perms = config.get("permissions", {})

        # Network access
        if perms.get("allow_network", False):
            self._config_grants.append(
                PermissionGrant(
                    permission_type=PermissionType.NETWORK,
                    resource="*",
                    scope="persistent",
                )
            )

        # Shell access
        if perms.get("allow_shell", False):
            self._config_grants.append(
                PermissionGrant(
                    permission_type=PermissionType.SHELL,
                    resource="*",
                    scope="persistent",
                )
            )

        # File read paths
        for path in perms.get("allow_file_read", []):
            self._config_grants.append(
                PermissionGrant(
                    permission_type=PermissionType.FILE_READ,
                    resource=str(Path(path).expanduser().resolve()),
                    scope="persistent",
                )
            )

        # File write paths
        for path in perms.get("allow_file_write", []):
            self._config_grants.append(
                PermissionGrant(
                    permission_type=PermissionType.FILE_WRITE,
                    resource=str(Path(path).expanduser().resolve()),
                    scope="persistent",
                )
            )

    def check(self, request: PermissionRequest) -> PermissionDecision:
        """
        Check if a permission is already granted (config or session).
        Does NOT prompt the user — use request_permission() for that.

        Returns the decision without side effects.
        """
        # Check if previously denied this session (don't re-ask)
        denial_key = f"{request.permission_type.value}:{request.resource}"
        if denial_key in self._session_denials:
            return PermissionDecision.DENIED_BY_USER

        # Check config grants (persistent)
        if self._matches_any_grant(request, self._config_grants):
            self._log_check(request, PermissionDecision.ALLOWED_BY_CONFIG)
            return PermissionDecision.ALLOWED_BY_CONFIG

        # Check session grants (ephemeral)
        if self._matches_any_grant(request, self._session_grants):
            self._log_check(request, PermissionDecision.ALLOWED_BY_SESSION)
            return PermissionDecision.ALLOWED_BY_SESSION

        return PermissionDecision.DENIED_BY_DEFAULT

    def request_permission(self, request: PermissionRequest) -> PermissionDecision:
        """
        Full permission flow: check existing grants, prompt user if needed.

        This is the main entry point for permission requests.
        Returns the final decision.
        """
        # First check if already granted or denied
        existing = self.check(request)
        if existing != PermissionDecision.DENIED_BY_DEFAULT:
            return existing

        # Prompt user
        granted = self._prompt_user(request)

        if granted:
            # Store as session grant (dies when Caz exits)
            self._session_grants.append(
                PermissionGrant(
                    permission_type=request.permission_type,
                    resource=request.resource,
                    scope="session",
                )
            )
            self._log_check(request, PermissionDecision.ALLOWED_BY_SESSION)
            return PermissionDecision.ALLOWED_BY_SESSION
        else:
            # Remember denial so we don't ask again this session
            denial_key = f"{request.permission_type.value}:{request.resource}"
            self._session_denials.append(denial_key)
            self._log_check(request, PermissionDecision.DENIED_BY_USER)
            return PermissionDecision.DENIED_BY_USER

    def _matches_any_grant(
        self, request: PermissionRequest, grants: list[PermissionGrant]
    ) -> bool:
        """
        Check if request matches any grant in the list.

        For file permissions, checks if the requested path is UNDER
        a granted directory. This prevents path traversal attacks —
        granting ~/notes doesn't grant ~/secrets.
        """
        for grant in grants:
            if grant.permission_type != request.permission_type:
                continue

            # Wildcard grant (e.g., network=true grants all network)
            if grant.resource == "*":
                return True

            # For file permissions, check path containment
            if request.permission_type in (
                PermissionType.FILE_READ,
                PermissionType.FILE_WRITE,
            ):
                granted_path = Path(grant.resource).resolve()
                requested_path = Path(request.resource).expanduser().resolve()

                # Security: resolve() prevents ../../../ traversal attacks
                # Check exact match OR path is under granted directory
                if requested_path == granted_path:
                    return True
                try:
                    requested_path.relative_to(granted_path)
                    return True
                except ValueError:
                    continue
            else:
                # Exact match for non-file permissions
                if grant.resource == request.resource:
                    return True

        return False

    def _prompt_user(self, request: PermissionRequest) -> bool:
        """
        Ask the user for permission with full transparency.

        Shows: what type, what resource, and WHY Caz needs it.
        The user must actively type 'y' — anything else is denial.

        Teaching note: This is "explicit consent" — the user must
        actively opt in. Silence or confusion = denied.
        """
        print("\n" + "=" * 50)
        print("🔐 PERMISSION REQUEST")
        print("=" * 50)
        print(f"  Type:     {request.permission_type.value}")
        print(f"  Resource: {request.resource}")
        print(f"  Reason:   {request.reason}")
        print(f"  Scope:    This session only (expires when Caz exits)")
        print("=" * 50)

        try:
            response = input("  Grant permission? (y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  → Denied (interrupted)")
            return False

        granted = response == "y"
        if granted:
            print("  → Granted for this session")
        else:
            print("  → Denied")

        return granted

    def _log_check(self, request: PermissionRequest, decision: PermissionDecision) -> None:
        """Record permission check in audit log."""
        self._audit_log.append({
            "type": request.permission_type.value,
            "resource": request.resource,
            "reason": request.reason,
            "decision": decision.value,
        })

    def get_audit_log(self) -> list[dict]:
        """Return full audit trail of permission decisions."""
        return self._audit_log.copy()

    def get_session_grants(self) -> list[PermissionGrant]:
        """Return current session grants (for transparency/debugging)."""
        return self._session_grants.copy()

    def revoke_session_grant(self, permission_type: PermissionType, resource: str) -> bool:
        """
        Revoke a session grant. Returns True if something was revoked.

        Teaching note: Revocability is important — if you grant something
        by mistake, you can take it back without restarting Caz.
        """
        before = len(self._session_grants)
        self._session_grants = [
            g for g in self._session_grants
            if not (g.permission_type == permission_type and g.resource == resource)
        ]
        revoked = len(self._session_grants) < before
        if revoked:
            self._audit_log.append({
                "type": permission_type.value,
                "resource": resource,
                "reason": "User revoked grant",
                "decision": "revoked",
            })
        return revoked
