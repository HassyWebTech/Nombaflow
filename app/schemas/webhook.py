from pydantic import BaseModel, HttpUrl, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

class WebhookEndpointCreate(BaseModel):
    url: str = Field(..., example="https://yourapp.com/webhooks/nombaflow")
    events: str = Field("*", example="subscription.active,invoice.paid")

class WebhookEndpointResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    url: str
    events: str
    secret: str   # shown once at creation
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class WebhookDeliveryResponse(BaseModel):
    id: UUID
    endpoint_id: UUID
    event_type: str
    status_code: Optional[int] = None
    attempt_count: int
    delivered_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
