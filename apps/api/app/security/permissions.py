"""
Single source of truth for the permission space and the default role ->
permission mapping seeded for every new organization.

Nothing in the application should check `if user.role == "admin"` or write a
raw permission string inline in a route — routes depend on
`require_permission(resource, action)` (see app/auth/dependencies.py), which
resolves against the Permission/RolePermission/UserRole tables in the
database. This module only defines *what the seed data looks like*; it is not
consulted at request time.
"""

from app.models.enums import RoleNameEnum

# resource -> allowed actions. This is the full permission space; Alembic seeds
# one Permission row per (resource, action) pair from this table.
RESOURCE_ACTIONS: dict[str, tuple[str, ...]] = {
    "users": ("create", "read", "update", "delete"),
    # "manage" predates this set and is kept for backward compatibility with
    # existing role grants; "read"/"update"/"delete" are the granular actions
    # the Organization module's routes actually check.
    "organizations": ("read", "update", "delete", "manage"),
    "campaigns": ("create", "read", "update", "delete"),
    "leads": ("create", "read", "update", "delete", "import", "export", "bulk"),
    "companies": ("create", "read", "update", "delete", "export", "bulk"),
    "notes": ("manage",),
    "attachments": ("manage",),
    "reports": ("read",),
    "analytics": ("read",),
    "billing": ("manage",),
    "settings": ("manage",),
    # "read" gates viewing AI jobs/usage/prompts; "manage" gates configuration
    # (agents, keys, prompt activation) and job actions (retry/cancel/approve).
    "ai": ("read", "manage"),
    "tasks": ("manage",),
    "notifications": ("manage",),
}


def permission_key(resource: str, action: str) -> str:
    return f"{resource}.{action}"


ALL_PERMISSIONS: list[tuple[str, str]] = [
    (resource, action)
    for resource, actions in RESOURCE_ACTIONS.items()
    for action in actions
]


def _all(*resources: str) -> list[tuple[str, str]]:
    return [(r, a) for r in resources for a in RESOURCE_ACTIONS[r]]


# Default permission grants per built-in role, applied when an organization's
# system roles are seeded (see app.services.organization_service). Custom
# roles start with an empty permission set and are configured explicitly.
DEFAULT_ROLE_PERMISSIONS: dict[RoleNameEnum, list[tuple[str, str]]] = {
    RoleNameEnum.OWNER: ALL_PERMISSIONS,
    RoleNameEnum.ADMIN: [
        p
        for p in ALL_PERMISSIONS
        if p
        not in {
            ("organizations", "manage"),
            ("organizations", "delete"),
            ("billing", "manage"),
        }
    ],
    RoleNameEnum.MANAGER: [
        *_all("campaigns", "leads", "companies", "notes", "attachments"),
        ("reports", "read"),
        ("analytics", "read"),
        # Managers can see AI activity/spend but not reconfigure providers,
        # agents, or prompts (OWNER/ADMIN only, via ai.manage).
        ("ai", "read"),
        ("tasks", "manage"),
        ("notifications", "manage"),
        ("users", "read"),
        ("organizations", "read"),
    ],
    RoleNameEnum.SALES: [
        ("leads", "create"),
        ("leads", "read"),
        ("leads", "update"),
        ("companies", "create"),
        ("companies", "read"),
        ("companies", "update"),
        ("notes", "manage"),
        ("attachments", "manage"),
        ("campaigns", "read"),
        ("tasks", "manage"),
        ("notifications", "manage"),
        ("organizations", "read"),
    ],
    RoleNameEnum.MEMBER: [
        ("leads", "read"),
        ("companies", "read"),
        ("campaigns", "read"),
        ("reports", "read"),
        ("notifications", "manage"),
        ("organizations", "read"),
    ],
    RoleNameEnum.VIEWER: [
        ("leads", "read"),
        ("companies", "read"),
        ("campaigns", "read"),
        ("reports", "read"),
        ("analytics", "read"),
        ("organizations", "read"),
    ],
}

# Lower number = higher privilege. Used to pick a single "primary" role for
# JWT claims/display when a user holds more than one role in an organization,
# and to power hierarchical `require_role(..., at_least=True)` checks.
ROLE_PRIORITY: dict[RoleNameEnum, int] = {
    RoleNameEnum.OWNER: 0,
    RoleNameEnum.ADMIN: 1,
    RoleNameEnum.MANAGER: 2,
    RoleNameEnum.SALES: 3,
    RoleNameEnum.MEMBER: 4,
    RoleNameEnum.VIEWER: 5,
}


def role_priority(role_name: str) -> int:
    try:
        return ROLE_PRIORITY[RoleNameEnum(role_name)]
    except ValueError:
        return len(ROLE_PRIORITY)  # custom roles sort last (lowest priority)
