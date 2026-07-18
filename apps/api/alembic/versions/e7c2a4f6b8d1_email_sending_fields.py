"""email sending: send failure tracking columns + campaigns.manage permission

Revision ID: e7c2a4f6b8d1
Revises: d3f8a2c91e5b
Create Date: 2026-07-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7c2a4f6b8d1'
down_revision: Union[str, Sequence[str], None] = 'd3f8a2c91e5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# "manage" gates org-level sender identity configuration (Email Sending
# module) — OWNER/ADMIN only, matching the seed of every other *.manage
# permission (ai.manage, billing.manage, settings.manage). Existing
# organizations' system roles were seeded before "campaigns.manage" existed,
# so they need an additive, one-time grant; new organizations pick it up
# automatically via OrganizationService.seed_system_roles +
# app.security.permissions.DEFAULT_ROLE_PERMISSIONS.
_GRANT_ROLES = ["owner", "admin"]


def upgrade() -> None:
    """Upgrade schema."""
    # ── Emails: send failure tracking (Email Sending module) ────────────────
    # Additive columns: the outbox needs to show *why* a send failed
    # (suppressed recipient vs. a transient provider error) and how many
    # attempts were made — mirrors AIJob.error_message/retry_count for the
    # identical reason.
    op.add_column('emails', sa.Column('send_error', sa.Text(), nullable=True))
    op.add_column(
        'emails',
        sa.Column('send_retry_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.alter_column('emails', 'send_retry_count', server_default=None)

    # ── Permission backfill: campaigns.manage (sender identity settings) ────
    connection = op.get_bind()
    permission_id = _get_or_create_permission(connection, "campaigns", "manage")

    for role_name in _GRANT_ROLES:
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
    op.drop_column('emails', 'send_retry_count')
    op.drop_column('emails', 'send_error')
    # Permission/role_permission rows intentionally left in place on
    # downgrade — see d3f8a2c91e5b for the same rationale.
