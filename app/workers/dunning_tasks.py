from app.workers.celery_app import celery_app

@celery_app.task(name="app.workers.dunning_tasks.retry_failed_invoice")
def retry_failed_invoice(invoice_id: str):
    """
    Retries a failed invoice charge.
    Called by dunning_service after computing next_retry_at.
    """
    from app.services.dunning_service import attempt_retry
    attempt_retry(invoice_id)
