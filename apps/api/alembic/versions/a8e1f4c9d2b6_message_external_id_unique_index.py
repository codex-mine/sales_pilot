"""inbox: partial unique index on messages.external_message_id

Revision ID: a8e1f4c9d2b6
Revises: f3d9c6a2b7e4
Create Date: 2026-07-20 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a8e1f4c9d2b6'
down_revision: Union[str, Sequence[str], None] = 'f3d9c6a2b7e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Partial (nullable-safe) unique index: `external_message_id` is
    # NULLABLE on `messages` (some inbound providers omit it), so a plain
    # UNIQUE constraint would reject multiple legitimate NULL rows. This
    # only enforces uniqueness when the column is actually populated —
    # webhook idempotency for the Inbox module's inbound ingestion.
    op.execute(
        "CREATE UNIQUE INDEX uq_message_external_id "
        "ON messages (external_message_id) "
        "WHERE external_message_id IS NOT NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX uq_message_external_id")
