"""
Celery application for asynchronous work.

Queues:
- `ai` — LLM job execution (app/workers/ai_tasks.py). Isolated in its own
  queue so long-running provider calls never compete with future
  email-sending or scheduler workers.

Run a worker locally with:
  celery -A app.workers.celery_app worker --loglevel=info -Q ai,celery
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
    task_routes={"ai.*": {"queue": "ai"}},
    task_time_limit=get_settings().ai_job_timeout_seconds * 2,
    task_soft_time_limit=get_settings().ai_job_timeout_seconds,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["app.workers"])

# Import task modules explicitly so a worker started with this app instance
# always has them registered even if autodiscovery misses a packaging edge.
from app.workers import ai_tasks  # noqa: E402,F401
