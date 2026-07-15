from celery import Celery
from app.core.config import get_settings
celery_app = Celery("salespilot", broker=get_settings().redis_url, backend=get_settings().redis_url)
# No tasks are registered in Phase 1; this is the intentionally empty async boundary.
