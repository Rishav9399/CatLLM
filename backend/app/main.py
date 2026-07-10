from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from app.database.core import engine, Base
from app.api.routers import documents, chat

# --- ARCHITECTURAL FIX: IMPORT THE MCP SINGLETON ---
from app.services.mcp_manager import global_mcp_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- THE LIFESPAN MANAGER ---
# This runs exactly once when the server starts, before accepting any traffic
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Database Architecture...")
    # Instructs SQLAlchemy to physically build the tables based on our models.py
    async with engine.begin() as conn:
        # Note: In a real production DB like PostgreSQL, you would use Alembic migrations instead of create_all()
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database Architecture Locked.")
    
    # --- ARCHITECTURAL FIX: WARM UP THE NERVOUS SYSTEM ---
    logger.info("Powering up Peripheral Nervous System (MCP)...")
    await global_mcp_manager._init_peripherals()
    
    yield
    
    # Code here runs when the server is shutting down
    logger.info("Swarm entering sleep mode. Severing MCP connections...")
    await global_mcp_manager.shutdown()

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

# --- STATIC FILES FOR MULTIMODAL VISION ---
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "OK",
        "message": "System Healthy."
    }
    