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

Run a worker locally with:
  celery -A app.workers.celery_app worker --loglevel=info -Q ai,research,email,sending,metrics,inbox,celery
Run beat (for scheduled sends + hourly metrics) alongside it with:
  celery -A app.workers.celery_app beat --loglevel=info
"""

from celery import Celery

from app.core.config import get_settings

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
    },
)

celery_app.autodiscover_tasks(["app.workers"])

# Import task modules explicitly so a worker started with this app instance
# always has them registered even if autodiscovery misses a packaging edge.
from app.workers import ai_tasks  # noqa: E402,F401
from app.workers import email_tasks  # noqa: E402,F401
from app.workers import email_metrics_tasks  # noqa: E402,F401
from app.workers import email_sending_tasks  # noqa: E402,F401
from app.workers import inbox_tasks  # noqa: E402,F401
from app.workers import research_tasks  # noqa: E402,F401
