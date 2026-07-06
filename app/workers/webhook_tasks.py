from app.workers.celery_app import celery_app

@celery_app.task(name="app.workers.webhook_tasks.deliver_webhook")
def deliver_webhook(delivery_id: str):
    """
    Sends a signed webhook payload to a merchant's registered endpoint.
    Retries up to 5 times with backoff on failure.
    """
    from app.services.webhook_service import send_delivery
    send_delivery(delivery_id)
