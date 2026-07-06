from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

class PlanCreate(BaseModel):
    name: str = Field(..., example="Starter Monthly")
    interval: str = Field(..., example="month")  # month, year, day
    interval_count: int = Field(1, example=1)
    amount: int = Field(..., example=500000)  # in kobo — ₦5,000
    currency: str = Field("NGN", example="NGN")

class PlanUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None  # active, archived

class PlanResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    interval: str
    interval_count: int
    amount: int
    currency: str
    status: str
    version: int
    created_at: datetime

    class Config:
        from_attributes = True
