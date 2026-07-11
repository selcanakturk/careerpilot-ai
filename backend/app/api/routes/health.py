from pydantic import BaseModel
from fastapi import APIRouter

from app.core.config import get_settings


router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    settings = get_settings()

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
    )

