from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness check: is the API process up? (No database involved.)"""
    return {"status": "ok"}
