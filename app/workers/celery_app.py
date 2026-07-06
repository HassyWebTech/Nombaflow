from celery import Celery
from app.config import settings

celery_app = Celery(
    "nombaflow",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.billing_tasks",
        "app.workers.dunning_tasks",
        "app.workers.webhook_tasks",
    ]
)

celery_app.conf.beat_schedule = {
    "process-billing-cycles": {
        "task": "app.workers.billing_tasks.process_due_subscriptions",
        "schedule": 60.0,  # runs every 60 seconds
    },
}

celery_app.conf.timezone = "Africa/Lagos"
