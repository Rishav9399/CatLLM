from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.database.core import engine, Base
from app.api.routers import documents, chat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- THE LIFESPAN MANAGER ---
# This runs eactly once when the server starts, before accespting any traffic
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Initializing Database Architecture...")
    # Instructs SQLAlchemy to physically build the tables based on our models.py
    async with engine.begin() as conn:
        # Note: In a real production DB like PostgreSQL, you would use ALembic migraations instead of create_all()
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database Architecture Locked.")
    yield
    # Code here runs when the server is shutting down
    logger.info("Swarm entering sleep mode.")

app = FastAPI(
    title="LLM Production Grade",
    description="Creating an LLM implemeting RAG and everything inside it.",
    lifespan=lifespan
)

# --- THE SECURITY BRIDGE (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# --- ROUTER REGISTRATION ---
app.include_router(documents.router)
app.include_router(chat.router)

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "OK",
        "message": "System Healthy."
    }
