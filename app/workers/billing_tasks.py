from app.workers.celery_app import celery_app

@celery_app.task(name="app.workers.billing_tasks.process_due_subscriptions")
def process_due_subscriptions():
    """
    Runs every 60s. Finds subscriptions where current_period_end <= now
    and status = active, then triggers a charge.
    Implemented fully in billing_service.py
    """
    from app.services.billing_service import run_due_billing_cycles
    run_due_billing_cycles()
