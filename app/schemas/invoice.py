from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class InvoiceResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    subscription_id: UUID
    amount: int
    currency: str
    status: str
    nomba_charge_ref: Optional[str] = None
    due_date: datetime
    paid_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
