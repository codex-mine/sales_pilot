# SalesPilot

Production-minded Phase 1 foundation for a multi-tenant AI SDR SaaS. This repository deliberately contains identity, organization boundaries, API conventions, and a dashboard shell—not sales automation or AI features.

## Quick start

1. Copy `.env.example` to `.env` and replace `JWT_SECRET_KEY`.
2. Run `docker compose up --build`.
3. Open `http://localhost:3000`; API health is at `http://localhost:8000/api/v1/health/live`.

uvicorn app.main:app --host 0.0.0.0 --port 8000

## Repository layout

```
apps/web       Next.js 15 application and feature-first UI
apps/api       FastAPI service, domain models, security and API modules
packages/      Reserved shared UI, types, config and cross-cutting contracts
docker/        Deployment assets (Nginx can be added here)
docs/          Architecture and contributor documentation
scripts/       Developer automation
```

## Architecture

The API is versioned under `/api/v1`, returns a consistent `success/data/message/errors/meta` envelope, and is organized by boundaries rather than technical dumping grounds. SQLAlchemy models define the initial identity and tenancy layer. Opaque refresh tokens are stored hashed, while short-lived access tokens are JWTs. Future services should use organization-scoped repository queries and dependency injection.

## Development standards

- TypeScript is strict; do not introduce `any`.
- Validate all external input with Zod (web) and Pydantic (API).
- Keep endpoints thin and put behavior in focused services.
- Never log credentials, JWTs, or raw refresh tokens.
- Add migrations through Alembic before shipping model changes.

See [architecture notes](docs/architecture.md) and [contributing guide](docs/contributing.md).


## Running locally

Follow the [local development guide](docs/local-development.md) for Docker, non-Docker, database reset, and the full authentication flow. The planned delivery sequence is in the [roadmap](docs/roadmap.md).
