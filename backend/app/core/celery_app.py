from celery import Celery
from app.core.config import settings

# Initialize Celery app with Redis broker and backend
celery_app = Celery(
    "document_intelligence_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure Celery execution parameters
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Clean up results after 1 day to prevent Redis memory growth
    result_expires=86400,
    # Explicitly import the tasks package
    imports=("app.tasks",)
)

# Auto-discover tasks defined in packages (e.g. app/tasks/)
celery_app.autodiscover_tasks(["app"])
