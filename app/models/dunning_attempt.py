import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class DunningAttempt(Base):
    __tablename__ = "dunning_attempts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(50))   # pending, success, failed
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
