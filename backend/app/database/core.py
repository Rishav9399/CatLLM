from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from app.core.config import settings

# In a true production environment, this will be a PostgreSQL database:
# DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/rag_db"
# For our initial scaffolding and immediate testing, we use async SQLite.
DATABASE_URL = "sqlite+aiosqlite:///./rag_production.db"

# 1. The Async Engine: Manages the connection pool to the database
# echo=False prevents spamming the console with SQL queries in production
engine = create_async_engine(
    DATABASE_URL, 
    echo=False, 
    future=True,
    # SQLite specific args, remove these if switching to PostgreSQL
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# 2. The Session Factory: Manufactures database sessions for our API endpoints
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autoflush=False
)

# 3. The Declarative Base: All our ORM models will inherit from this
class Base(DeclarativeBase):
    pass

# 4. The Dependency: FastAPI will inject this into our routes
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an asynchronous database session.
    Using 'async with' ensures the session cleanly closes and returns to the pool 
    even if an exception occurs during the API request.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()