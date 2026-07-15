# SalesPilot AI — PostgreSQL Optimization & Query Patterns

## Index Strategy

### Why these indexes, and when to add more

Indexes are a trade-off: faster reads, slower writes, more storage.
The rule: index columns that appear in WHERE, ORDER BY, or JOIN ON clauses
on tables with >10,000 rows. Don't pre-index everything.

### Mandatory indexes (already defined in models)

```sql
-- Tenant isolation (every query filters by org)
CREATE INDEX ix_leads_org_status       ON leads(organization_id, status);
CREATE INDEX ix_leads_org_owner        ON leads(organization_id, owner_id);
CREATE INDEX ix_campaigns_org_status   ON campaigns(organization_id, status);
CREATE INDEX ix_emails_org_status      ON emails(organization_id, current_status);
CREATE INDEX ix_ai_jobs_org_status     ON ai_jobs(organization_id, status);
CREATE INDEX ix_activities_org_lead    ON activities(organization_id, lead_id);

-- Scheduler hot path (Celery reads this every few seconds)
CREATE INDEX ix_campaign_leads_next_action
    ON campaign_leads(next_action_at, status)
    WHERE status = 'in_progress' AND next_action_at IS NOT NULL;

-- Email event analytics
CREATE INDEX ix_email_events_org_type_occurred
    ON email_events(organization_id, event_type, occurred_at);

-- AI job cost tracking
CREATE INDEX ix_ai_jobs_created_at     ON ai_jobs(created_at DESC);
CREATE INDEX ix_ai_jobs_entity         ON ai_jobs(entity_type, entity_id);

-- Webhook idempotency
CREATE UNIQUE INDEX uq_email_event_provider_id
    ON email_events(provider_event_id)
    WHERE provider_event_id IS NOT NULL;

-- Full-text search on leads (optional but recommended)
CREATE INDEX ix_leads_fts ON leads
    USING gin(to_tsvector('english',
        coalesce(first_name,'') || ' ' ||
        coalesce(last_name,'') || ' ' ||
        coalesce(email,'') || ' ' ||
        coalesce(company_name,'')
    ));
```

### Partial indexes (significant storage/speed savings)

```sql
-- Only index active campaigns (ignore archived/completed)
CREATE INDEX ix_campaigns_active ON campaigns(organization_id, created_at DESC)
    WHERE status = 'active' AND deleted_at IS NULL;

-- Only index unread notifications
CREATE INDEX ix_notifications_unread ON notifications(user_id, created_at DESC)
    WHERE is_read = false AND deleted_at IS NULL;

-- Only pending/running AI jobs (the scheduler never queries completed)
CREATE INDEX ix_ai_jobs_pending ON ai_jobs(created_at, organization_id)
    WHERE status IN ('pending', 'running', 'retrying');

-- Soft-delete aware: most queries filter deleted_at IS NULL
-- Add this to every business entity table with high query volume
CREATE INDEX ix_leads_active ON leads(organization_id, status)
    WHERE deleted_at IS NULL;
```

### pgvector indexes (when enabled)

```sql
-- IVFFlat index for approximate nearest-neighbor search on embeddings
-- Requires training (requires >1000 rows in practice)
-- lists = sqrt(total_rows) is a good starting point

CREATE INDEX ix_ai_memory_embedding ON ai_memories
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- HNSW is faster for queries but slower to build (PostgreSQL 16+)
CREATE INDEX ix_company_research_embedding ON company_research
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

---

## Row Level Security (RLS)

RLS enforces tenant isolation at the database level.
Even if application code has a bug, cross-tenant data leakage is impossible.

```sql
-- Enable RLS on all business entity tables
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE emails ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_jobs ENABLE ROW LEVEL SECURITY;
-- ... (all business tables)

-- Create a policy that uses a session variable set at connection time
-- The application sets this at the start of every request:
--   SET app.current_org_id = '<uuid>';

CREATE POLICY org_isolation ON leads
    USING (organization_id = current_setting('app.current_org_id')::uuid);

CREATE POLICY org_isolation ON companies
    USING (organization_id = current_setting('app.current_org_id')::uuid);

-- Service role (Celery workers, migrations) bypasses RLS
CREATE ROLE salespilot_service;
ALTER ROLE salespilot_service BYPASSRLS;

CREATE ROLE salespilot_app;
-- salespilot_app uses RLS (the application user)
```

Setting the session variable in FastAPI middleware:

```python
# app/db/middleware.py
from sqlalchemy import text

async def set_org_context(session: AsyncSession, org_id: str) -> None:
    """Set RLS session variable. Call at the start of every request."""
    await session.execute(
        text("SET LOCAL app.current_org_id = :org_id"),
        {"org_id": org_id}
    )
```

---

## Common Query Patterns

### 1. Lead list with pagination (most common query)

```python
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

