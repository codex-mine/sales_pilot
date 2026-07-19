"""email tracking: emails.email_template_id column

Revision ID: f3d9c6a2b7e4
Revises: e7c2a4f6b8d1
Create Date: 2026-07-19 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3d9c6a2b7e4'
down_revision: Union[str, Sequence[str], None] = 'e7c2a4f6b8d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Set when an Email was created from (or saved as) an EmailTemplate —
    # drives EmailTemplate.total_sent/total_opened/total_replied analytics
    # (Email Tracking module). Nullable: most emails aren't template-backed.
    op.add_column('emails', sa.Column('email_template_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_emails_email_template_id_email_templates', 'emails', 'email_templates',
        ['email_template_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index(op.f('ix_emails_email_template_id'), 'emails', ['email_template_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_emails_email_template_id'), table_name='emails')
    op.drop_constraint('fk_emails_email_template_id_email_templates', 'emails', type_='foreignkey')
    op.drop_column('emails', 'email_template_id')
