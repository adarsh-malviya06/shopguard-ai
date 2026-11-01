"""Configuration module for ShopGuard AI.

Loads environment variables from .env using python-dotenv and validates
critical settings.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Base directory of the repository
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env if present
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()


class Settings:
    """Application runtime settings with fail-safe defaults."""

    # Base Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    KNOWLEDGE_BASE_DIR: Path = BASE_DIR / "knowledge_base"

    # ShopGuard Backend Service
    SHOPGUARD_HOST: str = os.getenv("SHOPGUARD_HOST", "0.0.0.0")
    SHOPGUARD_PORT: int = int(os.getenv("SHOPGUARD_PORT", "8010"))

    # E-commerce Simulator Service
    SIMULATOR_HOST: str = os.getenv("SIMULATOR_HOST", "0.0.0.0")
    SIMULATOR_PORT: int = int(os.getenv("SIMULATOR_PORT", "8002"))
    SIMULATOR_URL: str = os.getenv("SIMULATOR_URL", f"http://localhost:{SIMULATOR_PORT}")

    # Streamlit UI
    STREAMLIT_PORT: int = int(os.getenv("STREAMLIT_PORT", "8501"))

    # LLM Settings (Groq Free Tier)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    GROQ_TEMPERATURE: float = float(os.getenv("GROQ_TEMPERATURE", "0.1"))
    GROQ_MAX_TOKENS: int = int(os.getenv("GROQ_MAX_TOKENS", "512"))

    # Database & Storage Paths
    SIMULATOR_DB_PATH: Path = BASE_DIR / os.getenv("SIMULATOR_DB_PATH", "data/simulator.db")
    SHOPGUARD_DB_PATH: Path = BASE_DIR / os.getenv("SHOPGUARD_DB_PATH", "data/shopguard.db")
    CHROMA_PERSIST_DIR: Path = BASE_DIR / os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
    AUDIT_LOG_PATH: Path = BASE_DIR / os.getenv("AUDIT_LOG_PATH", "logs/audit.jsonl")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # Rate Limiting & Caching
    RATE_LIMIT_GLOBAL_PER_MIN: int = int(os.getenv("RATE_LIMIT_GLOBAL_PER_MIN", "60"))
    RATE_LIMIT_PER_SESSION_PER_MIN: int = int(os.getenv("RATE_LIMIT_PER_SESSION_PER_MIN", "20"))
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    CACHE_MAX_ENTRIES: int = int(os.getenv("CACHE_MAX_ENTRIES", "100"))

    def ensure_directories(self) -> None:
        """Ensure runtime directories exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
        self.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        self.SIMULATOR_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.SHOPGUARD_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
