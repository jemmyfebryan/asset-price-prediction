from fastapi import APIRouter

router = APIRouter(prefix="/main-backend", tags=["Main Backend"])


@router.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}
