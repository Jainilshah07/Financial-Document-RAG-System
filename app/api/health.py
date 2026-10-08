from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness check. Database checks are added once the DB layer exists."""
    return {"status": "ok"}
