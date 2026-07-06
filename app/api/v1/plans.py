from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.database import get_db
from app.dependencies import get_current_tenant
from app.models.tenant import Tenant
from app.models.plan import Plan
from app.schemas.plan import PlanCreate, PlanUpdate, PlanResponse
from typing import List

router = APIRouter()

@router.post("/", response_model=PlanResponse, status_code=201)
async def create_plan(
    body: PlanCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    plan = Plan(**body.model_dump(), tenant_id=tenant.id)
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan

@router.get("/", response_model=List[PlanResponse])
async def list_plans(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Plan).where(Plan.tenant_id == tenant.id)
    )
    return result.scalars().all()

@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id, Plan.tenant_id == tenant.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan

@router.patch("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: UUID,
    body: PlanUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Plan).where(Plan.id == plan_id, Plan.tenant_id == tenant.id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(plan, field, value)

    await db.commit()
    await db.refresh(plan)
    return plan
