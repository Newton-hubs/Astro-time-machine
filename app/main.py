"""
Astro Time Machine - FastAPI Application
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse 
from app.core.exceptions import RateLimitExceededError, LocationResolutionError
from fastapi.staticfiles import StaticFiles


from app.api.v1.endpoints import astronomy, narration, health
# from app.core.config import settings
from app.core.logging import setup_logging
from app.db.redis_client import redis_client

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    await redis_client.connect()
    yield
    await redis_client.disconnect()


app = FastAPI(
    title="Astro Time Machine API",
    description="Travel through time and explore the night sky from any location on Earth.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceededError) 
async def rate_limit_handler(request, exc): 
    return JSONResponse(status_code=429, content={"detail": str(exc)}) 
@app.exception_handler(LocationResolutionError) 
async def location_handler(request, exc): 
    return JSONResponse(status_code=404, content={"detail": str(exc)})


# Routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(astronomy.router, prefix="/api/v1/astronomy", tags=["astronomy"])
app.include_router(narration.router, prefix="/api/v1/narration", tags=["narration"])

app.mount("/", StaticFiles(directory="fe", html=True), name="frontend")