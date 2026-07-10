from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    The Master Configuration Vault.
    Validates environment variables on startup. If a required field is mising, the FastAPI will crash immediately (Fail-Fast Principle).
    """
    PROJECT_NAME: str = "Enterprise RAG Swarm"

    # Database Settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./rag_production.db"

    # --- LLM API KEYS ---
    # Groq is our primary router and logic engine, so it is scritctly REQUIRED
    # If this is not in the .env file, the server willl not start
    GROQ_API_KEY: str

    # These are Optional. The Swarm will gracefully degrade if these are missing,
    # but we define then here so Pydantic knows to look for them in the .env file
    GEMINI_API_KEY: Optional[str] = None
    GLM_API_KEY: Optional[str] = None

    # Tells Pydantic to read from a local .env file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Instantiate the singleton. We import this object accross our app
settings = Settings()
