from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.subscription import Subscription
from app.models.plan import Plan
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.services.webhook_service import emit_event


# ---------------------------------------------------------------------------
# Valid state transitions
# Only these moves are legal. Any other transition raises an error.
# ---------------------------------------------------------------------------
VALID_TRANSITIONS = {
    "trialing":  ["active", "cancelled"],
    "active":    ["past_due", "paused", "cancelled"],
    "past_due":  ["active", "cancelled"],
    "paused":    ["active", "cancelled"],
    "cancelled": [],   # terminal state — no exit
    "expired":   [],   # terminal state — no exit
}


# ---------------------------------------------------------------------------
# Core state transition function
# Every status change in the system goes through this function.
# Nothing changes a subscription status directly — always use this.
# ---------------------------------------------------------------------------
async def transition_subscription(
    subscription: Subscription,
    new_status: str,
    db: AsyncSession,
    reason: str = None,
) -> Subscription:
    current = subscription.status
    allowed = VALID_TRANSITIONS.get(current, [])

    if new_status not in allowed:
        raise ValueError(
            f"Invalid transition: {current} → {new_status}. "
            f"Allowed from {current}: {allowed}"
        )

    old_status = subscription.status
    subscription.status = new_status

    # Record cancellation timestamp
    if new_status == "cancelled":
        subscription.cancelled_at = datetime.utcnow()

    await db.commit()
    await db.refresh(subscription)

    # Emit webhook event so downstream systems know about the change
    await emit_event(
        tenant_id=subscription.tenant_id,
        event_type=f"subscription.{new_status}",
        payload={
            "subscription_id": str(subscription.id),
            "customer_id": str(subscription.customer_id),
            "plan_id": str(subscription.plan_id),
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        },
        db=db,
    )

    return subscription


# ---------------------------------------------------------------------------
# Create a new subscription
# Called when a customer subscribes to a plan for the first time.
# ---------------------------------------------------------------------------
async def create_subscription(
    tenant_id: UUID,
    customer_id: UUID,
    plan_id: UUID,
    db: AsyncSession,
    trial_days: int = 0,
) -> Subscription:
    # Load the plan to get billing interval
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise ValueError(f"Plan {plan_id} not found")

    if plan.status != "active":
        raise ValueError(f"Plan {plan_id} is not active")

    now = datetime.utcnow()

    # Calculate first billing period
    period_end = _calculate_period_end(now, plan.interval, plan.interval_count)

    # If trial, subscription starts as trialing
    initial_status = "trialing" if trial_days > 0 else "active"
    trial_end = now + timedelta(days=trial_days) if trial_days > 0 else None

    subscription = Subscription(
        tenant_id=tenant_id,
        customer_id=customer_id,
        plan_id=plan_id,
        status=initial_status,
        current_period_start=now,
        current_period_end=period_end,
        trial_end=trial_end,
    )

    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)

    # Emit creation event
    await emit_event(
        tenant_id=tenant_id,
        event_type="subscription.created",
        payload={
            "subscription_id": str(subscription.id),
            "customer_id": str(customer_id),
            "plan_id": str(plan_id),
            "status": initial_status,
            "current_period_end": period_end.isoformat(),
        },
        db=db,
    )

    return subscription


# ---------------------------------------------------------------------------
# Renew a subscription after a successful charge
# Advances the billing period to the next cycle.
# ---------------------------------------------------------------------------
async def renew_subscription(
    subscription: Subscription,
    db: AsyncSession,
) -> Subscription:
    plan = await db.get(Plan, subscription.plan_id)

    # Advance the billing window
    new_start = subscription.current_period_end
    new_end = _calculate_period_end(
        new_start, plan.interval, plan.interval_count
    )

    subscription.current_period_start = new_start
    subscription.current_period_end = new_end

    # Ensure status is active after successful renewal
    if subscription.status != "active":
        await transition_subscription(subscription, "active", db, reason="payment_succeeded")
    else:
        await db.commit()
        await db.refresh(subscription)

    return subscription


# ---------------------------------------------------------------------------
# Cancel a subscription
# ---------------------------------------------------------------------------
async def cancel_subscription(
    subscription_id: UUID,
    tenant_id: UUID,
    db: AsyncSession,
    reason: str = "customer_request",
) -> Subscription:
    subscription = await _get_subscription(subscription_id, tenant_id, db)
    return await transition_subscription(subscription, "cancelled", db, reason=reason)


# ---------------------------------------------------------------------------
# Pause a subscription
# ---------------------------------------------------------------------------
async def pause_subscription(
    subscription_id: UUID,
    tenant_id: UUID,
    db: AsyncSession,
) -> Subscription:
    subscription = await _get_subscription(subscription_id, tenant_id, db)
    return await transition_subscription(subscription, "paused", db)


# ---------------------------------------------------------------------------
# Resume a paused subscription
# ---------------------------------------------------------------------------
async def resume_subscription(
    subscription_id: UUID,
    tenant_id: UUID,
    db: AsyncSession,
) -> Subscription:
    subscription = await _get_subscription(subscription_id, tenant_id, db)
    return await transition_subscription(subscription, "active", db, reason="resumed")


# ---------------------------------------------------------------------------
# Mark subscription as past_due when a charge fails
# Called by billing_service when Nomba returns a failed charge.
# ---------------------------------------------------------------------------
async def mark_past_due(
    subscription: Subscription,
    db: AsyncSession,
) -> Subscription:
    return await transition_subscription(
        subscription, "past_due", db, reason="charge_failed"
    )


# ---------------------------------------------------------------------------
# Helper: calculate next period end based on plan interval
# ---------------------------------------------------------------------------
def _calculate_period_end(
    from_date: datetime,
    interval: str,
    interval_count: int,
) -> datetime:
    if interval == "day":
        return from_date + timedelta(days=interval_count)
    elif interval == "month":
        # Add months properly
        month = from_date.month - 1 + interval_count
        year = from_date.year + month // 12
        month = month % 12 + 1
        day = min(from_date.day, _days_in_month(year, month))
        return from_date.replace(year=year, month=month, day=day)
    elif interval == "year":
        return from_date.replace(year=from_date.year + interval_count)
    else:
        raise ValueError(f"Unknown interval: {interval}")


def _days_in_month(year: int, month: int) -> int:
    import calendar
    return calendar.monthrange(year, month)[1]


# ---------------------------------------------------------------------------
# Helper: fetch and validate subscription belongs to tenant
# ---------------------------------------------------------------------------
async def _get_subscription(
    subscription_id: UUID,
    tenant_id: UUID,
    db: AsyncSession,
) -> Subscription:
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.tenant_id == tenant_id,
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise ValueError(f"Subscription {subscription_id} not found")
    return subscription
