# SalesPilot AI — Complete Architecture Reference

## Domain Breakdown & Design Rationale

---

### 1. IDENTITY DOMAIN

**Tables:** Organization, Team, User, Role, Permission, UserRole, RolePermission,
TeamMember, Session, RefreshToken, PasswordResetToken, EmailVerificationToken

**Core decisions:**

**Organization as the tenant boundary.**
Every business entity carries `organization_id`. This single FK is the tenant
discriminator for both application-level filtering and RLS policies. We chose
a shared database / shared schema model (vs separate schemas per tenant) because:
- Simpler ops (one migration for all tenants)
- PgBouncer connection pooling works uniformly
- Cross-org analytics at the DB layer (for Anthropic-level reporting)
- RLS + `app.current_org_id` session variable provides isolation

**Per-org RBAC.**
Roles belong to organizations. Built-in roles (owner, admin, member, viewer)
are seeded at org creation as `is_system=True` rows. Custom roles can be added.
This mirrors how HubSpot and Salesforce handle permissions — enterprise customers
need "Custom Sales Role" and "Read-Only Partner" without code changes.

**Session + RefreshToken dual model.**
Short-lived JWTs (15 min) for stateless access + server-side Session records
for revocability. This is the standard pattern for B2B SaaS. Pure stateless JWTs
can't be revoked without a blacklist (which is just a session table anyway).

---

### 2. CRM DOMAIN

**Tables:** Company, Contact, Lead, LeadScore, Tag, LeadTag, Note, Activity, Attachment

**Core decisions:**

**Three-level CRM: Company → Contact → Lead.**
This mirrors Apollo, HubSpot, and Attio. The separation matters because:
- A Company may have many Contacts across different campaigns
- A Contact may be in multiple campaigns simultaneously
- Company research is done once and reused across all leads at that company
- The same person (Contact) can be a lead for different products/campaigns

**Lead as a denormalized read-optimized record.**
Lead stores copies of first_name, last_name, email, company_name for fast
list queries without joins. These are synced from Contact/Company at import
and on update. This is deliberate denormalization — justified by the fact that
the lead list view is the most-accessed page in the entire application.

**Activity as append-only event log.**
We never update Activity rows. Each state transition, email event, AI action,
and manual note creates a new Activity row. This gives us a complete, auditable
timeline. It also supports real-time feed updates (SSE/WebSocket) trivially:
just subscribe to INSERTs on the activities table.

**LeadScore as a history table.**
Scores are AI-generated and can change as new data arrives. By keeping a
full history (newest first), we can show score trends on the lead detail page
and use historical scores to train better scoring models later.

---

### 3. CAMPAIGNS DOMAIN

**Tables:** Campaign, Sequence, SequenceStep, EmailTemplate, CampaignLead

**Core decisions:**

**Campaign → Sequence → SequenceStep hierarchy.**
A Campaign is the business objective ("Close 20 SaaS startups in Q1").
A Sequence is the playbook ("5-touch cold outreach over 15 days").
A SequenceStep is one action ("Day 1: Send cold email using template X").
This three-level hierarchy allows sequences to be reused across campaigns
and steps to reference shared templates.

**CampaignLead as the enrollment record.**
`CampaignLead.next_action_at` is the Celery scheduler's primary query target.
Every 60 seconds, the scheduler finds rows where `next_action_at <= now` and
`status = in_progress`. After executing a step, it sets the next `next_action_at`
based on the next step's `delay_days`.

**`WITH FOR UPDATE SKIP LOCKED` on the scheduler query.**
This PostgreSQL feature prevents multiple Celery workers from processing the
same CampaignLead simultaneously. Worker 1 locks row A; Worker 2 skips it
and takes row B instead. No distributed lock manager needed.

**EmailTemplate decoupled from SequenceStep.**
Templates are reusable assets. A step references a template but can also
override the subject and body for one-off customization. This avoids copying
template content into every step.

---

### 4. COMMUNICATION DOMAIN

**Tables:** Email, EmailEvent, Conversation, Message, Meeting, CalendarEvent

**Core decisions:**

