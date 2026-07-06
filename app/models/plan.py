import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, BigInteger, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    interval: Mapped[str] = mapped_column(String(50))       # month, year, day
    interval_count: Mapped[int] = mapped_column(Integer, default=1)
    amount: Mapped[int] = mapped_column(BigInteger)          # in kobo
    currency: Mapped[str] = mapped_column(String(10), default="NGN")
    status: Mapped[str] = mapped_column(String(50), default="active")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
