# Deployment guide

This guide deploys SalesPilot AI to a public URL using the services that already
exist in this repo (`apps/web`, `apps/api`, plus the `worker`/`beat` services added
by `prompts/13-langgraph-agents.txt`) with no re-architecture. It assumes modules
04 and 13 are implemented — without them there is no Celery task to run and this
guide has nothing to deploy beyond a CRUD API.

Primary recommendation: **Railway** for everything except the Next.js frontend,
which goes to **Vercel**. Reasoning is in each section below, and a VPS/Fly.io
alternative is covered at the end for when you outgrow the managed-platform tier.

---

## 0. What "public and will actually work" requires

Five things people get wrong with exactly this stack (FastAPI + Celery + Redis +
Postgres + Next.js + WebSockets), stated up front so you don't hit them:

1. **The FastAPI/WebSocket backend cannot go on Vercel, Netlify, or any serverless
   function platform.** Serverless functions don't hold a persistent WebSocket
   connection open — the live agent-status streaming from prompt 13 will silently
   never connect. The API needs a platform that runs a long-lived process
   (Railway, Render, Fly.io, or a VPS all qualify).
2. **Celery `worker` and `beat` are separate processes from the API**, not
   background threads inside it. If you only deploy `api`, every AI job, campaign
   step, and metrics rollup from prompts 04-12 will queue forever and never run.
   Your current `docker-compose.yml` doesn't even define these services yet —
   prompt 13 adds them; deploy both.
3. **Local disk file storage does not survive a redeploy on Railway/Render.**
   `app/services/storage_service.py` currently writes attachments/logos to
   `uploads/` on local disk, backed in Docker Compose by the `api_uploads` named
   volume. On a managed platform, a redeploy usually gives you a fresh
   filesystem. Two options: (a) Railway supports attaching a persistent Volume to
   a service — mount it at the same `upload_dir` path and this keeps working
   as-is; (b) migrate `storage_service.py` to an S3-compatible bucket
   (Cloudflare R2 is cheap and S3-API-compatible) — more correct long-term, more
   work now. Pick (a) to ship fast, note (b) as follow-up debt.