**Outgoing (Email) and Incoming (Message) are separate tables.**
Outgoing emails have delivery tracking, scheduling, AI generation flags, and
template references. Incoming messages have reply classification and AI
suggested actions. Merging them into one table would require many nullable
columns and conditional logic. Separate tables → clean domain models.

**EmailEvent as append-only delivery timeline.**
This models email delivery the same way Stripe models payment events: each
state transition is a new immutable row. The webhook handler inserts an event;
a post-insert trigger (or application code) updates the cached `Email.current_status`.
Advantages: full audit trail, idempotent webhook handling via `provider_event_id`
unique constraint, accurate time-to-open/click metrics.

**Meeting vs CalendarEvent split.**
Meeting = our intent (we want to meet with this lead on these proposed times).
CalendarEvent = the external system's confirmed record.
A Meeting exists before a CalendarEvent (during the proposal phase).
Once confirmed, the CalendarEvent is created and linked.
This prevents our data model from depending on the calendar provider's
availability — if Google Calendar goes down, our Meeting record is intact.

---

### 5. AI DOMAIN

**Tables:** AIAgent, AIJob, AIOutput, CompanyResearch, ProspectAnalysis,
           PromptTemplate, PromptVersion, AIMemory

**Core decisions:**

**AIJob as the central audit record for all LLM calls.**
Every call to any LLM creates an AIJob row with full metadata:
provider, model, tokens, cost, latency, input payload, error (if failed).
This enables:
- Cost dashboards ("We spent $847 on AI this month, mostly on email generation")
- Debugging ("Why did this email look wrong? View the exact input sent to GPT")
- Replay ("Re-run this job with the same input but a newer model")
- Billing ("We used 1.2M tokens in March — upgrade needed")

**AIOutput separate from AIJob.**
One job can produce multiple outputs (3 email variants, 5 pain points).
Outputs can be individually approved/rejected by users.
Outputs can be large (full research report) — keeping them separate prevents
the AIJob analytics table from becoming bloated.

**PromptTemplate + PromptVersion = Git-like versioning.**
A PromptTemplate is the "file" (concept + name). A PromptVersion is the
"commit" (immutable snapshot of the actual prompt text at a point in time).
We never edit a PromptVersion; we create new ones. The AIJob records which
PromptVersion it used. This makes regression testing straightforward:
compare output quality across version_number 1 vs 2 vs 3.

**CompanyResearch and ProspectAnalysis as typed tables.**
Generic AIOutput handles unstructured text. But Company research and Prospect
analysis have well-known schemas with individual columns that are queried
and displayed in the UI. A typed table with proper columns is more maintainable
than JSON extraction from a generic output row.

**AIMemory + ChromaDB hybrid.**
AIMemory stores the text + metadata in PostgreSQL (filterable, joinable, backupable).
The vector embedding lives in ChromaDB (or pgvector if preferred).
Query pattern: filter in PostgreSQL first (organization + entity + memory_type),
then pass candidate IDs to ChromaDB for reranking by similarity.
Pure vector stores don't support relational filtering efficiently.

---

### 6. AUTOMATION DOMAIN

**Tables:** Workflow, WorkflowExecution, ScheduledJob

**Core decisions:**

**Workflows use JSONB for steps (V1).**
In V1, workflow steps are simple enough to represent as a JSON array.
This avoids a complex WorkflowStep table with a self-referential tree structure.
If workflows become complex (branching, conditions, sub-workflows), introduce
a proper WorkflowStep table in V2 — the JSONB column is a pragmatic starting point.

