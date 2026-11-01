"""ShopGuard Co-Pilot Backend — FastAPI Application (Port 8010)."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx

from src.shopguard.config import settings
from src.shopguard.logging_config import logger
from src.shopguard.database.models import init_shopguard_db
from src.shopguard.database.connection import get_shopguard_db
from src.shopguard.api.routes import router as api_router
from src.shopguard.tools.rag_tool import seed_knowledge_base, collection_health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise database, RAG vector store on backend boot."""
    init_shopguard_db()
    # Seed knowledge base if not already seeded
    try:
        seed_res = seed_knowledge_base()
        logger.info("RAG knowledge base initialized: %s", seed_res)
    except Exception as exc:
        logger.warning("RAG initialization notice: %s", exc)

    logger.info("ShopGuard Backend initialized on port %d.", settings.SHOPGUARD_PORT)
    yield


app = FastAPI(
    title="ShopGuard Co-Pilot API",
    description="Deterministic Operations Co-Pilot & Investigation Engine",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["System"])
def health_check():
    """System health check validating all core subsystems without exposing secrets."""
    # 1. Check SQLite
    db_status = "error"
    try:
        with get_shopguard_db() as conn:
            conn.execute("SELECT 1").fetchone()
        db_status = "connected"
    except Exception as exc:
        db_status = f"unhealthy: {exc}"

    # 2. Check Simulator
    sim_status = "unreachable"
    try:
        with httpx.Client(timeout=2.0) as client:
            r = client.get(f"{settings.SIMULATOR_URL}/health")
            if r.status_code == 200:
                sim_status = "reachable"
    except Exception:
        sim_status = "offline"

    # 3. Check ChromaDB
    chroma_info = collection_health()

    # 4. Check Groq Configuration Status (Never leak key)
    groq_configured = bool(
        settings.GROQ_API_KEY
        and settings.GROQ_API_KEY != "gsk_your_groq_api_key_here"
    )

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "shopguard-backend",
        "port": settings.SHOPGUARD_PORT,
        "database": db_status,
        "simulator": sim_status,
        "vector_store": chroma_info,
        "groq_configured": groq_configured,
        "groq_model": settings.GROQ_MODEL,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.shopguard.api.main:app",
        host=settings.SHOPGUARD_HOST,
        port=settings.SHOPGUARD_PORT,
        reload=False,
    )
