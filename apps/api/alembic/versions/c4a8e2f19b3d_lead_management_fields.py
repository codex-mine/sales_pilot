"""lead management fields + permission backfill

Revision ID: c4a8e2f19b3d
Revises: b7f3e91a2c4d
Create Date: 2026-07-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'c4a8e2f19b3d'
down_revision: Union[str, Sequence[str], None] = 'b7f3e91a2c4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# New (resource, action) pairs introduced by the Lead Management module.
# Mirrors the backfill pattern from b7f3e91a2c4d (organizations) — existing
# organizations' system roles were seeded before these actions existed, so
# they need an additive, one-time grant. New organizations pick these up
# automatically via OrganizationService.seed_system_roles.
_NEW_LEADS_ACTIONS = ["import", "export", "bulk"]

# role_name -> [(resource, action), ...]
_GRANTS: dict[str, list[tuple[str, str]]] = {
    "owner": [
        ("leads", "import"), ("leads", "export"), ("leads", "bulk"),
        ("notes", "manage"), ("attachments", "manage"),
    ],
    "admin": [
        ("leads", "import"), ("leads", "export"), ("leads", "bulk"),
        ("notes", "manage"), ("attachments", "manage"),
    ],
    "manager": [
        ("leads", "import"), ("leads", "export"), ("leads", "bulk"),
        ("notes", "manage"), ("attachments", "manage"),
    ],
    "sales": [
        ("notes", "manage"), ("attachments", "manage"),
    ],
}


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('leads', sa.Column('twitter_url', sa.String(length=512), nullable=True))
    op.add_column('leads', sa.Column('state', sa.String(length=100), nullable=True))
    op.add_column('leads', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('leads', sa.Column('address', JSONB(), nullable=True))
    op.add_column('leads', sa.Column('company_size', sa.String(length=20), nullable=True))
    op.add_column('leads', sa.Column('revenue', sa.Float(), nullable=True))
    op.add_column('leads', sa.Column('employee_count', sa.Integer(), nullable=True))
    op.add_column('leads', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('leads', sa.Column('lead_score', sa.Float(), nullable=True))
    op.add_column(
        'leads',
        sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'leads',
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column('leads', 'is_favorite', server_default=None)
    op.alter_column('leads', 'is_archived', server_default=None)

    op.create_index('ix_leads_org_archived', 'leads', ['organization_id', 'is_archived'])
    op.create_index('ix_leads_org_favorite', 'leads', ['organization_id', 'is_favorite'])

    connection = op.get_bind()

    # 1) get-or-create the new "leads" Permission rows.
    permission_ids: dict[tuple[str, str], str] = {}
    for action in _NEW_LEADS_ACTIONS:
        permission_ids[("leads", action)] = _get_or_create_permission(connection, "leads", action)
    for resource in ("notes", "attachments"):
        permission_ids[(resource, "manage")] = _get_or_create_permission(connection, resource, "manage")

    # 2) grant them to every existing organization's built-in system roles,
    # additively — skip any (role, permission) pair that's already present.
    for role_name, grants in _GRANTS.items():
        for resource, action in grants:
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
                {"role_name": role_name, "permission_id": permission_ids[(resource, action)]},
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
    op.drop_index('ix_leads_org_favorite', table_name='leads')
    op.drop_index('ix_leads_org_archived', table_name='leads')
    op.drop_column('leads', 'is_archived')
    op.drop_column('leads', 'is_favorite')
    op.drop_column('leads', 'lead_score')
    op.drop_column('leads', 'description')
    op.drop_column('leads', 'employee_count')
    op.drop_column('leads', 'revenue')
    op.drop_column('leads', 'company_size')
    op.drop_column('leads', 'address')
    op.drop_column('leads', 'city')
    op.drop_column('leads', 'state')
    op.drop_column('leads', 'twitter_url')
    # Permission/role_permission rows intentionally left in place on downgrade
    # — see b7f3e91a2c4d for the same rationale.
