from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.database import get_db
from app.models.customer import Customer
from app.models.subscription import Subscription
from app.models.invoice import Invoice
from app.schemas.subscription import SubscriptionResponse, CancelRequest
from app.schemas.invoice import InvoiceResponse
from app.services.subscription_service import cancel_subscription
from typing import List

router = APIRouter()

# Portal uses customer_id directly — no API key needed
# Customers authenticate via a token issued at checkout

@router.get("/customers/{customer_id}/subscription", response_model=SubscriptionResponse)
async def get_my_subscription(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(
            Subscription.customer_id == customer_id,
            Subscription.status.notin_(["cancelled", "expired"]),
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription found")
    return sub

@router.get("/customers/{customer_id}/invoices", response_model=List[InvoiceResponse])
async def get_my_invoices(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Invoice)
        .join(Subscription)
        .where(Subscription.customer_id == customer_id)
        .order_by(Invoice.created_at.desc())
    )
    return result.scalars().all()

@router.post("/customers/{customer_id}/cancel")
async def cancel_my_subscription(
    customer_id: UUID,
    body: CancelRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(
            Subscription.customer_id == customer_id,
            Subscription.status.notin_(["cancelled", "expired"]),
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription found")

    await cancel_subscription(sub.id, sub.tenant_id, db, body.reason)
    return {"message": "Subscription cancelled successfully"}

@router.patch("/customers/{customer_id}/payment-method")
async def update_payment_method(
    customer_id: UUID,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Updates a customer's tokenised card.
    Called after a customer completes a new checkout session
    to update their payment method.
    """
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer.nomba_token = token
    await db.commit()
    return {"message": "Payment method updated successfully"}
