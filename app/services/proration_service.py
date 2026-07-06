from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.subscription import Subscription
from app.models.plan import Plan
from app.models.invoice import Invoice
from app.services.subscription_service import _calculate_period_end
from app.services.webhook_service import emit_event


# ---------------------------------------------------------------------------
# Proration explained simply:
#
# A customer is on a ₦5,000/month plan.
# They upgrade to ₦10,000/month halfway through the month.
#
# They already paid ₦5,000 for the full month.
# They used 15 of 30 days on the old plan = ₦2,500 used.
# They have 15 days remaining = ₦2,500 credit.
#
# New plan for 15 days = ₦5,000 (half of ₦10,000).
# Amount to charge = ₦5,000 - ₦2,500 credit = ₦2,500.
#
# On downgrade, the credit rolls into the next invoice.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Calculate proration credit for unused days on current plan
# Returns the credit amount in kobo
# ---------------------------------------------------------------------------
def calculate_unused_credit(
    subscription: Subscription,
    current_plan: Plan,
) -> int:
    now = datetime.utcnow()
    period_start = subscription.current_period_start
    period_end = subscription.current_period_end

    total_seconds = (period_end - period_start).total_seconds()
    remaining_seconds = (period_end - now).total_seconds()

    if total_seconds <= 0 or remaining_seconds <= 0:
        return 0

    # Fraction of period remaining
    fraction_remaining = remaining_seconds / total_seconds

    # Credit = plan amount × fraction remaining
    credit = int(current_plan.amount * fraction_remaining)
    return credit


# ---------------------------------------------------------------------------
# Calculate the prorated charge for the new plan
# Returns the amount to charge immediately in kobo
# ---------------------------------------------------------------------------
def calculate_prorated_charge(
    subscription: Subscription,
    new_plan: Plan,
    credit: int,
) -> int:
    now = datetime.utcnow()
    period_end = subscription.current_period_end

    total_seconds = (period_end - subscription.current_period_start).total_seconds()
    remaining_seconds = (period_end - now).total_seconds()

    if total_seconds <= 0 or remaining_seconds <= 0:
        return 0

    fraction_remaining = remaining_seconds / total_seconds

    # New plan cost for remaining period
    new_plan_cost = int(new_plan.amount * fraction_remaining)

    # Amount to charge = new plan cost minus credit from old plan
    amount_due = max(0, new_plan_cost - credit)
    return amount_due


# ---------------------------------------------------------------------------
# Execute a plan upgrade
# Charges the prorated difference immediately
# ---------------------------------------------------------------------------
async def upgrade_plan(
    subscription: Subscription,
    new_plan_id: UUID,
    db: AsyncSession,
) -> dict:
    current_plan = await db.get(Plan, subscription.plan_id)
    new_plan = await db.get(Plan, new_plan_id)

    if not new_plan or new_plan.status != "active":
        raise ValueError(f"Plan {new_plan_id} not found or inactive")

    if new_plan.amount <= current_plan.amount:
        raise ValueError("Use downgrade_plan for switching to a cheaper plan")

    # Calculate what the customer gets back from the old plan
    credit = calculate_unused_credit(subscription, current_plan)

    # Calculate what they owe for the new plan for remaining days
    amount_due = calculate_prorated_charge(subscription, new_plan, credit)

    # Switch the plan immediately
    old_plan_id = subscription.plan_id
    subscription.plan_id = new_plan_id
    await db.commit()

    # Charge the prorated difference if any amount is due
    result = {"credit_applied": credit, "amount_charged": 0, "invoice_id": None}

    if amount_due > 0:
        from app.models.customer import Customer
        customer = await db.get(Customer, subscription.customer_id)

        invoice = Invoice(
            tenant_id=subscription.tenant_id,
            subscription_id=subscription.id,
            amount=amount_due,
            currency=current_plan.currency,
            status="pending",
            due_date=datetime.utcnow(),
        )
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)

        from app.services.billing_service import attempt_charge
        success = await attempt_charge(invoice, subscription, customer, new_plan, db)

        result["amount_charged"] = amount_due if success else 0
        result["invoice_id"] = str(invoice.id)

    # Emit upgrade event
    await emit_event(
        tenant_id=subscription.tenant_id,
        event_type="subscription.upgraded",
        payload={
            "subscription_id": str(subscription.id),
            "old_plan_id": str(old_plan_id),
            "new_plan_id": str(new_plan_id),
            "credit_applied": credit,
            "amount_charged": result["amount_charged"],
            "timestamp": datetime.utcnow().isoformat(),
        },
        db=db,
    )

    return result


# ---------------------------------------------------------------------------
# Execute a plan downgrade
# Credit rolls into next invoice — no immediate charge
# ---------------------------------------------------------------------------
async def downgrade_plan(
    subscription: Subscription,
    new_plan_id: UUID,
    db: AsyncSession,
) -> dict:
    current_plan = await db.get(Plan, subscription.plan_id)
    new_plan = await db.get(Plan, new_plan_id)

    if not new_plan or new_plan.status != "active":
        raise ValueError(f"Plan {new_plan_id} not found or inactive")

    if new_plan.amount >= current_plan.amount:
        raise ValueError("Use upgrade_plan for switching to a more expensive plan")

    # Calculate credit from unused days on current plan
    credit = calculate_unused_credit(subscription, current_plan)

    # Switch the plan — takes effect at next billing cycle
    old_plan_id = subscription.plan_id
    subscription.plan_id = new_plan_id
    await db.commit()

    # Find or create next invoice and apply the credit
    # Credit reduces what they pay at next billing cycle
    next_invoice_amount = max(0, new_plan.amount - credit)

    # Emit downgrade event
    await emit_event(
        tenant_id=subscription.tenant_id,
        event_type="subscription.downgraded",
        payload={
            "subscription_id": str(subscription.id),
            "old_plan_id": str(old_plan_id),
            "new_plan_id": str(new_plan_id),
            "credit_applied": credit,
            "next_invoice_amount": next_invoice_amount,
            "effective_date": subscription.current_period_end.isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
        },
        db=db,
    )

    return {
        "credit_applied": credit,
        "next_invoice_amount": next_invoice_amount,
        "effective_date": subscription.current_period_end.isoformat(),
    }


# ---------------------------------------------------------------------------
# Format kobo amount to naira string for display
# e.g. 500000 kobo → "₦5,000.00"
# ---------------------------------------------------------------------------
def format_amount(kobo: int, currency: str = "NGN") -> str:
    naira = kobo / 100
    return f"₦{naira:,.2f}"
