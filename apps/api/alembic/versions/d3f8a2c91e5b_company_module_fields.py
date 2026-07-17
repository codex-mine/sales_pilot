"""company module fields + polymorphic notes/activities/attachments + permission backfill

Revision ID: d3f8a2c91e5b
Revises: c4a8e2f19b3d
Create Date: 2026-07-17 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'd3f8a2c91e5b'
down_revision: Union[str, Sequence[str], None] = 'c4a8e2f19b3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# New (resource, action) pairs introduced by the Company module. Mirrors the
# backfill pattern from b7f3e91a2c4d/c4a8e2f19b3d — existing organizations'
# system roles were seeded before "companies" existed as a resource, so they
# need an additive, one-time grant. New organizations pick these up
# automatically via OrganizationService.seed_system_roles +
# app.security.permissions.DEFAULT_ROLE_PERMISSIONS.
_COMPANIES_ACTIONS = ["create", "read", "update", "delete", "export", "bulk"]

# role_name -> [action, ...] for the "companies" resource.
_GRANTS: dict[str, list[str]] = {
    "owner": ["create", "read", "update", "delete", "export", "bulk"],
    "admin": ["create", "read", "update", "delete", "export", "bulk"],
    "manager": ["create", "read", "update", "delete", "export", "bulk"],
    "sales": ["create", "read", "update"],
    "member": ["read"],
    "viewer": ["read"],
}


def upgrade() -> None:
    """Upgrade schema."""
    # ── Companies: new profile/ownership/status fields ─────────────────────
    op.add_column('companies', sa.Column('owner_id', sa.UUID(), nullable=True))
    op.add_column('companies', sa.Column('legal_name', sa.String(length=255), nullable=True))
    op.add_column('companies', sa.Column('logo_url', sa.String(length=512), nullable=True))
    op.add_column('companies', sa.Column('twitter_url', sa.String(length=512), nullable=True))
    op.add_column('companies', sa.Column('facebook_url', sa.String(length=512), nullable=True))
    op.add_column('companies', sa.Column('instagram_url', sa.String(length=512), nullable=True))
    op.add_column('companies', sa.Column('postal_code', sa.String(length=20), nullable=True))
    op.add_column(
        'companies',
        sa.Column(
            'address', JSONB(), nullable=True,
            comment='Structured street address: {line1, line2}. City/state/country/postal_code are separate columns.',
        ),
    )
    op.add_column(
        'companies',
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD', comment='ISO 4217 code'),
    )
    op.add_column('companies', sa.Column('founded_year', sa.Integer(), nullable=True))
    op.add_column('companies', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column(
        'companies',
        sa.Column('status', sa.String(length=20), nullable=False, server_default='prospect'),
    )
    op.add_column('companies', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))
    op.alter_column('companies', 'currency', server_default=None)
    op.alter_column('companies', 'status', server_default=None)

    op.create_foreign_key(
        'fk_companies_owner_id_users', 'companies', 'users', ['owner_id'], ['id'], ondelete='SET NULL'
    )
    op.create_index('ix_companies_org_owner', 'companies', ['organization_id', 'owner_id'])
    op.create_index('ix_companies_org_archived', 'companies', ['organization_id', 'archived_at'])
    op.create_index(op.f('ix_companies_status'), 'companies', ['status'])

    # ── Contacts: simple active/inactive flag for the Employees display ────
    op.add_column(
        'contacts',
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
    )
    op.alter_column('contacts', 'status', server_default=None)

    # ── company_tags: mirrors lead_tags (Tag is org-scoped, reused across entities) ─
    op.create_table(
        'company_tags',
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('tag_id', sa.UUID(), nullable=False),
        sa.Column('tagged_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tagged_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tagged_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('company_id', 'tag_id'),
    )
    op.create_index('ix_company_tags_company', 'company_tags', ['company_id'])
    op.create_index('ix_company_tags_tag', 'company_tags', ['tag_id'])

    # ── Notes/Activities/Attachments: relax lead_id, add company_id ────────
    # These tables started Lead-only. The Company module reuses them instead
    # of introducing parallel CompanyNote/CompanyActivity/CompanyAttachment
    # tables. lead_id and company_id are mutually exclusive by application
    # convention (enforced in the service layer, matching this codebase's
    # existing preference for service-level invariants over DB CHECK
    # constraints — see e.g. Lead's identity validation).
    op.alter_column('notes', 'lead_id', nullable=True)
    op.add_column('notes', sa.Column('company_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_notes_company_id_companies', 'notes', 'companies', ['company_id'], ['id'], ondelete='CASCADE'
    )
    op.create_index(op.f('ix_notes_company_id'), 'notes', ['company_id'])

    op.alter_column('activities', 'lead_id', nullable=True)
    op.add_column('activities', sa.Column('company_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_activities_company_id_companies', 'activities', 'companies', ['company_id'], ['id'], ondelete='CASCADE'
    )
    op.create_index(op.f('ix_activities_company_id'), 'activities', ['company_id'])
    op.create_index('ix_activities_org_company', 'activities', ['organization_id', 'company_id'])

    op.alter_column('attachments', 'lead_id', nullable=True)
    op.add_column('attachments', sa.Column('company_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_attachments_company_id_companies', 'attachments', 'companies', ['company_id'], ['id'], ondelete='CASCADE'
    )
    op.create_index(op.f('ix_attachments_company_id'), 'attachments', ['company_id'])

    # ── Permission backfill ─────────────────────────────────────────────────
    connection = op.get_bind()

    permission_ids: dict[str, str] = {}
    for action in _COMPANIES_ACTIONS:
        permission_ids[action] = _get_or_create_permission(connection, "companies", action)

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
    op.drop_index(op.f('ix_attachments_company_id'), table_name='attachments')
    op.drop_constraint('fk_attachments_company_id_companies', 'attachments', type_='foreignkey')
    op.drop_column('attachments', 'company_id')
    op.alter_column('attachments', 'lead_id', nullable=False)

    op.drop_index('ix_activities_org_company', table_name='activities')
    op.drop_index(op.f('ix_activities_company_id'), table_name='activities')
    op.drop_constraint('fk_activities_company_id_companies', 'activities', type_='foreignkey')
    op.drop_column('activities', 'company_id')
    op.alter_column('activities', 'lead_id', nullable=False)

    op.drop_index(op.f('ix_notes_company_id'), table_name='notes')
    op.drop_constraint('fk_notes_company_id_companies', 'notes', type_='foreignkey')
    op.drop_column('notes', 'company_id')
    op.alter_column('notes', 'lead_id', nullable=False)

    op.drop_index('ix_company_tags_tag', table_name='company_tags')
    op.drop_index('ix_company_tags_company', table_name='company_tags')
    op.drop_table('company_tags')

    op.drop_column('contacts', 'status')

    op.drop_index(op.f('ix_companies_status'), table_name='companies')
    op.drop_index('ix_companies_org_archived', table_name='companies')
    op.drop_index('ix_companies_org_owner', table_name='companies')
    op.drop_constraint('fk_companies_owner_id_users', 'companies', type_='foreignkey')
    op.drop_column('companies', 'archived_at')
    op.drop_column('companies', 'status')
    op.drop_column('companies', 'email')
    op.drop_column('companies', 'founded_year')
    op.drop_column('companies', 'currency')
    op.drop_column('companies', 'address')
    op.drop_column('companies', 'postal_code')
    op.drop_column('companies', 'instagram_url')
    op.drop_column('companies', 'facebook_url')
    op.drop_column('companies', 'twitter_url')
    op.drop_column('companies', 'logo_url')
    op.drop_column('companies', 'legal_name')
    op.drop_column('companies', 'owner_id')
    # Permission/role_permission rows intentionally left in place on downgrade
    # — see b7f3e91a2c4d for the same rationale.
