# SalesPilot AI — Alembic Migration Strategy

## Folder Structure

```
salespilot/
├── alembic/
│   ├── env.py                    # Alembic environment config
│   ├── script.py.mako            # Migration template
│   └── versions/
│       ├── 0001_initial_identity.py
│       ├── 0002_crm.py
│       ├── 0003_campaigns.py
│       ├── 0004_communication.py
│       ├── 0005_ai.py
│       ├── 0006_automation.py
│       ├── 0007_analytics.py
│       ├── 0008_administration.py
│       ├── 0009_billing.py
│       ├── 0010_seed_permissions.py
│       ├── 0011_seed_plans.py
│       └── 0012_seed_system_prompts.py
├── alembic.ini
└── app/
    └── models/
        ├── base.py
        ├── enums.py
        ├── __init__.py            # Imports all models so Alembic sees them
        ├── identity/
        │   ├── __init__.py
        │   └── models.py
        ├── crm/
        │   ├── __init__.py
        │   └── models.py
        ├── campaigns/
        │   ├── __init__.py
        │   └── models.py
        ├── communication/
        │   ├── __init__.py
        │   └── models.py
        ├── ai/
        │   ├── __init__.py
        │   └── models.py
        ├── automation/
        │   ├── __init__.py
        │   └── models.py
        ├── analytics/
        │   ├── __init__.py
        │   └── models.py
        ├── administration/
        │   ├── __init__.py
        │   └── models.py
        └── billing/
            ├── __init__.py
            └── models.py
```

---

## alembic/env.py

```python
"""
Alembic environment configuration for SalesPilot AI.

Key decisions:
- Uses online migration mode only (we always have a live DB connection).
- compare_type=True: detects column type changes (VARCHAR → TEXT, etc.).
- compare_server_default=True: detects server_default changes.
- render_as_batch=False: PostgreSQL supports DDL transactions natively.
- include_schemas=False: single schema (public) for V1.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import Base so Alembic sees all models via metadata
from app.models import Base  # noqa: F401 — triggers all model imports

config = context.config
fileConfig(config.config_file_name)

# Override sqlalchemy.url from environment variable
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

target_metadata = Base.metadata


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            # Render PostgreSQL-specific types correctly
            dialect_opts={"paramstyle": "named"},
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
```

---

## app/models/\_\_init\_\_.py  (critical — Alembic must import all models)

```python
"""
Central import file.
Alembic's env.py imports Base from here, which triggers all model imports
and registers every table in Base.metadata.

If a model file is not imported here, Alembic will not detect it.
"""

from app.models.base import Base, BaseModel  # noqa

# Import all models in dependency order to avoid FK resolution issues
from app.models.identity.models import (  # noqa
    Organization, Team, User, Role, Permission,
    UserRole, RolePermission, TeamMember,
    Session, RefreshToken, PasswordResetToken, EmailVerificationToken,
)
from app.models.crm.models import (  # noqa
    Company, Contact, Lead, LeadScore, Tag, LeadTag, Note, Activity, Attachment,
)
from app.models.campaigns.models import (  # noqa
    Campaign, Sequence, SequenceStep, EmailTemplate, CampaignLead,
)
from app.models.communication.models import (  # noqa
    Email, EmailEvent, Conversation, Message, Meeting, CalendarEvent,
)
from app.models.ai.models import (  # noqa
    AIAgent, AIJob, AIOutput, CompanyResearch, ProspectAnalysis,
    PromptTemplate, PromptVersion, AIMemory,
)
from app.models.remaining_domains import (  # noqa
    Workflow, WorkflowExecution, ScheduledJob,
    Event, Metric, Report, DashboardWidget,
    Notification, APIKey, Integration, AuditLog,
    Plan, Subscription, Invoice, Payment, UsageRecord,
)

__all__ = ["Base", "BaseModel"]
```

---

## Migration Ordering Rules

Migrations must respect foreign key dependencies:

```
1. extensions     → pgvector, uuid-ossp
2. enums          → PostgreSQL ENUM types
3. identity       → organizations, users, teams, roles, permissions
4. crm            → companies, contacts, leads, tags, notes, activities
5. campaigns      → campaigns, sequences, steps, templates, campaign_leads
6. communication  → emails, email_events, conversations, messages, meetings
7. ai             → ai_agents, ai_jobs, ai_outputs, prompt_templates, memories
8. automation     → workflows, workflow_executions, scheduled_jobs
9. analytics      → events, metrics, reports, widgets
10. administration → notifications, api_keys, integrations, audit_logs
11. billing       → plans, subscriptions, invoices, payments, usage_records
12. seeds         → permissions, plans, system prompt templates, admin roles
```

---

## Example Migration: 0001_initial_identity.py

```python
"""Initial identity tables

Revision ID: 0001
Revises: 
Create Date: 2025-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable required PostgreSQL extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    # op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')  # pgvector

    op.create_table(
        'organizations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('domain', sa.String(255), nullable=True),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('metadata', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('slug', name='uq_organizations_slug'),
    )
    op.create_index('ix_organizations_slug', 'organizations', ['slug'])
    op.create_index('ix_organizations_domain', 'organizations', ['domain'])

    # ... (users, teams, roles follow in dependency order)


def downgrade() -> None:
    op.drop_table('organizations')
```

---

## Seed Data Strategy

Seeds are executed as Alembic data migrations (separate from schema migrations).
This ensures seeds run exactly once and are tracked in the alembic_version table.

```python
# 0010_seed_permissions.py
"""Seed default permissions"""

from alembic import op
import uuid
from datetime import datetime, timezone

RESOURCES = ['leads', 'companies', 'contacts', 'campaigns', 'sequences',
             'emails', 'meetings', 'analytics', 'billing', 'settings',
             'api_keys', 'integrations', 'team_members', 'ai_jobs']

ACTIONS = ['create', 'read', 'update', 'delete', 'export', 'import', 'manage']

def upgrade() -> None:
    connection = op.get_bind()
    now = datetime.now(timezone.utc)
    rows = [
        {'id': str(uuid.uuid4()), 'resource': r, 'action': a,
         'created_at': now, 'updated_at': now}
        for r in RESOURCES for a in ACTIONS
    ]
    connection.execute(
        sa.text("""
            INSERT INTO permissions (id, resource, action, created_at, updated_at)
            VALUES (:id, :resource, :action, :created_at, :updated_at)
            ON CONFLICT (resource, action) DO NOTHING
        """),
        rows
    )

def downgrade() -> None:
    pass  # Never remove seeded permissions in downgrade
```

### Seed data categories

| Seed File | Content |
|---|---|
| 0010_seed_permissions.py | All resource × action permission pairs |
| 0011_seed_plans.py | Starter / Pro / Business / Enterprise plans |
| 0012_seed_system_prompts.py | Default prompt templates for each agent type |
| 0013_seed_ai_agents.py | Default agent configurations per org (run at org creation) |

System prompt seeds use `ON CONFLICT DO NOTHING` so re-running migrations is idempotent.
