from datetime import datetime
from uuid import UUID
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.subscription import Subscription
from app.models.invoice import Invoice
from app.models.customer import Customer
from app.models.plan import Plan
from app.nomba.charge import charge_tokenised_card
from app.services.subscription_service import renew_subscription, mark_past_due
from app.services.dunning_service import initiate_dunning
from app.services.webhook_service import emit_event
from app.database import AsyncSessionLocal


# ---------------------------------------------------------------------------
# Main entry point — called by Celery Beat every 60 seconds
# Finds all subscriptions due for billing and charges them
# ---------------------------------------------------------------------------
def run_due_billing_cycles():
    """
    Synchronous wrapper for Celery.
    Celery workers are sync by default — we run the async logic inside here.
    """
    import asyncio
    asyncio.run(_process_due_subscriptions())


async def _process_due_subscriptions():
    async with AsyncSessionLocal() as db:
        now = datetime.utcnow()

        # Find all active subscriptions whose billing period has ended
        result = await db.execute(
            select(Subscription).where(
                Subscription.status == "active",
                Subscription.current_period_end <= now,
            )
        )
        due_subscriptions = result.scalars().all()

        for subscription in due_subscriptions:
            await _bill_subscription(subscription, db)


# ---------------------------------------------------------------------------
# Bill a single subscription
# Creates an invoice and attempts to charge the customer
# ---------------------------------------------------------------------------
async def _bill_subscription(
    subscription: Subscription,
    db: AsyncSession,
):
    # Load related data
    customer = await db.get(Customer, subscription.customer_id)
    plan = await db.get(Plan, subscription.plan_id)

    if not customer or not plan:
        return

    # Customer has no tokenised card — can't charge
    if not customer.nomba_token:
        await mark_past_due(subscription, db)
        return

    # Create invoice before attempting charge
    # This way we have a record even if the charge fails
    invoice = Invoice(
        tenant_id=subscription.tenant_id,
        subscription_id=subscription.id,
        amount=plan.amount,
        currency=plan.currency,
        status="pending",
        due_date=subscription.current_period_end,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)

    # Attempt the charge
    await attempt_charge(invoice, subscription, customer, plan, db)


# ---------------------------------------------------------------------------
# Attempt a charge against Nomba
# Used by both billing_service (first attempt) and dunning_service (retries)
# ---------------------------------------------------------------------------
async def attempt_charge(
    invoice: Invoice,
    subscription: Subscription,
    customer: Customer,
    plan: Plan,
    db: AsyncSession,
) -> bool:
    """
    Returns True if charge succeeded, False if it failed.
    """
    # Unique reference per charge attempt — required by Nomba for idempotency
    charge_reference = f"nombaflow-{invoice.id}-{uuid.uuid4().hex[:8]}"

    try:
        result = await charge_tokenised_card(
            token=customer.nomba_token,
            amount=invoice.amount,
            currency=invoice.currency,
            reference=charge_reference,
            customer_email=customer.email,
        )

        # Nomba returned a success response
        if result.get("code") == "00":
            await _handle_charge_success(
                invoice, subscription, charge_reference, db
            )
            return True
        else:
            failure_reason = result.get("description", "unknown_error")
            await _handle_charge_failure(
                invoice, subscription, failure_reason, db
            )
            return False

    except Exception as e:
        await _handle_charge_failure(
            invoice, subscription, str(e), db
        )
        return False


# ---------------------------------------------------------------------------
# Handle a successful charge
# ---------------------------------------------------------------------------
async def _handle_charge_success(
    invoice: Invoice,
    subscription: Subscription,
    charge_reference: str,
    db: AsyncSession,
):
    # Mark invoice as paid
    invoice.status = "paid"
    invoice.nomba_charge_ref = charge_reference
    invoice.paid_at = datetime.utcnow()
    await db.commit()

    # Advance the subscription to the next billing period
    await renew_subscription(subscription, db)

    # Notify downstream systems
    await emit_event(
        tenant_id=subscription.tenant_id,
        event_type="invoice.paid",
        payload={
            "invoice_id": str(invoice.id),
            "subscription_id": str(subscription.id),
            "amount": invoice.amount,
            "currency": invoice.currency,
            "charge_reference": charge_reference,
            "paid_at": datetime.utcnow().isoformat(),
        },
        db=db,
    )


# ---------------------------------------------------------------------------
# Handle a failed charge
# ---------------------------------------------------------------------------
async def _handle_charge_failure(
    invoice: Invoice,
    subscription: Subscription,
    failure_reason: str,
    db: AsyncSession,
):
    # Mark invoice as failed
    invoice.status = "failed"
    await db.commit()

    # Move subscription to past_due
    await mark_past_due(subscription, db)

    # Notify downstream systems
    await emit_event(
        tenant_id=subscription.tenant_id,
        event_type="invoice.failed",
        payload={
            "invoice_id": str(invoice.id),
            "subscription_id": str(subscription.id),
            "amount": invoice.amount,
            "failure_reason": failure_reason,
            "timestamp": datetime.utcnow().isoformat(),
        },
        db=db,
    )

    # Start dunning — schedule first retry
    await initiate_dunning(invoice, subscription, db)


# ---------------------------------------------------------------------------
# Manually trigger a charge for a specific subscription
# Used by the portal when a customer updates their card and retries payment
# ---------------------------------------------------------------------------
async def manual_charge(
    subscription_id: UUID,
    tenant_id: UUID,
    db: AsyncSession,
) -> bool:
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.tenant_id == tenant_id,
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise ValueError(f"Subscription {subscription_id} not found")

    customer = await db.get(Customer, subscription.customer_id)
    plan = await db.get(Plan, subscription.plan_id)

    # Get the latest unpaid invoice or create a new one
    invoice_result = await db.execute(
        select(Invoice).where(
            Invoice.subscription_id == subscription_id,
            Invoice.status.in_(["pending", "failed"]),
        )
    )
    invoice = invoice_result.scalar_one_or_none()

    if not invoice:
        invoice = Invoice(
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            amount=plan.amount,
            currency=plan.currency,
            status="pending",
            due_date=datetime.utcnow(),
        )
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)

    return await attempt_charge(invoice, subscription, customer, plan, db)
