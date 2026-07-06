from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

class CustomerCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., example="Amaka Obi")

class CustomerResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    name: str
    has_payment_method: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    reference: str
    customer_id: UUID