async def get_leads(
    session: AsyncSession,
    org_id: uuid.UUID,
    status: LeadStatusEnum | None = None,
    owner_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Lead], int]:
    
    base_query = (
        select(Lead)
        .where(Lead.organization_id == org_id)
        .where(Lead.deleted_at.is_(None))
    )
    
    if status:
        base_query = base_query.where(Lead.status == status)
    if owner_id:
        base_query = base_query.where(Lead.owner_id == owner_id)
    
    # Count query (separate to avoid COUNT(*) on a paginated subquery)
    count_query = select(func.count()).select_from(base_query.subquery())
    total = await session.scalar(count_query)
    
    # Data query with selectin loading for tags (avoids N+1)
    data_query = (
        base_query
        .options(selectinload(Lead.tags))
        .order_by(Lead.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.scalars(data_query)
    
    return result.all(), total or 0
```

### 2. Scheduler: find leads ready for next sequence step

```python
async def get_leads_due_for_action(
    session: AsyncSession,
    batch_size: int = 100,
) -> list[CampaignLead]:
    """
    Called by Celery beat every minute.
    Uses the partial index ix_campaign_leads_next_action for sub-ms performance.
    """
    now = datetime.now(timezone.utc)
    result = await session.scalars(
        select(CampaignLead)
        .where(CampaignLead.status == CampaignLeadStatusEnum.IN_PROGRESS)
        .where(CampaignLead.next_action_at <= now)
        .options(
            selectinload(CampaignLead.lead),
            selectinload(CampaignLead.next_step)
            .selectinload(SequenceStep.email_template)
        )
        .order_by(CampaignLead.next_action_at.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)  # Prevents duplicate processing across workers
    )
    return result.all()
```

### 3. Dashboard metrics (pre-aggregated via Metric table)

```python
async def get_dashboard_stats(
    session: AsyncSession,
    org_id: uuid.UUID,
    campaign_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
) -> dict:
    """Fast dashboard query — reads from pre-aggregated Metric table."""
    query = (
        select(Metric.metric_name, func.sum(Metric.value).label("total"))
        .where(Metric.organization_id == org_id)
        .where(Metric.period == "daily")
        .where(Metric.metric_date >= (date_from or datetime.now() - timedelta(days=30)))
        .group_by(Metric.metric_name)
    )
    if campaign_id:
        query = query.where(Metric.campaign_id == campaign_id)
    
    rows = await session.execute(query)
    return {row.metric_name: row.total for row in rows}
```

### 4. Email event timeline for a single email

```python
async def get_email_timeline(
    session: AsyncSession,
    email_id: uuid.UUID,
) -> list[EmailEvent]:
    """
    Append-only events give us the full delivery timeline.
    Ordered by occurred_at for chronological display.
    """
    result = await session.scalars(
        select(EmailEvent)
        .where(EmailEvent.email_id == email_id)
        .order_by(EmailEvent.occurred_at.asc())
    )
    return result.all()
```

### 5. AI job cost report

```python
async def get_ai_cost_by_agent(
    session: AsyncSession,
    org_id: uuid.UUID,
    month: datetime,
) -> list[dict]:
    """Monthly AI cost breakdown by agent type."""
    result = await session.execute(
        select(
            AIAgent.agent_type,
            func.count(AIJob.id).label("job_count"),
            func.sum(AIJob.total_tokens).label("total_tokens"),
            func.sum(AIJob.cost_usd).label("total_cost_usd"),
        )
        .join(AIJob, AIJob.agent_id == AIAgent.id)
        .where(AIJob.organization_id == org_id)
        .where(AIJob.status == AIJobStatusEnum.COMPLETED)
        .where(func.date_trunc("month", AIJob.created_at) == func.date_trunc("month", month))
        .group_by(AIAgent.agent_type)
        .order_by(func.sum(AIJob.cost_usd).desc())
    )
    return [
        {"agent_type": r.agent_type, "jobs": r.job_count,
         "tokens": r.total_tokens, "cost_usd": r.total_cost_usd}
        for r in result
    ]
```

### 6. Lead full context (used by AI agents)

```python
async def get_lead_full_context(
    session: AsyncSession,
    lead_id: uuid.UUID,
) -> Lead:
    """
    Load a lead with all related data needed by AI agents.
    Uses selectinload to avoid N+1 without joining everything into one huge query.
    """
    result = await session.scalar(
        select(Lead)
        .where(Lead.id == lead_id)
        .options(
            selectinload(Lead.contact),
            selectinload(Lead.company)
                .selectinload(Company.research),  # type: ignore
            selectinload(Lead.scores),
            selectinload(Lead.activities),
            selectinload(Lead.emails)
                .selectinload(Email.events),
            selectinload(Lead.tags),
        )
    )
    return result
```

---

## PostgreSQL Configuration Recommendations

For a 4-core / 16GB RAM production instance (adjust proportionally):

```ini
# postgresql.conf tuning for SalesPilot AI workload

# Memory
shared_buffers = 4GB              # 25% of RAM
effective_cache_size = 12GB       # 75% of RAM
work_mem = 64MB                   # Per sort/hash operation
maintenance_work_mem = 1GB        # For VACUUM, CREATE INDEX

# WAL / Durability
wal_buffers = 64MB
checkpoint_completion_target = 0.9
max_wal_size = 4GB

# Connections (use PgBouncer in front — not raw connections)
max_connections = 100

# Parallelism
max_worker_processes = 4
max_parallel_workers_per_gather = 2
max_parallel_workers = 4

# Planner
random_page_cost = 1.1            # SSD storage
effective_io_concurrency = 200    # SSD IOPS

# Autovacuum (critical for append-heavy tables like email_events, activities)
autovacuum_vacuum_scale_factor = 0.05   # Vacuum after 5% of rows change (default 20%)
autovacuum_analyze_scale_factor = 0.02  # Analyze after 2% change
autovacuum_max_workers = 4

# Logging
log_min_duration_statement = 1000  # Log queries >1 second
log_autovacuum_min_duration = 0
```

### PgBouncer (connection pooling)

```ini
# pgbouncer.ini
[databases]
salespilot = host=localhost port=5432 dbname=salespilot

[pgbouncer]
pool_mode = transaction            # Transaction-level pooling (required for RLS SET LOCAL)
max_client_conn = 1000
default_pool_size = 20
server_idle_timeout = 600
```

**Important:** Use `pool_mode = transaction` (not session) with RLS because
`SET LOCAL app.current_org_id` is transaction-scoped. Session pooling would
leak the org context between requests.

---

## Partitioning Strategy (Scale >100M rows)

For high-volume tables, add range partitioning by month:

```sql
-- email_events: can grow to billions of rows over years
CREATE TABLE email_events (
    -- columns as defined
) PARTITION BY RANGE (occurred_at);

CREATE TABLE email_events_2025_01
    PARTITION OF email_events
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- Automate with pg_partman extension
SELECT partman.create_parent(
    p_parent_table => 'public.email_events',
    p_control => 'occurred_at',
    p_type => 'range',
    p_interval => 'monthly',
    p_premake => 3
);
```

Tables to partition when they exceed ~50M rows:
- `email_events` — partition by `occurred_at`
- `activities` — partition by `occurred_at`
- `events` (analytics) — partition by `occurred_at`
- `audit_logs` — partition by `occurred_at`
- `ai_jobs` — partition by `created_at`

---

## Soft Delete Query Pattern

Every query on business entities must filter `deleted_at IS NULL`.
Enforce this with SQLAlchemy's `with_loader_criteria` in a FastAPI dependency:

```python
# app/db/filters.py
from sqlalchemy.orm import with_loader_criteria
from app.models.base import BaseModel

def active_only_option():
    """Apply soft-delete filter to all BaseModel queries in a session."""
    return with_loader_criteria(
        BaseModel,
        lambda cls: cls.deleted_at.is_(None),
        include_aliases=True,
    )
```

Usage in FastAPI route:

```python
@router.get("/leads")
async def list_leads(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(
        select(Lead)
        .where(Lead.organization_id == current_org_id)
        .execution_options(populate_existing=True),
        execution_options={"loader_criteria": [active_only_option()]}
    )
```

---

## GDPR / PII Erasure Strategy

Soft delete is not sufficient for GDPR "right to erasure" requests.
The strategy:

1. **Anonymize** the Contact record: replace email, name, phone with hashed/null values
2. **Hard delete** RefreshTokens, Sessions, EmailVerificationTokens for the user
3. **Soft delete** the User record (preserve for audit trail FK integrity)
4. **Flag** the Lead as `status=unsubscribed`, anonymize denormalized name/email fields
5. **Retain** AIJob, AuditLog, Invoice rows (legitimate interest / legal obligation)
6. **Document** the erasure in AuditLog with action=`gdpr_erasure`

```python
async def gdpr_erase_contact(session: AsyncSession, contact_id: uuid.UUID) -> None:
    """Anonymize a contact for GDPR erasure."""
    anon_email = f"erased_{contact_id}@deleted.invalid"
    await session.execute(
        update(Contact)
        .where(Contact.id == contact_id)
        .values(
            email=anon_email, first_name="[Erased]", last_name="[Erased]",
            phone=None, linkedin_url=None, deleted_at=func.now()
        )
    )
    # Cascade to Lead denormalized fields
    await session.execute(
        update(Lead)
        .where(Lead.contact_id == contact_id)
        .values(email=anon_email, first_name="[Erased]", last_name="[Erased]", phone=None)
    )
    await session.commit()
```
