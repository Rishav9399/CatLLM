from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import uuid
import logging

from app.database.core import get_db
from app.database.models import ChatSession, Message
from app.schemas.chat import (
    MessageCreate, MessageRole,
    SessionPreview, SessionListResponse, SessionDetailResponse, MessageResponse
)
from app.services.chat_orchestrator import AgenticOrchestrator
from app.services.vector_engine import EnterpriseVectorEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["Chat & AI Operations"])

# Singleton engine: Models remain in VRAM across requests
vector_engine_instance = EnterpriseVectorEngine()


# ---------------------------------------------------------------------------
# POST /sessions — Create a new chat session
# ---------------------------------------------------------------------------
@router.post("/sessions", response_model=dict)
async def create_chat_session(db: AsyncSession = Depends(get_db)):
    new_session = ChatSession(title="New Session")
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return {"session_id": str(new_session.id)}


# ---------------------------------------------------------------------------
# DELETE /sessions/{session_id} — Delete a chat session
# ---------------------------------------------------------------------------
@router.delete("/sessions/{session_id}", status_code=204)
async def delete_chat_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Purges a session and all its associated messages.
    Leverages SQLAlchemy cascade rules defined in models.py.
    """
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    await db.delete(session)
    await db.commit()
    return None


# ---------------------------------------------------------------------------
# GET /sessions — Paginated session list for the sidebar
# ---------------------------------------------------------------------------
@router.get("/sessions", response_model=SessionListResponse)
async def list_chat_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Paginated session list for the sidebar. Never unbounded."""
    count_result = await db.execute(select(func.count()).select_from(ChatSession))
    total = count_result.scalar_one()

    sessions_result = await db.execute(
        select(ChatSession)
        .order_by(ChatSession.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    sessions = sessions_result.scalars().all()

    previews = []
    for session in sessions:
        first_msg_result = await db.execute(
            select(Message)
            .where(Message.session_id == session.id)
            .order_by(Message.timestamp.asc())
            .limit(1)
        )
        first_msg = first_msg_result.scalar_one_or_none()
        content = first_msg.content if first_msg else ""
        preview_text = (content[:80] + "…") if len(content) > 80 else content

        previews.append(SessionPreview(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            preview=preview_text,
        ))

    return SessionListResponse(sessions=previews, total=total, limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# GET /sessions/{session_id} — Full session with message history
# ---------------------------------------------------------------------------
@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_chat_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Full session with all messages. Called on sidebar session click."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_id)
        .options(selectinload(ChatSession.messages))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    sorted_messages = sorted(session.messages, key=lambda m: m.timestamp)

    return SessionDetailResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        messages=[
            MessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
                citations_snapshot=msg.citations_snapshot,
                attachments=msg.attachments,
            )
            for msg in sorted_messages
        ],
    )


# ---------------------------------------------------------------------------
# POST /sessions/{session_id}/message — Send a message, get SSE stream back
# ---------------------------------------------------------------------------
@router.post("/sessions/{session_id}/message")
async def send_message(
    session_id: uuid.UUID,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    user_message = Message(
        session_id=session_id, 
        role=MessageRole.USER, 
        content=payload.content,
        attachments=payload.attachments
    )
    db.add(user_message)
    await db.commit()

    orchestrator = AgenticOrchestrator(db_session=db, vector_engine=vector_engine_instance)

    return StreamingResponse(
        orchestrator.stream_agentic_response(session_id, payload.content, payload.attachments),
        media_type="text/event-stream"
    )