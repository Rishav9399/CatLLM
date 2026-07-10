from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid

# 1. The Roles
class MessageRole(str, Enum):
    USER = "user"
    AI = "ai"
    SYSTEM = "system"
    TOOL = "tool" # ARCHITECTURAL ADDITION: For Autonomous Agent Observations

# 2. Incoming Data Contract
class MessageCreate(BaseModel):
    content: str = Field(..., description="The user's raw input query")
    attachments: Optional[List[str]] = Field(default=None, description="Optional local file paths for images")

# 3. Outgoing Data Contract (For fetching chat history to the UI)
class MessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: MessageRole
    content: str
    timestamp: datetime
    # Returns the chunk IDs used by the LLM so the UI can render citations
    citations_snapshot: Optional[Dict[str, Any]] = None 
    attachments: Optional[List[str]] = None

    class Config:
        from_attributes = True

# 4. Session Contract
class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True

# 5. Sidebar Contracts (Paginated Session List + Session Detail)

class SessionPreview(BaseModel):
    """Lightweight session summary for the sidebar list."""
    id: uuid.UUID
    title: str
    created_at: datetime
    preview: str = ""  # First 80 chars of the first message, empty if no messages yet

    class Config:
        from_attributes = True

class SessionListResponse(BaseModel):
    """Paginated session list — never unbounded."""
    sessions: List[SessionPreview]
    total: int
    limit: int
    offset: int

class SessionDetailResponse(BaseModel):
    """Full session with all messages — for loading history on sidebar click."""
    id: uuid.UUID
    title: str
    created_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True