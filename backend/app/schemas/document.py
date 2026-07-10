from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime
import uuid

# ==========================================
# 1. ENUMS: The Core Classifiers
# ==========================================

class DocumentCategory(str, Enum):
    STANDARD = "standard" # Manuals, books, general PDFs
    LEGAL = "legal"       # Contracts, NDAs (requires clause-boundary chunking)
    CODE = "code"         # Repositories (requires AST parsing, whitespace preservation)
    FINANCIAL = "finance" # Earnings reports (heavy table prioritization)

class ChunkType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    CODE = "code"

class DocumentStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"       # Layout engine is separating tables/images
    EMBEDDING = "embedding"   # Sending to GLM/FAISS
    COMPLETED = "completed"
    FAILED = "failed"

# ==========================================
# 2. METADATA CONTRACTS (The "Smart" part)
# ==========================================
# We define these so our ingestion pipeline knows exactly 
# what data must be attached to specific chunk types.

class TableMetadata(BaseModel):
    format: str = Field(default="markdown", description="e.g., markdown, html")
    columns: List[str] = Field(default_factory=list, description="Extracted column headers")
    parent_section: Optional[str] = None # What header was above this table?

class ImageMetadata(BaseModel):
    storage_path: str = Field(..., description="S3 or local path to the cropped image")
    alt_text: Optional[str] = Field(None, description="VLM-generated description")
    bounding_box: Optional[List[float]] = Field(None, description="[x0, y0, x1, y1] for UI highlighting")

class CodeMetadata(BaseModel):
    language: str = Field(..., example="python")
    file_path: str = Field(..., example="app/services/ingestion.py")
    scope: Optional[str] = Field(None, description="Function or class name (e.g., 'def parse_pdf')")

class LegalMetadata(BaseModel):
    clause_id: Optional[str] = Field(None, example="Section 4.1.a")
    is_definition: bool = Field(default=False)

# ==========================================
# 3. CHUNK SCHEMAS
# ==========================================

class ChunkBase(BaseModel):
    chunk_type: ChunkType
    # The content is standard text, gorgeous markdown for tables, or VLM summaries for images
    content: str 
    
    # CRITICAL: Absolute ordering. You cannot reconstruct a legal doc or code 
    # if you lose the exact sequence of the chunks.
    chunk_index: int = Field(..., description="Sequential order in the original document")
    page_number: Optional[int] = None
    
    # We keep this as a Dict for SQLAlchemy JSONB compatibility, 
    # but in our ingestion service, we will validate it against the Metadata Contracts above.
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChunkCreate(ChunkBase):
    document_id: uuid.UUID

class ChunkResponse(ChunkBase):
    id: uuid.UUID
    document_id: uuid.UUID
    vector_id: Optional[str] = None # ID mapping to FAISS/HNSW

# ==========================================
# 4. DOCUMENT SCHEMAS
# ==========================================

class DocumentBase(BaseModel):
    filename: str
    file_type: str = Field(..., example="application/pdf")
    file_size_bytes: int
    category: DocumentCategory = Field(default=DocumentCategory.STANDARD)

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: uuid.UUID
    status: DocumentStatus
    upload_timestamp: datetime
    chunks_processed: int = 0
    total_chunks: Optional[int] = None

    class Config:
        from_attributes = True