**ScheduledJob is distinct from Celery beat.**
Celery beat handles system-level schedules (run every 60 seconds).
ScheduledJob handles user-configurable recurring tasks (send weekly report every
Monday at 9am in the user's timezone). These are computed into absolute timestamps
stored in `next_run_at` and picked up by a Celery task that runs every minute.

---

### 7. ANALYTICS DOMAIN

**Tables:** Event, Metric, Report, DashboardWidget

**Core decisions:**

**Two-tier analytics: Event (raw) + Metric (aggregated).**
Raw events are written on every user/system action. A nightly Celery task
aggregates them into Metric rows (daily/weekly/monthly counts and rates).
Dashboard queries read from Metric (fast, pre-computed) not from Event
(slow, requires GROUP BY over millions of rows).

**Events table is not partitioned in V1.**
At 10k leads × 10 events each = 100k rows — fine for a simple index.
Add monthly partitioning when the table exceeds ~10M rows.

---

### 8. BILLING DOMAIN

**Tables:** Plan, Subscription, Invoice, Payment, UsageRecord

**Core decisions:**

**Mirror Stripe data locally.**
We don't rely on Stripe as the source of truth for billing state.
Every Invoice and Payment is mirrored locally via Stripe webhooks.
Reasons: faster billing page loads (no Stripe API call), billing data
available even during Stripe outages, join with local business data
for custom reporting.

**UsageRecord for metered billing.**
V1 uses seat-based billing. But we track usage (AI jobs, emails sent)
from day one so we can switch to usage-based pricing in V2 without a schema change.
UsageRecord rows are reported to Stripe's metered billing API.

---

## Relationship Summary

```
Organization (1) ────────── (N) Team
Organization (1) ────────── (N) User
Organization (1) ─────── (0..1) Subscription
Organization (1) ────────── (N) Campaign
Organization (1) ────────── (N) Company

Team (N) ──────────────── (N) User          [TeamMember]
User (N) ──────────────── (N) Role          [UserRole]
Role (N) ──────────────── (N) Permission    [RolePermission]

Company (1) ───────────── (N) Contact
Company (1) ───────────── (N) Lead
Company (1) ─────────── (0..1) CompanyResearch

Contact (1) ───────────── (N) Lead
Lead (1) ───────────────── (N) LeadScore
Lead (N) ──────────────── (N) Tag           [LeadTag]
Lead (1) ───────────────── (N) Activity
Lead (1) ───────────────── (N) Note
Lead (1) ───────────────── (N) Email
Lead (1) ───────────────── (N) Meeting
Lead (1) ─────────────── (0..1) ProspectAnalysis
Lead (1) ───────────────── (N) CampaignLead

Campaign (1) ──────────── (N) Sequence
Sequence (1) ──────────── (N) SequenceStep
SequenceStep (N) ─────── (0..1) EmailTemplate
Campaign (1) ──────────── (N) CampaignLead  [enrollment]
CampaignLead (1) ─────── (N) Email

Email (1) ─────────────── (N) EmailEvent    [append-only]
Lead (1) ───────────────── (N) Conversation
Conversation (1) ─────── (N) Message        [incoming replies]
Meeting (1) ────────────── (0..1) CalendarEvent

AIAgent (1) ──────────── (N) AIJob
AIJob (1) ────────────── (N) AIOutput
AIJob (1) ──────────── (0..1) AIJob         [parent/child orchestration]
PromptTemplate (1) ────── (N) PromptVersion
AIJob (N) ─────────────── (1) PromptVersion

Workflow (1) ─────────── (N) WorkflowExecution
Subscription (1) ─────── (N) Invoice
Subscription (1) ─────── (N) UsageRecord
Invoice (1) ─────────── (N) Payment
```

---

## V2 Extensibility Considerations

The schema is designed so these V2 features require additive changes only
(new tables, new columns) — not destructive schema rewrites:

| V2 Feature | Schema Impact |
|---|---|
| LinkedIn outreach | Add `linkedin_message` to SequenceStepTypeEnum; new LinkedInEvent table |
| WhatsApp campaigns | New WhatsAppMessage table; add `whatsapp` to SequenceStepTypeEnum |
| A/B testing | Add `ab_group` to CampaignLead; add `variant_id` to Sequence |
| Multi-language emails | Add `language` to EmailTemplate; new TranslationJob table |
| Voice call summaries | New CallRecording + CallTranscript tables; Activity entry |
| Lead scoring history | Already supported — LeadScore is a history table |
| AI-generated proposals | New Proposal table; ProposalJob in AIJob.job_type |
| Team permissions | Already supported — RolePermission is the extension point |
| White-label branding | Add branding JSONB columns to Organization |
| Custom fields | Already supported — Lead.custom_fields is JSONB |
| Webhook triggers | Workflow.trigger_event can be any event string |
| Multi-org users | Add OrganizationMembership table (N:M User ↔ Organization) |
| Email provider switching | Integration table already provider-agnostic |
| Usage-based billing | UsageRecord already tracks all metered events |
