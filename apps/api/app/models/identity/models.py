"""
Identity Domain — Organizations, Teams, Users, RBAC, Sessions, Tokens.

Architecture decisions:
- Organization is the top-level multi-tenant boundary. Every business entity
  has a FK to organization_id. This is the single chokepoint for tenant isolation
  and can be enforced at the DB level via Row Level Security (RLS) in PostgreSQL.

- Role-Based Access Control (RBAC) uses three tables: Role, Permission, RolePermission.
  Roles belong to an organization so each tenant can customize their permission model.
  System-level roles (owner, admin) are seeded at org creation.

- Sessions and RefreshTokens are separate tables.
  Session = server-side record of an active login (supports revocation).
  RefreshToken = JWT refresh token stored as a hashed value (never plaintext).

- Tokens (PasswordResetToken, EmailVerificationToken) are one-time-use with expiry.
  They store a hashed version of the token, not the plaintext.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModel
from app.models.enums import (
    OrganizationInvitationStatusEnum, PermissionActionEnum, RoleNameEnum, UserStatusEnum,
)

if TYPE_CHECKING:
    from app.models.crm.models import Lead, Company, Activity, Note
    from app.models.campaigns.models import Campaign
    from app.models.communication.models import Email, Meeting
    from app.models.ai.models import AIJob
    from app.models.billing.models import Subscription
    from app.models.administration.models import AuditLog, Notification, APIKey, Integration


# ─── Association Tables ───────────────────────────────────────────────────────

class RolePermission(Base):
    """
    M:M between Role and Permission.
    Junction table — no BaseModel overhead needed.
    """
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )


class UserRole(Base):
    """
    M:M between User and Role within an Organization context.
    A user can have different roles in different organizations.
    """
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    assigned_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        Index("ix_user_roles_org", "organization_id"),
        Index("ix_user_roles_user", "user_id"),
    )


class TeamMember(Base):
    """
    M:M between User and Team.
    Stores when the user joined the team and whether they are the team lead.
    """
    __tablename__ = "team_members"

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    is_team_lead: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_team_members_team", "team_id"),
        Index("ix_team_members_user", "user_id"),
    )


# ─── Core Tables ─────────────────────────────────────────────────────────────

class Organization(BaseModel):
    """
    Top-level tenant boundary. Every business entity belongs to an organization.

    The slug is used in URLs and must be globally unique.
    settings is a JSONB field for tenant-specific configuration that doesn't
    warrant its own table — e.g. branding colors, default timezone.
    """
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    domain: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
        comment="Primary email domain, used for auto-joining (e.g. acme.com)"
    )
    logo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Public/contact email, distinct from any user's login email"
    )
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    company_size: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="Bucketed headcount, e.g. '1-10', '11-50', '51-200'"
    )
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False, comment="ISO 4217 code")
    brand_color: Mapped[Optional[str]] = mapped_column(
        String(7), nullable=True, comment="Hex color, e.g. #16A34A"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="Structured mailing address: {line1, line2, city, state, postal_code}. Country uses the existing `country` column, not duplicated here."
    )
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, nullable=True,
        comment="Flexible org-level metadata (branding, feature flags, etc.)"
    )

    # Relationships
    teams: Mapped[List["Team"]] = relationship(
        "Team", back_populates="organization", cascade="all, delete-orphan"
    )
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="organization",
        cascade="all, delete-orphan",
        # Disambiguates against organizations.created_by/updated_by, which are
        # also FKs to users.id — without this, SQLAlchemy sees two FK paths
        # linking the organizations and users tables and can't infer which
        # one defines "an organization's users".
        foreign_keys="User.organization_id",
    )
    roles: Mapped[List["Role"]] = relationship(
        "Role", back_populates="organization", cascade="all, delete-orphan"
    )
    subscription: Mapped[Optional["Subscription"]] = relationship(
        "Subscription", back_populates="organization", uselist=False
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        "APIKey", back_populates="organization"
    )
    integrations: Mapped[List["Integration"]] = relationship(
        "Integration", back_populates="organization"
    )
    invitations: Mapped[List["OrganizationInvitation"]] = relationship(
        "OrganizationInvitation", back_populates="organization", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_organizations_domain", "domain"),
    )


class Team(BaseModel):
    """
    Sub-unit within an organization. Used for lead/campaign ownership and analytics.
    A user can belong to multiple teams; a team belongs to one organization.
    """
    __tablename__ = "teams"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="teams")
    members: Mapped[List["User"]] = relationship(
        "User", secondary="team_members", back_populates="teams"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_team_org_name"),
    )


class User(BaseModel):
    """
    Application user. A user belongs to exactly one organization (their primary org).
    They may be invited to other orgs via the invitation system (future V2).

    Passwords are stored as bcrypt hashes (never plaintext).
    avatar_url points to an S3-compatible object.
    """
    __tablename__ = "users"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
        comment="NULL for OAuth-only users"
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    locale: Mapped[str] = mapped_column(String(10), default="en")
    status: Mapped[UserStatusEnum] = mapped_column(
        String(30), default=UserStatusEnum.PENDING_VERIFICATION, nullable=False, index=True
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    google_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True,
        comment="Google OAuth subject identifier"
    )
    preferences: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="User preferences: notification settings, UI theme, etc."
    )
    permissions_version: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False,
        comment=(
            "Bumped whenever this user's role/permission assignments change. "
            "Embedded in JWT access tokens as a cache-invalidation hint for clients — "
            "server-side permission checks always re-derive from Role/Permission tables "
            "and never trust this claim, per the 'never trust frontend claims' rule."
        ),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="users", foreign_keys=[organization_id])
    teams: Mapped[List["Team"]] = relationship(
        "Team", secondary="team_members", back_populates="members"
    )
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        # user_roles.assigned_by is also a FK to users.id alongside user_id,
        # so the join through the secondary table is ambiguous without this.
        primaryjoin="User.id == UserRole.user_id",
        secondaryjoin="Role.id == UserRole.role_id",
    )
    sessions: Mapped[List["Session"]] = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan",
        foreign_keys="Session.user_id"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="RefreshToken.user_id",
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Notification.user_id",
    )

    __table_args__ = (
        Index("ix_users_org_status", "organization_id", "status"),
        Index("ix_users_google_id", "google_id"),
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Role(BaseModel):
    """
    RBAC Role — scoped to an organization.

    Why per-organization roles instead of global roles?
    Because enterprise customers need custom role names and permission sets.
    The built-in roles (owner, admin, member, viewer) are seeded at org creation,
    but organizations can define additional roles.

    is_system = True marks the seeded roles that cannot be deleted.
    """
    __tablename__ = "roles"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False,
        comment="System roles (owner, admin) cannot be deleted"
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="roles")
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission", secondary="role_permissions", back_populates="roles"
    )
    users: Mapped[List["User"]] = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
        primaryjoin="Role.id == UserRole.role_id",
        secondaryjoin="User.id == UserRole.user_id",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_role_org_name"),
    )


class Permission(BaseModel):
    """
    Fine-grained permission: resource + action pair.
    e.g. resource="leads", action="export"

    Permissions are global (not per-org) because the resource/action space
    is defined by the application, not by tenants.
    """
    __tablename__ = "permissions"

    resource: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Resource name: leads, campaigns, emails, billing, etc."
    )
    action: Mapped[PermissionActionEnum] = mapped_column(
        String(30), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role", secondary="role_permissions", back_populates="permissions"
    )

    __table_args__ = (
        UniqueConstraint("resource", "action", name="uq_permission_resource_action"),
        Index("ix_permissions_resource", "resource"),
    )


class Session(BaseModel):
    """
    Server-side session record. Allows immediate session revocation.

    Why server-side sessions alongside JWTs?
    Short-lived access tokens (15min) + long-lived refresh tokens (30 days)
    with server-side session records gives us the best of both worlds:
    stateless access validation + revocability.
    """
    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    device_info: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_sessions_user_active", "user_id", "is_active"),
        Index("ix_sessions_expires", "expires_at"),
    )


class RefreshToken(BaseModel):
    """Hashed refresh token for JWT rotation."""
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True,
        comment="SHA-256 hash of the token. Never store plaintext."
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
        comment="Hash of the new token that replaced this one (for rotation chain)"
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="refresh_tokens", foreign_keys=[user_id]
    )

    __table_args__ = (
        Index("ix_refresh_tokens_hash", "token_hash"),
        Index("ix_refresh_tokens_expires", "expires_at"),
    )


class PasswordResetToken(Base):
    """
    One-time password reset tokens.
    Not inheriting BaseModel to keep the table minimal — no soft delete needed.
    Tokens are hard-deleted after use or expiry (purge job).
    """
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class EmailVerificationToken(Base):
    """One-time email verification token."""
    __tablename__ = "email_verification_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class OrganizationInvitation(BaseModel):
    """
    Organization invitation — architecture for the future multi-member-onboarding
    flow (owner invites user by email -> accept -> membership + role assignment).

    Only the *invite an unregistered email into this organization* path is fully
    wired today because `User.organization_id` models one primary org per user
    (see User docstring). Accepting an invitation for an email that already has
    an account is intentionally rejected with a clear error rather than silently
    reassigning that user's org — true multi-org membership requires an
    `OrganizationMembership` M:M table, called out as a V2, additive-only change
    in ARCHITECTURE.md. This table and its service are built so that swap-in
    requires no changes to the invitation flow itself.
    """
    __tablename__ = "organization_invitations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    invited_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True,
        comment="SHA-256 hash of the invitation token. Never store plaintext."
    )
    status: Mapped[OrganizationInvitationStatusEnum] = mapped_column(
        String(20), default=OrganizationInvitationStatusEnum.PENDING, nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="invitations")
    role: Mapped["Role"] = relationship("Role")

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "email", "status",
            name="uq_invitation_org_email_status",
        ),
        Index("ix_invitations_org_status", "organization_id", "status"),
        Index("ix_invitations_email", "email"),
    )
