from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.invoice import Invoice
from app.models.subscription import Subscription
from app.models.customer import Customer
from app.models.plan import Plan
from app.models.dunning_attempt import DunningAttempt
from app.services.webhook_service import emit_event
from app.database import AsyncSessionLocal


# ---------------------------------------------------------------------------
# Dunning retry schedule
# Day offsets from the original failure date.
# Attempt 1 → retry after 1 day
# Attempt 2 → retry after 3 days
# Attempt 3 → retry after 7 days
# Attempt 4 → retry after 14 days → then cancel
# ---------------------------------------------------------------------------
RETRY_SCHEDULE = [1, 3, 7, 14]

# Failure reasons where retrying is pointless
# No point retrying a card that is expired or reported stolen
DO_NOT_RETRY_REASONS = [
    "card_expired",
    "card_stolen",
    "card_blocked",
    "do_not_honor",
    "invalid_card",
]


# ---------------------------------------------------------------------------
# Initiate dunning after a first charge failure
# Creates the first dunning attempt and schedules the retry
# ---------------------------------------------------------------------------
async def initiate_dunning(
    invoice: Invoice,
    subscription: Subscription,
    db: AsyncSession,
):
    failure_reason = invoice.status  # "failed"

    # Check if this failure reason is worth retrying
    # If card is expired, skip straight to notifying the customer
    if _should_not_retry(failure_reason):
        await _escalate_to_cancelled(subscription, invoice, db, reason=failure_reason)
        return

    # Schedule first retry — 1 day from now
    next_retry_at = datetime.utcnow() + timedelta(days=RETRY_SCHEDULE[0])

    attempt = DunningAttempt(
        invoice_id=invoice.id,
        attempt_number=1,
        status="pending",
        failure_reason=None,
        next_retry_at=next_retry_at,
    )
    db.add(attempt)
    await db.commit()

    # Schedule the Celery retry task
    _schedule_retry_task(str(invoice.id), next_retry_at)

    # Notify customer — payment failed, we will retry
    await emit_event(
        tenant_id=subscription.tenant_id,
        event_type="dunning.started",
        payload={
            "subscription_id": str(subscription.id),
            "invoice_id": str(invoice.id),
            "next_retry_at": next_retry_at.isoformat(),
            "attempt_number": 1,
        },
        db=db,
    )


# ---------------------------------------------------------------------------
# Execute a dunning retry
# Called by the Celery dunning_tasks worker
# ---------------------------------------------------------------------------
def attempt_retry(invoice_id: str):
    """Sync wrapper for Celery."""
    import asyncio
    asyncio.run(_execute_retry(invoice_id))


async def _execute_retry(invoice_id: str):
    async with AsyncSessionLocal() as db:
        # Load invoice
        invoice = await db.get(Invoice, invoice_id)
        if not invoice or invoice.status == "paid":
            return  # Already paid by other means, skip

        # Load latest dunning attempt for this invoice
        result = await db.execute(
            select(DunningAttempt)
            .where(DunningAttempt.invoice_id == invoice_id)
            .order_by(DunningAttempt.attempt_number.desc())
        )
        latest_attempt = result.scalar_one_or_none()
        if not latest_attempt:
            return

        # Load subscription and related data
        subscription = await db.get(Subscription, invoice.subscription_id)
        customer = await db.get(Customer, subscription.customer_id)
        plan = await db.get(Plan, subscription.plan_id)

        if not subscription or not customer or not plan:
            return

        # Mark this attempt as in-progress
        latest_attempt.status = "attempting"
        latest_attempt.attempted_at = datetime.utcnow()
        await db.commit()

        # Import here to avoid circular imports
        from app.services.billing_service import attempt_charge

        success = await attempt_charge(invoice, subscription, customer, plan, db)

        if success:
            # Charge succeeded — mark attempt as success, dunning is over
            latest_attempt.status = "success"
            await db.commit()

            await emit_event(
                tenant_id=subscription.tenant_id,
                event_type="dunning.recovered",
                payload={
                    "subscription_id": str(subscription.id),
                    "invoice_id": str(invoice.id),
                    "attempt_number": latest_attempt.attempt_number,
                    "recovered_at": datetime.utcnow().isoformat(),
                },
                db=db,
            )
        else:
            # Charge failed again — decide whether to retry or cancel
            latest_attempt.status = "failed"
            await db.commit()
            await _handle_retry_failure(invoice, subscription, latest_attempt, db)


# ---------------------------------------------------------------------------
# Handle a failed retry — schedule next retry or cancel
# ---------------------------------------------------------------------------
async def _handle_retry_failure(
    invoice: Invoice,
    subscription: Subscription,
    failed_attempt: DunningAttempt,
    db: AsyncSession,
):
    attempt_number = failed_attempt.attempt_number
    max_attempts = len(RETRY_SCHEDULE)

    if attempt_number >= max_attempts:
        # Exhausted all retries — cancel the subscription
        await _escalate_to_cancelled(
            subscription, invoice, db,
            reason=f"dunning_exhausted_after_{max_attempts}_attempts"
        )
        return

    # Schedule next retry using the schedule
    days_until_retry = RETRY_SCHEDULE[attempt_number]  # next index
    next_retry_at = datetime.utcnow() + timedelta(days=days_until_retry)

    next_attempt = DunningAttempt(
        invoice_id=invoice.id,
        attempt_number=attempt_number + 1,
        status="pending",
        next_retry_at=next_retry_at,
    )
    db.add(next_attempt)
    await db.commit()

    # Schedule next Celery task
    _schedule_retry_task(str(invoice.id), next_retry_at)

    # Notify customer — payment still failing, next retry scheduled
    await emit_event(
        tenant_id=subscription.tenant_id,
        event_type="dunning.retry_scheduled",
        payload={
            "subscription_id": str(subscription.id),
            "invoice_id": str(invoice.id),
            "attempt_number": attempt_number + 1,
            "next_retry_at": next_retry_at.isoformat(),
            "attempts_remaining": max_attempts - attempt_number - 1,
        },
        db=db,
    )


# ---------------------------------------------------------------------------
# Final escalation — cancel the subscription after dunning is exhausted
# ---------------------------------------------------------------------------
async def _escalate_to_cancelled(
    subscription: Subscription,
    invoice: Invoice,
    db: AsyncSession,
    reason: str,
):
    from app.services.subscription_service import transition_subscription

    await transition_subscription(
        subscription, "cancelled", db, reason=reason
    )

    await emit_event(
        tenant_id=subscription.tenant_id,
        event_type="dunning.failed",
        payload={
            "subscription_id": str(subscription.id),
            "invoice_id": str(invoice.id),
            "reason": reason,
            "cancelled_at": datetime.utcnow().isoformat(),
        },
        db=db,
    )


# ---------------------------------------------------------------------------
# Schedule a Celery retry task at a specific time
# ---------------------------------------------------------------------------
def _schedule_retry_task(invoice_id: str, eta: datetime):
    from app.workers.dunning_tasks import retry_failed_invoice
    retry_failed_invoice.apply_async(args=[invoice_id], eta=eta)


# ---------------------------------------------------------------------------
# Check if a failure reason should skip retrying entirely
# ---------------------------------------------------------------------------
def _should_not_retry(reason: str) -> bool:
    if not reason:
        return False
    return any(skip in reason.lower() for skip in DO_NOT_RETRY_REASONS)
