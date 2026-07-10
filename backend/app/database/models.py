import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SQLEnum, JSON, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, Dict, Any

from app.database.core import Base
from app.schemas.document import DocumentCategory, ChunkType, DocumentStatus
# pyrefly: ignore [missing-import]
from app.schemas.chat import MessageRole

def get_utc_now():
    return datetime.now(timezone.utc)

# ==========================================
# KNOWLEDGE BASE DOMAIN
# ==========================================

class Document(Base):
    __tablename__ = "documents"

    # We use UUIDs (UUID4) across the board. Sequential integers are easily guessable (security risk)
    # and clash in distributed multi-tenant environments.
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    category: Mapped[DocumentCategory] = mapped_column(SQLEnum(DocumentCategory), default=DocumentCategory.STANDARD)
    status: Mapped[DocumentStatus] = mapped_column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING)
    
    upload_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    total_chunks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationship: A Document has many Chunks
    # cascade="all, delete-orphan" means if we delete a Document, its Chunks die with it.
    chunks: Mapped[List["Chunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    
    chunk_type: Mapped[ChunkType] = mapped_column(SQLEnum(ChunkType), nullable=False)
    # Text holds the actual content. We use Text instead of String because chunks can be large.
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # The JSON column allows us to store our complex, dynamic metadata (bounding boxes, code AST info) safely.
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # The crucial link to FAISS/HNSW. We don't store the massive float array here, just the reference ID.
    vector_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    document: Mapped["Document"] = relationship(back_populates="chunks")


# ==========================================
# CONVERSATION DOMAIN
# ==========================================

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    messages: Mapped[List["Message"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    
    role: Mapped[MessageRole] = mapped_column(SQLEnum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    
    # For citations, rather than making a complex Many-to-Many table mapping Messages to Chunks,
    # we store a snapshot of the cited chunk IDs and brief context as JSON. 
    # This prevents heavy JOINs every time we load chat history.
    citations_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")