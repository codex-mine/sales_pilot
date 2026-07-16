# Delivery roadmap

## Phase 1 — Foundation (complete when the acceptance checks below pass)

- Local and Docker startup, PostgreSQL/Redis connectivity, health checks, and initial schema bootstrap.
- Tenant-aware identity models and working authentication: registration, email verification flow, login, rotating refresh cookies, logout, password reset, password change, and `/me`.
- Dashboard shell and stable API response/error conventions.

### Phase 1 acceptance checks

1. `docker compose up --build` leaves `web`, `api`, `postgres`, and `redis` running.
2. `GET /api/v1/health/live` returns `{ "success": true }`.
3. A user can complete the complete local authentication sequence in [local development](local-development.md).
4. Tokens are never returned by production endpoints except the short-lived access token returned at login/refresh; reset and verification tokens must be delivered by an email adapter.

## Phase 1.1 — Operational hardening

Before a shared staging deployment, add Alembic baseline migrations, a transactional-email provider adapter, structured JSON logging with correlation IDs, rate limiting backed by Redis, CSRF protection for cookie-authenticated mutations, and integration tests against PostgreSQL. Do not begin sales features before these are deployed.

## Phase 2 — Tenant and lead-data foundation

Implement organization provisioning, invitation acceptance, role enforcement, settings, lead import validation, audit events, and a background-job outbox. Every new query must require an organization scope and every state change must produce an audit event. Still no sending, AI research, or campaigns.

## Phase 3 — Research and AI orchestration

Introduce provider-agnostic LLM interfaces, model configuration per organization, company-enrichment interfaces, prompt/version storage, approval workflows, observability, cost controls, and human review. Keep all writes idempotent and all agent runs traceable.

## Phase 4 — Outreach execution

Add sender-domain connection, mailbox health controls, email generation approval, scheduling, follow-up state machines, unsubscribe/suppression support, delivery/reply webhooks, and strict rate limits. This phase requires security review and compliance sign-off.

## Phase 5 — CRM, meetings, and analytics

Add CRM synchronization, calendar availability and booking, dashboard metrics, reporting pipelines, and operational alerts. These consumers should read well-defined domain events rather than reach into campaign tables directly.

## Definition of ready for each next phase

- Approved database migration and rollback plan.
- API contract and permission model documented.
- Unit and integration coverage for the new state transitions.
- Audit logging, tenant isolation, error handling, and observability verified.
- No future phase is coupled directly to internal persistence details of a previous feature.