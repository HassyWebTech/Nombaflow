from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.database import get_db
from app.dependencies import get_current_tenant
from app.models.tenant import Tenant
from app.models.webhook import WebhookEndpoint, WebhookDelivery
from app.schemas.webhook import WebhookEndpointCreate, WebhookEndpointResponse, WebhookDeliveryResponse
from app.services.webhook_service import register_endpoint
from app.models.subscription import Subscription
from app.models.customer import Customer
from typing import List
import json

router = APIRouter()

@router.post("/endpoints", response_model=WebhookEndpointResponse, status_code=201)
async def create_endpoint(
    body: WebhookEndpointCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    endpoint = await register_endpoint(
        tenant_id=tenant.id,
        url=body.url,
        events=body.events,
        db=db,
    )
    return endpoint

@router.get("/endpoints", response_model=List[WebhookEndpointResponse])
async def list_endpoints(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebhookEndpoint).where(WebhookEndpoint.tenant_id == tenant.id)
    )
    return result.scalars().all()

@router.delete("/endpoints/{endpoint_id}", status_code=204)
async def delete_endpoint(
    endpoint_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.tenant_id == tenant.id,
        )
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    endpoint.active = False
    await db.commit()

@router.get("/deliveries", response_model=List[WebhookDeliveryResponse])
async def list_deliveries(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebhookDelivery)
        .join(WebhookEndpoint)
        .where(WebhookEndpoint.tenant_id == tenant.id)
        .order_by(WebhookDelivery.created_at.desc())
    )
    return result.scalars().all()

@router.post("/nomba/inbound")
async def nomba_inbound_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Receives webhook events FROM Nomba.
    Nomba calls this endpoint after a checkout is completed
    and returns the tokenised card for the customer.
    """
    payload = await request.json()
    event_type = payload.get("eventType")

    if event_type == "CHECKOUT_ORDER_COMPLETED":
        data = payload.get("data", {})
        token = data.get("cardToken")
        customer_email = data.get("customerEmail")

        if token and customer_email:
            result = await db.execute(
                select(Customer).where(Customer.email == customer_email)
            )
            customer = result.scalar_one_or_none()
            if customer:
                customer.nomba_token = token
                await db.commit()

    return {"received": True}
