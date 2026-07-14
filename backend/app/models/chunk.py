import uuid
import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import DateTime, String, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.document import Document

class Chunk(Base):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=True)
    
    # Store chunk-specific metadata (e.g. headers, layout position)
    meta_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    embeddings: Mapped[List["ChunkEmbedding"]] = relationship("ChunkEmbedding", back_populates="chunk", cascade="all, delete-orphan")


class ChunkEmbedding(Base):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    chunk_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False)
    
    # pgvector column with dynamic dimension support
    embedding: Mapped[List[float]] = mapped_column(Vector, nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    chunk: Mapped["Chunk"] = relationship("Chunk", back_populates="embeddings")
