import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    subscription_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("subscriptions.id"))
    amount: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(10), default="NGN")
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, paid, failed
    nomba_charge_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    due_date: Mapped[datetime] = mapped_column(DateTime)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
