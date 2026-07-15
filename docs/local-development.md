# Local development

## Prerequisites

- Docker Desktop with Compose enabled (recommended), or Node.js 20+ and Python 3.12+.
- Copy `.env.example` to `.env`. The checked-in `.env` is development-only; replace `JWT_SECRET_KEY` before sharing the project.

## Start with Docker

```powershell
# From the repository root
docker compose up --build
```

Open `http://localhost:3000`. The API is available at `http://localhost:8000`, and interactive API documentation is at `http://localhost:8000/docs`.

Check service status:

```powershell
docker compose ps
Invoke-RestMethod http://localhost:8000/api/v1/health/live
```

The API creates the initial local database schema during startup when `ENVIRONMENT=development`. In staging and production, run Alembic migrations before starting the API. To start fresh locally (this deletes all local data):

```powershell
docker compose down -v
docker compose up --build
```

## Start without Docker

```powershell
# Terminal 1: PostgreSQL and Redis must be running locally, then set their URLs in .env
npm install
npm run dev:web

# Terminal 2
cd apps/api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

## Exercise authentication locally

The API intentionally returns a one-time verification/reset token in `meta.development_token` only when `ENVIRONMENT=development`; this is the local replacement for an email provider.

1. `POST /api/v1/auth/register` with `{ "email": "owner@example.com", "password": "A-strong-password1", "full_name": "Owner" }`.
2. Send `meta.development_token` to `POST /api/v1/auth/verify-email` as `{ "token": "..." }`.
3. `POST /api/v1/auth/login`; preserve the `refresh_token` cookie and use `data.access_token` as `Authorization: Bearer <token>`.
4. Call `GET /api/v1/auth/me`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/change-password`, and `POST /api/v1/auth/logout`.
5. `POST /api/v1/auth/forgot-password` returns a development token; submit it to `POST /api/v1/auth/reset-password`.

Never enable development-token output outside a local environment. Staging/production need a transactional-email adapter before their email verification/reset flows can be delivered to end users.