"""
Health check endpoint — used by load balancers and k8s probes.
"""
from fastapi import APIRouter

from app.db.redis_client import redis_client
from app.schemas.astronomy import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Service health check")
async def health_check():
    """
    Returns service health status.
    - `redis`: whether Redis is reachable.
    Suitable for use as a Kubernetes liveness/readiness probe.
    """
    redis_ok = await redis_client.health_check()
    return HealthResponse(
        status="healthy" if redis_ok else "degraded",
        redis=redis_ok,
    )
