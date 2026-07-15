"""
Base model and shared infrastructure for SalesPilot AI database.

All business entities inherit from BaseModel to ensure consistent audit fields,
soft-delete behavior, and UUID-based primary keys across the entire schema.

Design decisions:
- UUID PKs: Avoid sequential ID enumeration attacks and support distributed inserts.
- Soft delete (deleted_at): Preserve data for audit trails and AI memory recall.
  Hard deletes are reserved for PII erasure (GDPR) via a separate purge job.
- created_by / updated_by: Row-level audit trail without a separate audit table
  for every minor change. The AuditLog table captures significant business events.
- Timestamps use timezone-aware datetime (TIMESTAMP WITH TIME ZONE) so multi-region
  deployments don't produce ambiguous records.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base."""
    pass


class BaseModel(Base):
    """
    Abstract base for all business entities.

    Every table that represents a business object inherits from this class.
    Pure junction/association tables do NOT inherit BaseModel — they use
    lightweight definitions to keep join queries fast.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Primary key — UUIDv4 generated at application or DB level",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Row creation timestamp (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last modification timestamp, auto-updated by SQLAlchemy",
    )

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Soft-delete timestamp. NULL means the row is active.",
    )

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who created this row (nullable for system-generated rows)",
    )

    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who last modified this row",
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
