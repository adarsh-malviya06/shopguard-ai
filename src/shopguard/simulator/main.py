"""E-Commerce Simulator — FastAPI Application (Port 8002)."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.shopguard.config import settings
from src.shopguard.logging_config import logger
from src.shopguard.database.models import init_simulator_db
from src.shopguard.simulator.engine import _seed_simulator
from src.shopguard.simulator.routes import router as sim_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise and seed the simulator database on startup."""
    init_simulator_db()
    _seed_simulator()
    logger.info("Simulator ready on port %d.", settings.SIMULATOR_PORT)
    yield


app = FastAPI(
    title="ShopGuard E-Commerce Simulator",
    description="Dynamic E-Commerce Order & Operations Simulator",
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

app.include_router(sim_router)


@app.get("/health", tags=["System"])
def health_check():
    """Health status probe for Simulator."""
    return {
        "status": "healthy",
        "service": "ecommerce-simulator",
        "port": settings.SIMULATOR_PORT,
        "database": "connected",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.shopguard.simulator.main:app",
        host=settings.SIMULATOR_HOST,
        port=settings.SIMULATOR_PORT,
        reload=False,
    )
