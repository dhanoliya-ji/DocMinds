import uuid
import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User

class AuditLog(Base):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g., "user.login", "document.upload"
    
    # Store dynamic action context
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)  # IPv4/IPv6 support
    
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # Nullable for system-level runs
    
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="audit_logs")
    user: Mapped["User"] = relationship("User", back_populates="audit_logs")