4. **The frontend and API are typically on different domains/origins in this
   split.** Your Axios client already uses `withCredentials: true` for cookie
   auth — cross-origin cookies require `SameSite=None; Secure` and matching
   `cors_origins` on the API. WebSocket auth via cookies has the same
   cross-origin caveat (see prompt 13's note on this) — plan to either put both
   services behind one domain via a reverse proxy, or pass a short-lived token on
   the WebSocket handshake instead of relying on the cookie.
5. **`docker compose up` locally must work with the new `worker`/`beat` services
   before you deploy anything** — if a research job doesn't visibly execute
   locally, it will not execute in production either; production just hides the
   failure behind "nothing happens" instead of an obvious local error.

---

## 1. Architecture you're deploying

```
                              ┌─────────────────┐
     Browser ──HTTPS/WSS──▶   │   api (FastAPI)  │──┐
        │                     └─────────────────┘  │
        │                              │             │
        ▼                              ▼             ▼
  ┌───────────┐               ┌───────────────┐  ┌──────────┐
  │ web (Next)│               │ worker (Celery)│  │  beat    │
  │  Vercel   │               │   Railway      │  │ Railway  │
  └───────────┘               └───────┬───────┘  └────┬─────┘
                                       │                │
                              ┌────────▼────────────────▼───┐
                              │   Redis (broker + pub/sub)   │
                              └───────────────┬───────────────┘
                                               │
                                     ┌─────────▼─────────┐
                                     │  Postgres (managed) │
                                     └─────────────────────┘
```

Five deployable units: `web`, `api`, `worker`, `beat`, plus managed `postgres` and
`redis`. `worker` and `beat` use the exact same Docker image as `api` — only the
container `command` differs (see prompt 13's docker-compose additions).

---

## 2. Prerequisites

- A GitHub repo with this project pushed (Railway/Vercel both deploy from a
  connected repo).
- A Railway account (railway.app) — free trial credit, then usage-based billing.
- A Vercel account (vercel.com) — free tier is enough to start.
- Your LLM provider API key(s) (Anthropic and/or OpenAI, from prompt 04/13).
- A domain name if you want a custom domain (optional at first — both platforms
  give you a working subdomain for free).

---

## 3. Deploy the database and Redis (Railway)

1. Create a new Railway project.
2. Add a **PostgreSQL** plugin from Railway's template gallery — this gives you a
   managed Postgres instance with a `DATABASE_URL`-shaped connection string
   Railway generates automatically. Copy it; you'll set it as an env var on `api`/
   `worker`/`beat` momentarily (Railway's "Reference Variables" feature lets you
   point one service's env var at another service's generated value, so you
   don't have to hand-copy it — use that instead of pasting the raw string, so
   password rotation doesn't require touching four services).
3. Add a **Redis** plugin the same way.
4. Note: Railway's generated Postgres URL uses `postgresql://`, but your
   `Settings.database_url` in `app/core/config.py` expects the `asyncpg` driver
   prefix (`postgresql+asyncpg://`, per how `docker-compose.yml` already
   overrides it for the `api` service). Set the env var explicitly as
   `postgresql+asyncpg://...` using Railway's reference-variable syntax to
   rewrite the prefix, or add a small startup-time string replace in
   `get_settings()` if you'd rather not touch Railway's raw value — pick one and
   be consistent.

---

## 4. Deploy `api` (Railway)

1. In the same Railway project, add a new service from your GitHub repo.
2. Set the build to use `apps/api/Dockerfile` with build context `./apps/api`
   (Railway's service settings let you point at a subdirectory Dockerfile —
   matches exactly what `docker-compose.yml` already does locally).
3. Environment variables (mirror `apps/api/.env.example` plus everything prompts
   04/07/10/13 added — set every one of these on Railway's service Variables tab):

   ```
   ENVIRONMENT=production
   DATABASE_URL=postgresql+asyncpg://...        (reference var from step 3)
   REDIS_URL=${{Redis.REDIS_URL}}                (Railway reference syntax)
   JWT_SECRET_KEY=<generate a real 32+ char secret, never reuse the dev one>
   CORS_ORIGINS=https://<your-vercel-domain>
   SECURE_COOKIES=true
   FRONTEND_URL=https://<your-vercel-domain>
   API_BASE_URL=https://<your-railway-api-domain>

   # SMTP (transactional — auth emails)
   SMTP_HOST=... SMTP_PORT=587 SMTP_USERNAME=... SMTP_PASSWORD=...
   SMTP_FROM_EMAIL=no-reply@yourdomain.com SMTP_FROM_NAME=SalesPilot

   # Outreach sending (prompt 07 — separate from transactional SMTP above)
   OUTREACH_SMTP_HOST=... OUTREACH_SMTP_USERNAME=... OUTREACH_SMTP_PASSWORD=...
   OUTREACH_DAILY_SEND_LIMIT_DEFAULT=100
   UNSUBSCRIBE_TOKEN_SECRET=<separate secret from JWT_SECRET_KEY>

   # AI providers (prompt 04/13)
   ANTHROPIC_API_KEY=sk-ant-...
   OPENAI_API_KEY=sk-...
   AI_DEFAULT_PROVIDER=anthropic
   AI_DEFAULT_MODEL=claude-sonnet-5

   # Calendar (prompt 10, once implemented)
   GOOGLE_CALENDAR_CLIENT_ID=...
   GOOGLE_CALENDAR_CLIENT_SECRET=...
   GOOGLE_CALENDAR_REDIRECT_URI=https://<your-railway-api-domain>/api/v1/integrations/google-calendar/callback

   UPLOAD_DIR=/app/uploads
   ```

4. **Attach a Volume** (Railway → service → Volumes tab) mounted at `/app/uploads`
   so uploaded logos/attachments survive redeploys (see §0 point 3).
5. **Run the database migration as a release step**, not manually: set Railway's
   "Deploy" pre-start command (or a `railway.json`/`Procfile` release phase, per
   Railway's current release-command feature) to run
   `alembic upgrade head` before the `uvicorn` process starts. If Railway's UI in
   your account version doesn't expose a distinct release phase, wrap it in the
   container's entrypoint: run migrations, then exec into `uvicorn`.
6. Health check: point Railway's health check at
   `GET /api/v1/health/live` (already exists per your Phase 1 acceptance checks)
   so a bad deploy doesn't get traffic.
7. Note the public URL Railway assigns (e.g. `salespilot-api-production.up.
   railway.app`) — this is your `NEXT_PUBLIC_API_URL` root for the frontend, and
   confirm WebSocket connections work at
   `wss://salespilot-api-production.up.railway.app/api/v1/ws/ai-jobs/{id}` —
   Railway proxies WebSocket upgrades transparently, no extra config needed
   (this is the reason Railway/Render beat serverless platforms for this stack).

---

## 5. Deploy `worker` and `beat` (Railway)

Add two more services in the same Railway project, both from the **same repo and
Dockerfile** as `api` (`apps/api/Dockerfile`, context `./apps/api`) — the only
difference is the start command:

- `worker` service → override start command to
  `celery -A app.workers.celery_app worker --loglevel=info --concurrency=4`
- `beat` service → override start command to
  `celery -A app.workers.celery_app beat --loglevel=info`

Both need the **same environment variables as `api`** (`DATABASE_URL`,
`REDIS_URL`, all the AI/email/calendar keys) — Celery tasks need the same
settings the API does to do their work. Use Railway's "Reference Variables" or
its variable-group/shared-environment feature (naming varies by current Railway
UI) to avoid manually duplicating 20+ env vars across three services and having
them drift out of sync.

Neither `worker` nor `beat` needs a public domain/port exposed — they connect
outbound to Postgres/Redis only. Leave networking private.

**Verify it's actually running**: after deploy, check the `worker` service's
logs for Celery's startup banner and registered task list. Trigger one AI job
from the frontend (once modules 04+13 are live) and confirm the job transitions
out of `PENDING` in the `worker` logs within seconds — "the container started"
is not sufficient verification, per prompt 13's own testing checklist.

---

## 6. Deploy `web` (Vercel)

1. Import the repo into Vercel, set the project root to `apps/web` (Vercel
   supports monorepo subdirectory roots directly — no need to restructure).
2. Environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://<your-railway-api-domain>/api/v1
   ```
3. Vercel auto-detects Next.js and uses your existing `apps/web/Dockerfile`-
   equivalent build (or its native Next.js build pipeline — either works;
   Vercel's native build is typically simpler than pointing it at your Docker
   image, since Vercel's platform is optimized specifically for Next.js output).
4. This is fine on Vercel specifically because `web` makes outbound HTTP/WS
   requests to `api` (on Railway) rather than needing to host a persistent
   connection itself — the constraint in §0 point 1 applies to the WebSocket
   *server*, not a WebSocket *client* running in the browser via a Vercel-served
   page.

Alternative: if you'd rather keep everything on one platform, deploy `web` on
Railway too, using `apps/web/Dockerfile` as-is. Vercel is the recommendation
because its Next.js-specific optimizations (image handling, edge caching,
preview deployments per PR) are meaningfully better for a Next.js app
specifically — but it's not a hard requirement.

---

## 7. Cross-origin auth (the part most likely to silently break)

Your `web` domain (Vercel) and `api` domain (Railway) are different origins.
Confirm end-to-end, not just in code:

- `Settings.cors_origins` on the API includes the exact Vercel URL (no trailing
  slash, matching the existing `parse_origins` validator's normalization).
- `Settings.secure_cookies = True` in production, and cookies set with
  `SameSite=None` for cross-origin — verify wherever cookies are actually set in
  `app/auth/cookies.py` (or equivalent) uses this correctly; `SameSite=None`
  requires `Secure`, which requires HTTPS everywhere (Railway/Vercel both give
  you HTTPS by default, so this is satisfied automatically once
  `secure_cookies` is on).
- WebSocket auth (prompt 13): if you kept the cookie-based approach, verify the
  browser actually attaches the cookie on the WebSocket handshake to a
  cross-origin host — this is inconsistent across browsers/configurations, and
  is exactly why prompt 13 flags using a short-lived query-param/subprotocol
  token as the safer default for a cross-origin deployment like this one. If
  live status silently doesn't connect in production but works in local dev
  (where everything is same-origin `localhost`), this is almost certainly why —
  check it first.
- If you want to eliminate this whole class of bug, put both services behind one
  domain via a reverse proxy (e.g. `app.yourdomain.com` → Vercel,
  `app.yourdomain.com/api` → Railway, using Vercel's rewrites feature or a
  Cloudflare proxy in front of both) so everything is same-origin. This is more
  setup now but removes an entire category of cross-origin cookie/WebSocket bugs
  — worth it once you're past the initial "get it live" milestone.

---

## 8. Custom domain + TLS

Both Railway and Vercel provision free TLS certificates automatically once you
point a domain at them:

1. Buy/use your domain (any registrar).
2. Vercel: Project → Settings → Domains → add `app.yourdomain.com`, follow the
   CNAME instructions Vercel shows.
3. Railway: service → Settings → Networking → add your custom domain (e.g.
   `api.yourdomain.com`), follow the CNAME instructions Railway shows.
4. Update `CORS_ORIGINS`, `FRONTEND_URL`, `API_BASE_URL`, and
   `NEXT_PUBLIC_API_URL` to the final custom domains once DNS propagates, redeploy
   both services.

Until you're ready for a custom domain, the free `*.up.railway.app` and
`*.vercel.app` subdomains work fully — including HTTPS/WSS — so you can ship and
demo to a client today without owning a domain yet.

---

## 9. Cost ballpark (as of writing; confirm current pricing before committing)

- Railway: usage-based. `api` + `worker` + `beat` + small Postgres + small Redis
  for a low-traffic MVP typically lands in the **$15-30/month** range on
  Railway's Hobby/Pro usage pricing — the always-on `worker`/`beat` processes are
  the main cost driver since they run continuously even when idle (Celery beat
  in particular never scales to zero).
- Vercel: free Hobby tier is sufficient until you have real production traffic.
- LLM API costs are separate and usage-driven — this is exactly what module 04's
  `AIJob.cost_usd` tracking and module 12's cost dashboard are for; watch it
  from day one.

---

## 10. Post-deploy smoke test

Run through this by hand after every first deploy to a new environment:

1. `GET https://<api-domain>/api/v1/health/live` → `{ "success": true }`.
2. Register a new user on the live frontend, verify the email arrives (SMTP is
   wired correctly).
3. Log in, confirm the session persists across a page refresh (cookie/CORS is
   correct).
4. Trigger one AI research job on a test lead; confirm it completes (worker is
   actually consuming the queue) and the live step timeline updates in the
   browser (WebSocket connects cross-origin correctly).
5. Upload a logo/attachment, redeploy the `api` service, confirm the file is
   still reachable afterward (the Volume mount is working).
6. Send one test outreach email to an address you control; confirm the
   unsubscribe link works and the tracking pixel fires an open event.

If step 4 or 6 fails but the rest pass, it's almost always the cross-origin
WebSocket/cookie issue from §7 — check that first before anything else.

---

## 11. When you outgrow Railway: VPS alternative

Once traffic/cost justifies it, your existing `docker-compose.yml` (plus the
`worker`/`beat` services from prompt 13) already **is** a working VPS deployment
— that's the point of building it that way. On a Hetzner/DigitalOcean box:

1. `docker compose up -d --build` runs the whole stack as-is.
2. Put Caddy (simplest — automatic Let's Encrypt TLS with a ~5-line Caddyfile) in
   front of `web` and `api` on the same box, routing by subdomain.
3. Use a managed Postgres/Redis add-on from the same VPS provider instead of the
   in-compose containers for production durability (automated backups), or
   self-manage backups if running Postgres in a container long-term (`pg_dump`
   on a cron, shipped off-box).
4. You now own uptime/monitoring/patching yourself — budget for that operational
   time, not just the lower hosting bill.

This is strictly a later-stage move, not a starting recommendation — Railway's
managed Postgres/Redis, automatic TLS, and zero-ops restart/health-check
behavior are worth the price premium while you're still validating the product
with early clients.
