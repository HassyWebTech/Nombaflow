from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID, uuid4
from app.database import get_db
from app.dependencies import get_current_tenant
from app.models.tenant import Tenant
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerResponse, CheckoutSessionResponse
from app.nomba.checkout import create_checkout_session
from typing import List

router = APIRouter()

@router.post("/", response_model=CustomerResponse, status_code=201)
async def create_customer(
    body: CustomerCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    # Check for duplicate email within tenant
    result = await db.execute(
        select(Customer).where(
            Customer.email == body.email,
            Customer.tenant_id == tenant.id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Customer with this email already exists")

    customer = Customer(**body.model_dump(), tenant_id=tenant.id)
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return {**customer.__dict__, "has_payment_method": bool(customer.nomba_token)}

@router.get("/", response_model=List[CustomerResponse])
async def list_customers(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Customer).where(Customer.tenant_id == tenant.id)
    )
    customers = result.scalars().all()
    return [{**c.__dict__, "has_payment_method": bool(c.nomba_token)} for c in customers]

@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant.id
        )
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {**customer.__dict__, "has_payment_method": bool(customer.nomba_token)}

@router.post("/{customer_id}/checkout", response_model=CheckoutSessionResponse)
async def create_checkout(
    customer_id: UUID,
    plan_id: UUID,
    callback_url: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a Nomba checkout session for first-time card tokenisation.
    Customer pays via checkout → Nomba tokenises the card → webhook returns token.
    """
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant.id
        )
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    from app.models.plan import Plan
    plan = await db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    reference = f"nombaflow-checkout-{uuid4().hex[:12]}"

    session = await create_checkout_session(
        amount=plan.amount,
        currency=plan.currency,
        reference=reference,
        customer_email=customer.email,
        callback_url=callback_url,
    )

    return {
        "checkout_url": session["data"]["checkoutLink"],
        "reference": reference,
        "customer_id": customer_id,
    }
