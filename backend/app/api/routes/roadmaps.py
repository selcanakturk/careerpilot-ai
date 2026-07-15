import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import CurrentUser, get_current_user
from app.schemas.roadmap import RoadmapGenerateResponse
from app.services import roadmap_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/roadmaps", tags=["Roadmaps"])


@router.post("/generate/{analysis_id}", response_model=RoadmapGenerateResponse)
def generate_roadmap(
    analysis_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
) -> RoadmapGenerateResponse:
    try:
        analysis = roadmap_service.get_analysis_context(
            analysis_id=str(analysis_id),
            user_id=current_user.id,
        )
    except Exception:
        logger.exception("Unable to load analysis before roadmap generation.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load analysis.",
        )

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found.",
        )

    try:
        existing_roadmap = roadmap_service.get_active_roadmap(
            analysis_id=str(analysis_id),
            user_id=current_user.id,
        )
    except Exception:
        logger.exception("Unable to check existing roadmap.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load roadmap.",
        )

    if existing_roadmap is not None:
        return existing_roadmap

    try:
        generated_roadmap = roadmap_service.generate_career_roadmap(analysis)
    except roadmap_service.TemporaryAIServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI roadmap service is busy. Please try again shortly.",
        ) from exc
    except Exception:
        logger.exception("Unable to generate roadmap.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate roadmap.",
        )

    try:
        return roadmap_service.save_roadmap(
            user_id=current_user.id,
            analysis=analysis,
            roadmap=generated_roadmap,
        )
    except Exception:
        logger.exception("Unable to save roadmap.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate roadmap.",
        )
