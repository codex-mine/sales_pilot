"""
Celery application for asynchronous work.

Queues:
- `ai` — LLM job execution (app/workers/ai_tasks.py). Isolated in its own
  queue so long-running provider calls never compete with future
  email-sending or scheduler workers.
- `research` — Company Research / Prospect Analysis orchestration
  (app/workers/research_tasks.py). These tasks poll `ai`-queue jobs until
  terminal and then finalize (parse structured output into CompanyResearch /
  ProspectAnalysis) — kept off the `ai` queue so a chain of waits here never
  blocks LLM job execution.
- `email` — Email Generation orchestration (app/workers/email_tasks.py).
  Same poll-then-finalize shape as `research`, splitting a generated
  variants array into individually-approvable AIOutput rows.
- `sending` — Email Sending dispatch (app/workers/email_sending_tasks.py).
  A Celery-beat periodic task finds due SCHEDULED emails and fans out a
  per-row send task; isolated in its own queue so a burst of outbound sends
  never competes with LLM/orchestration work on the other queues.
- `metrics` — Email Tracking analytics aggregation
  (app/workers/email_metrics_tasks.py). One hourly Celery-beat task per
  worker cycle; isolated so a slow aggregation pass never delays sends.
- `inbox` — Inbox reply-classification finalize (app/workers/inbox_tasks.py).
  Same poll-then-finalize shape as `research`/`email`, applying
  classification side effects once the `ai`-queue job completes.
- `meetings` — Meeting Scheduling & Calendar Booking internal reminders
  (app/workers/meeting_tasks.py). One periodic Celery-beat task per worker
  cycle, isolated so it never competes with the other queues.
- `campaigns` — Multi-Step Sequence Automation (app/workers/
  campaign_scheduler_tasks.py). `dispatch_due_campaign_steps` runs every 60
  seconds and claims due CampaignLead rows with `SELECT ... FOR UPDATE SKIP
  LOCKED` (see models/ARCHITECTURE.md §3), fanning out one
  `execute_campaign_step` per row — isolated in its own queue since a step
  that waits on AI generation can run considerably longer than this queue's
  usual tasks.
- `analytics` — Dashboard/Reports Metric aggregation (app/workers/
  analytics_tasks.py). `aggregate_daily_metrics` runs once daily (01:00 UTC)
  and writes the pipeline/AI-cost/campaign/meeting Metric rows the module 12
  dashboard reads; `check_scheduled_reports` runs hourly and delivers any
  due saved Report — isolated so a slow daily aggregation pass never delays
  the other queues' usual sub-minute tasks.

Run a worker locally with:
  celery -A app.workers.celery_app worker --loglevel=info -Q ai,research,email,sending,metrics,inbox,meetings,campaigns,analytics,celery
Run beat (for scheduled sends + hourly metrics) alongside it with:
  celery -A app.workers.celery_app beat --loglevel=info
"""

import asyncio

from celery import Celery
from celery.schedules import crontab

from app.core.asyncio_compat import ensure_selector_event_loop_policy
from app.core.config import get_settings

# Same Windows/psycopg-async note as app/main.py — each task's
# `asyncio.run(...)` (see app/workers/session_utils.py) creates a fresh loop
# per invocation, so the policy must be set once here at worker-process
# import time, before the first task ever runs.
ensure_selector_event_loop_policy()

# Same "must run once, before any task could hold an open transaction"
# requirement as app/main.py's lifespan — see `bootstrap_checkpoint_tables`'s
# docstring. In a real Celery worker process, this module is imported
# exactly once at true cold start (no event loop running yet), so
# `asyncio.run(...)` here is that process's bootstrap point. In the API
# process and in tests, though, this module is imported *lazily* — from
# inside `AIJobService.run_job`'s non-eager dispatch branch, itself already
# running inside an event loop (FastAPI's/pytest-asyncio's) — where
# `asyncio.run()` would raise; skip in that case, since that caller's own
# process already bootstrapped the tables itself (`app/main.py`'s lifespan,
# or the test suite's session-scoped schema fixture).
from app.agents.base import bootstrap_checkpoint_tables  # noqa: E402

try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.run(bootstrap_checkpoint_tables())

celery_app = Celery(
    "salespilot",
    broker=get_settings().redis_url,
    backend=get_settings().redis_url,
)

celery_app.conf.update(
    task_default_queue="celery",
    task_routes={
        "ai.*": {"queue": "ai"},
        "research.*": {"queue": "research"},
        "email.*": {"queue": "email"},
        "sending.*": {"queue": "sending"},
        "metrics.*": {"queue": "metrics"},
        "inbox.*": {"queue": "inbox"},
        "meetings.*": {"queue": "meetings"},
        "campaigns.*": {"queue": "campaigns"},
        "analytics.*": {"queue": "analytics"},
    },
    task_time_limit=get_settings().ai_job_timeout_seconds * 2,
    task_soft_time_limit=get_settings().ai_job_timeout_seconds,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "dispatch-due-scheduled-emails": {
            "task": "sending.dispatch_due_scheduled_emails",
            "schedule": 60.0,
        },
        "aggregate-email-metrics": {
            "task": "metrics.aggregate_email_metrics",
            "schedule": 3600.0,
        },
        "send-meeting-reminders": {
            "task": "meetings.send_reminders",
            "schedule": 900.0,
        },
        "dispatch-due-campaign-steps": {
            "task": "campaigns.dispatch_due_steps",
            "schedule": 60.0,
        },
        "aggregate-daily-metrics": {
            "task": "analytics.aggregate_daily_metrics",
            "schedule": crontab(hour=1, minute=0),
        },
        "check-scheduled-reports": {
            "task": "analytics.check_scheduled_reports",
            "schedule": 3600.0,
        },
    },
)

celery_app.autodiscover_tasks(["app.workers"])

# Import task modules explicitly so a worker started with this app instance
# always has them registered even if autodiscovery misses a packaging edge.
from app.workers import ai_tasks  # noqa: E402,F401
from app.workers import analytics_tasks  # noqa: E402,F401
from app.workers import campaign_scheduler_tasks  # noqa: E402,F401
from app.workers import email_tasks  # noqa: E402,F401
from app.workers import email_metrics_tasks  # noqa: E402,F401
from app.workers import email_sending_tasks  # noqa: E402,F401
from app.workers import inbox_tasks  # noqa: E402,F401
from app.workers import meeting_tasks  # noqa: E402,F401
from app.workers import research_tasks  # noqa: E402,F401
