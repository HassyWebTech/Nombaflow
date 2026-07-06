from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

class SubscriptionCreate(BaseModel):
    customer_id: UUID
    plan_id: UUID
    trial_days: int = Field(0, example=14)

class SubscriptionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    customer_id: UUID
    plan_id: UUID
    status: str
    current_period_start: datetime
    current_period_end: datetime
    trial_end: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PlanChangeRequest(BaseModel):
    new_plan_id: UUID

class CancelRequest(BaseModel):
    reason: Optional[str] = "customer_request"
