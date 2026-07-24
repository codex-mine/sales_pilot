"""reports create/update/delete permission backfill

Revision ID: b1d5e8f3a7c2
Revises: a8e1f4c9d2b6
Create Date: 2026-07-22 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1d5e8f3a7c2'
down_revision: Union[str, Sequence[str], None] = 'a8e1f4c9d2b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# The Analytics/Reports module widened `RESOURCE_ACTIONS["reports"]` from
# `("read",)` to `("read", "create", "update", "delete")` without a matching
# backfill (unlike every earlier resource expansion — see
# b7f3e91a2c4d/c4a8e2f19b3d/e7c2a4f6b8d1 for the same pattern). Organizations
# seeded before that change still only have `reports.read` in
# `role_permissions`, so `POST /reports` genuinely 403s for them even though
# the application code is correct — OWNER/ADMIN/MANAGER need the three new
# actions granted retroactively; SALES never had a reports grant and MEMBER/
# VIEWER stay read-only by design, so none of those three are touched here.
_GRANT_ROLES = ["owner", "admin", "manager"]
_GRANT_ACTIONS = ["create", "update", "delete"]


def upgrade() -> None:
    """Upgrade schema."""
    connection = op.get_bind()
    permission_ids = [_get_or_create_permission(connection, "reports", action) for action in _GRANT_ACTIONS]

    for role_name in _GRANT_ROLES:
        for permission_id in permission_ids:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT r.id, :permission_id
                    FROM roles r
                    WHERE r.name = :role_name AND r.is_system = true
                    AND NOT EXISTS (
                        SELECT 1 FROM role_permissions rp
                        WHERE rp.role_id = r.id AND rp.permission_id = :permission_id
                    )
                    """
                ),
                {"role_name": role_name, "permission_id": permission_id},
            )


def _get_or_create_permission(connection, resource: str, action: str) -> str:
    existing = connection.execute(
        sa.text("SELECT id FROM permissions WHERE resource = :resource AND action = :action"),
        {"resource": resource, "action": action},
    ).scalar()
    if existing is not None:
        return str(existing)
    created = connection.execute(
        sa.text(
            "INSERT INTO permissions (id, resource, action, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :resource, :action, now(), now()) "
            "RETURNING id"
        ),
        {"resource": resource, "action": action},
    ).scalar()
    return str(created)


def downgrade() -> None:
    """Downgrade schema."""
    # Permission/role_permission rows intentionally left in place on
    # downgrade — see d3f8a2c91e5b for the same rationale.
    pass
