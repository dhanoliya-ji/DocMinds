import uuid
import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, String, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.organization import Organization

class APIKey(Base):
    __tablename__ = "api_keys"  # Override default pluralization "a_p_i_keys"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Store first few characters for visual reference in dashboards (e.g. sk_live_abcd...)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    # Store SHA256 hashed key, never store the actual key in plain-text
    hashed_key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")
    organization: Mapped["Organization"] = relationship("Organization", back_populates="api_keys")
