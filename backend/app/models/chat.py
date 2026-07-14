import uuid
import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import DateTime, String, ForeignKey, Integer, Text, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import Project

class ChatSession(Base):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), default="New Chat", nullable=False)
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="chat_sessions")
    project: Mapped["Project"] = relationship("Project", back_populates="chat_sessions")
    messages: Mapped[List["ChatMessage"]] = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Analytics & Citations
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=True)
    latency: Mapped[float] = mapped_column(Float, nullable=True)
    citations: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # List of dicts representing sources
    
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
    feedbacks: Mapped[List["Feedback"]] = relationship("Feedback", back_populates="message", cascade="all, delete-orphan")


class Feedback(Base):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False)
    
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 (Upvote) | -1 (Downvote)
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    message: Mapped["ChatMessage"] = relationship("ChatMessage", back_populates="feedbacks")
