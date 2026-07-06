from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.database import get_db
from app.dependencies import get_current_tenant
from app.models.tenant import Tenant
from app.models.subscription import Subscription
from app.schemas.subscription import (
    SubscriptionCreate, SubscriptionResponse,
    PlanChangeRequest, CancelRequest
)
from app.services.subscription_service import (
    create_subscription, cancel_subscription,
    pause_subscription, resume_subscription
)
from app.services.proration_service import upgrade_plan, downgrade_plan
from typing import List

router = APIRouter()

@router.post("/", response_model=SubscriptionResponse, status_code=201)
async def subscribe(
    body: SubscriptionCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    subscription = await create_subscription(
        tenant_id=tenant.id,
        customer_id=body.customer_id,
        plan_id=body.plan_id,
        db=db,
        trial_days=body.trial_days,
    )
    return subscription

@router.get("/", response_model=List[SubscriptionResponse])
async def list_subscriptions(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(Subscription.tenant_id == tenant.id)
    )
    return result.scalars().all()

@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.tenant_id == tenant.id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return sub

@router.post("/{subscription_id}/cancel", response_model=SubscriptionResponse)
async def cancel(
    subscription_id: UUID,
    body: CancelRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await cancel_subscription(subscription_id, tenant.id, db, body.reason)

@router.post("/{subscription_id}/pause", response_model=SubscriptionResponse)
async def pause(
    subscription_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await pause_subscription(subscription_id, tenant.id, db)

@router.post("/{subscription_id}/resume", response_model=SubscriptionResponse)
async def resume(
    subscription_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await resume_subscription(subscription_id, tenant.id, db)

@router.post("/{subscription_id}/upgrade")
async def upgrade(
    subscription_id: UUID,
    body: PlanChangeRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.tenant_id == tenant.id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return await upgrade_plan(sub, body.new_plan_id, db)

@router.post("/{subscription_id}/downgrade")
async def downgrade(
    subscription_id: UUID,
    body: PlanChangeRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.tenant_id == tenant.id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return await downgrade_plan(sub, body.new_plan_id, db)
