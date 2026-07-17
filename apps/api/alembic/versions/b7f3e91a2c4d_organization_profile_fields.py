"""organization profile fields + permission backfill

Revision ID: b7f3e91a2c4d
Revises: a2c71a69f650
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'b7f3e91a2c4d'
down_revision: Union[str, Sequence[str], None] = 'a2c71a69f650'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# New (resource, action) pairs introduced by the Organization module. Existing
# organizations were seeded (at creation time) with whatever RESOURCE_ACTIONS
# looked like back then, so — unlike new orgs, which pick these up automatically
# via OrganizationService.seed_system_roles — their roles need a one-time,
# additive backfill. This never touches permissions a role already has.
_NEW_ORG_ACTIONS = ["read", "update", "delete"]

# role_name -> actions granted, mirroring app/security/permissions.py's
# DEFAULT_ROLE_PERMISSIONS for the "organizations" resource specifically.
_GRANTS: dict[str, list[str]] = {
    "owner": ["read", "update", "delete"],
    "admin": ["read", "update"],
    "manager": ["read"],
    "sales": ["read"],
    "member": ["read"],
    "viewer": ["read"],
}


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('organizations', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('organizations', sa.Column('phone', sa.String(length=50), nullable=True))
    op.add_column('organizations', sa.Column('company_size', sa.String(length=20), nullable=True))
    op.add_column(
        'organizations',
        sa.Column('language', sa.String(length=10), nullable=False, server_default='en'),
    )
    op.add_column(
        'organizations',
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
    )
    op.add_column('organizations', sa.Column('brand_color', sa.String(length=7), nullable=True))
    op.add_column('organizations', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('organizations', sa.Column('address', JSONB(), nullable=True))

    # `server_default` above only backfills existing rows at add-column time;
    # drop it afterward so future inserts fall back to the ORM-level Python
    # default instead of a DB-level one baked into the schema forever.
    op.alter_column('organizations', 'language', server_default=None)
    op.alter_column('organizations', 'currency', server_default=None)

    connection = op.get_bind()

    # 1) get-or-create the new Permission rows (resource='organizations').
    permission_ids: dict[str, str] = {}
    for action in _NEW_ORG_ACTIONS:
        existing = connection.execute(
            sa.text(
                "SELECT id FROM permissions WHERE resource = 'organizations' AND action = :action"
            ),
            {"action": action},
        ).scalar()
        if existing is None:
            existing = connection.execute(
                sa.text(
                    "INSERT INTO permissions (id, resource, action, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), 'organizations', :action, now(), now()) "
                    "RETURNING id"
                ),
                {"action": action},
            ).scalar()
        permission_ids[action] = str(existing)

    # 2) grant them to every existing organization's built-in system roles,
    # additively — skip any (role, permission) pair that's already present.
    for role_name, actions in _GRANTS.items():
        for action in actions:
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
                {"role_name": role_name, "permission_id": permission_ids[action]},
            )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('organizations', 'address')
    op.drop_column('organizations', 'description')
    op.drop_column('organizations', 'brand_color')
    op.drop_column('organizations', 'currency')
    op.drop_column('organizations', 'language')
    op.drop_column('organizations', 'company_size')
    op.drop_column('organizations', 'phone')
    op.drop_column('organizations', 'email')
    # Permission/role_permission rows intentionally left in place on downgrade
    # — removing them could strip access other, unrelated code now depends on
    # if this migration is rolled back after the app has been running.
