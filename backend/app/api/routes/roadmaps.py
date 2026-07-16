import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import CurrentUser, get_current_user
from app.schemas.roadmap import (
    RoadmapGenerateResponse,
    RoadmapStepProgressResponse,
    RoadmapTaskProgressResponse,
    UpdateRoadmapTaskRequest,
    UpdateRoadmapStepRequest,
)
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


@router.patch(
    "/{roadmap_id}/steps/{step_id}",
    response_model=RoadmapStepProgressResponse,
)
def update_roadmap_step_status(
    roadmap_id: UUID,
    step_id: UUID,
    payload: UpdateRoadmapStepRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> RoadmapStepProgressResponse:
    try:
        roadmap = roadmap_service.get_owned_roadmap(
            roadmap_id=str(roadmap_id),
            user_id=current_user.id,
        )
    except Exception:
        logger.exception("Unable to verify roadmap ownership before step update.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update roadmap step.",
        )

    if roadmap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found.",
        )

    try:
        updated_step = roadmap_service.update_step_status(
            roadmap_id=str(roadmap_id),
            step_id=str(step_id),
            status=payload.status,
        )
    except Exception:
        logger.exception("Unable to update roadmap step status.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update roadmap step.",
        )

    if updated_step is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap step not found.",
        )

    return RoadmapStepProgressResponse.model_validate(updated_step)


@router.patch(
    "/{roadmap_id}/tasks/{task_id}",
    response_model=RoadmapTaskProgressResponse,
)
def update_roadmap_task_status(
    roadmap_id: UUID,
    task_id: UUID,
    payload: UpdateRoadmapTaskRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> RoadmapTaskProgressResponse:
    try:
        roadmap = roadmap_service.get_owned_roadmap(
            roadmap_id=str(roadmap_id),
            user_id=current_user.id,
        )
    except Exception:
        logger.exception("Unable to verify roadmap ownership before task update.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update roadmap task.",
        )

    if roadmap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found.",
        )

    try:
        updated_task = roadmap_service.update_task_status(
            roadmap_id=str(roadmap_id),
            task_id=str(task_id),
            status=payload.status,
        )
    except Exception:
        logger.exception("Unable to update roadmap task status.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update roadmap task.",
        )

    if updated_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap task not found.",
        )

    return RoadmapTaskProgressResponse.model_validate(updated_task)
