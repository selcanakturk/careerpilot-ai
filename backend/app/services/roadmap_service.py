from functools import lru_cache
import logging
import random
import time

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.supabase import get_supabase_client
from app.schemas.roadmap import CareerRoadmap, RoadmapGenerateResponse, RoadmapStep


logger = logging.getLogger(__name__)

ROADMAPS_TABLE = "career_roadmaps"
ROADMAP_STEPS_TABLE = "roadmap_steps"
ANALYSES_TABLE = "cv_analyses"
UPLOADS_TABLE = "cv_uploads"
PRIMARY_TEMPORARY_ATTEMPTS = 2
FALLBACK_TEMPORARY_ATTEMPTS = 3
BACKOFF_SECONDS = (1.0, 2.0, 4.0)

SYSTEM_INSTRUCTIONS = """
Act as a senior technical recruiter, career coach, and learning path designer.
Create a realistic, personalized career roadmap based only on the provided CV analysis.
Use the target role, experience level, strengths, weaknesses, skill gaps, CV suggestions, and
overall score to choose the right duration.
The roadmap duration must be at least 4 weeks and at most 24 weeks. Do not use a fixed duration.
Prioritize the highest-impact gaps first, then sequence learning, proof-building, portfolio work,
and interview readiness in a practical order.
Make the plan realistic for the job market and concrete enough for a candidate to follow weekly.
Do not invent career history or skills that are not supported by the analysis.
Ensure estimated_job_readiness_after is higher than estimated_job_readiness_before when reasonable.
Each step priority must be one of: low, medium, high, critical.
Each resources item must include title and url.
Return only valid JSON matching the requested schema.
""".strip()


class TemporaryAIServiceError(RuntimeError):
    """Raised when the AI provider is temporarily unavailable after retries."""


class DailyQuotaExceededError(TemporaryAIServiceError):
    """Raised when the selected AI model has exhausted its daily quota."""


class PermanentAIServiceError(RuntimeError):
    """Raised when the AI provider response or request is not retryable."""


def _extract_response_data(response: object, action: str) -> object | None:
    if response is None:
        return None

    data = getattr(response, "data", None)

    if data is None or data == []:
        return None

    if isinstance(data, list):
        first_item = data[0] if data else None

        if first_item is None:
            return None

        if isinstance(first_item, dict):
            return first_item

        logger.error("Unexpected roadmap %s list item type: %s", action, type(first_item).__name__)
        raise RuntimeError("Unexpected roadmap database response.")

    if isinstance(data, dict):
        return data

    logger.error("Unexpected roadmap %s response type: %s", action, type(data).__name__)
    raise RuntimeError("Unexpected roadmap database response.")


def _extract_rows(response: object, action: str) -> list[dict[str, object]]:
    if response is None:
        return []

    data = getattr(response, "data", None)

    if data is None:
        return []

    if isinstance(data, list):
        if all(isinstance(item, dict) for item in data):
            return data

        logger.error("Unexpected roadmap %s rows item type.", action)
        raise RuntimeError("Unexpected roadmap database response.")

    if isinstance(data, dict):
        return [data]

    logger.error("Unexpected roadmap %s rows response type: %s", action, type(data).__name__)
    raise RuntimeError("Unexpected roadmap database response.")


def _require_row(response: object, action: str, empty_message: str) -> dict[str, object]:
    data = _extract_response_data(response, action)

    if data is None:
        raise RuntimeError(empty_message)

    if not isinstance(data, dict):
        raise RuntimeError("Unexpected roadmap database response.")

    return data


@lru_cache
def get_gemini_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(api_key=settings.gemini_api_key)


def _extract_response_text(response: object) -> str:
    response_text = getattr(response, "text", None)

    if isinstance(response_text, str) and response_text.strip():
        return response_text

    logger.error("Gemini returned an empty or unsupported roadmap response text payload.")
    raise RuntimeError("The AI roadmap response could not be validated.")


def _is_temporary_ai_error(error: Exception) -> bool:
    message = str(error).lower()
    error_name = type(error).__name__.lower()

    temporary_markers = (
        "503",
        "unavailable",
        "high demand",
        "429",
        "resource_exhausted",
        "rate limit",
        "quota",
        "timeout",
        "timed out",
        "connection",
        "network",
    )

    return any(marker in message or marker in error_name for marker in temporary_markers)


def _is_daily_quota_error(error: Exception) -> bool:
    message = str(error).lower()
    quota_markers = (
        "generaterequestsperdayperprojectpermodel-freetier",
        "quota exceeded",
        "current quota",
        "exceeded your current quota",
        "generate_content_free_tier_requests",
    )

    return any(marker in message for marker in quota_markers)


def _sleep_before_retry(attempt_index: int) -> None:
    delay = BACKOFF_SECONDS[min(attempt_index, len(BACKOFF_SECONDS) - 1)]
    jitter = random.uniform(0, 0.2)
    time.sleep(delay + jitter)


def _build_prompt(analysis: dict[str, object]) -> str:
    return "\n\n".join(
        [
            SYSTEM_INSTRUCTIONS,
            f"Target role: {analysis.get('target_role', '')}",
            f"Experience level: {analysis.get('experience_level', '')}",
            f"Overall score: {analysis.get('overall_score', '')}",
            f"Strengths: {analysis.get('strengths', [])}",
            f"Weaknesses: {analysis.get('weaknesses', [])}",
            f"Skill gaps: {analysis.get('skill_gaps', [])}",
            f"CV suggestions: {analysis.get('cv_suggestions', [])}",
            f"Analysis summary: {analysis.get('summary', '')}",
        ]
    )


def build_gemini_roadmap_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "duration_weeks": {
                "type": "integer",
                "minimum": 4,
                "maximum": 24,
            },
            "estimated_job_readiness_before": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
            },
            "estimated_job_readiness_after": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
            },
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "week_number": {
                            "type": "integer",
                            "minimum": 1,
                        },
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "reason": {"type": "string"},
                        "estimated_hours": {
                            "type": "integer",
                            "minimum": 1,
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                        },
                        "resources": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "url": {"type": "string"},
                                },
                                "required": ["title", "url"],
                            },
                        },
                        "mini_project": {"type": "string"},
                    },
                    "required": [
                        "week_number",
                        "title",
                        "description",
                        "reason",
                        "estimated_hours",
                        "priority",
                        "resources",
                        "mini_project",
                    ],
                },
            },
        },
        "required": [
            "summary",
            "duration_weeks",
            "estimated_job_readiness_before",
            "estimated_job_readiness_after",
            "steps",
        ],
    }


def get_analysis_context(analysis_id: str, user_id: str) -> dict[str, object] | None:
    try:
        analysis_response = (
            get_supabase_client()
            .table(ANALYSES_TABLE)
            .select(
                "id,user_id,cv_upload_id,target_role,status,overall_score,summary,"
                "strengths,weaknesses,skill_gaps,cv_suggestions,created_at,updated_at"
            )
            .eq("id", analysis_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to load analysis for roadmap generation.")
        raise RuntimeError("Unable to load analysis.") from exc

    analysis = _extract_response_data(analysis_response, "select analysis")

    if analysis is None:
        return None

    if not isinstance(analysis, dict):
        raise RuntimeError("Unexpected analysis database response.")

    try:
        upload_response = (
            get_supabase_client()
            .table(UPLOADS_TABLE)
            .select("id,experience_level")
            .eq("id", str(analysis["cv_upload_id"]))
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to load upload context for roadmap generation.")
        raise RuntimeError("Unable to load upload context.") from exc

    upload = _extract_response_data(upload_response, "select upload context")

    analysis["experience_level"] = (
        upload.get("experience_level") if isinstance(upload, dict) else "Not specified"
    )

    return analysis


def _generate_with_model(model_name: str, analysis: dict[str, object]) -> CareerRoadmap:
    response = get_gemini_client().models.generate_content(
        model=model_name,
        contents=_build_prompt(analysis),
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=build_gemini_roadmap_schema(),
        ),
    )
    try:
        return CareerRoadmap.model_validate_json(_extract_response_text(response))
    except ValidationError as exc:
        logger.exception("Gemini returned an invalid structured roadmap response.")
        raise PermanentAIServiceError("The AI roadmap response could not be validated.") from exc
    except RuntimeError as exc:
        raise PermanentAIServiceError(str(exc)) from exc


def _generate_with_retry(
    model_name: str,
    analysis: dict[str, object],
    max_attempts: int,
) -> CareerRoadmap:
    for attempt in range(max_attempts):
        try:
            return _generate_with_model(model_name, analysis)
        except PermanentAIServiceError as exc:
            raise RuntimeError(str(exc)) from exc
        except Exception as exc:
            if _is_daily_quota_error(exc):
                raise DailyQuotaExceededError("The AI roadmap model daily quota is exhausted.") from exc

            if not _is_temporary_ai_error(exc):
                logger.exception("Gemini roadmap generation failed.")
                raise RuntimeError("Unable to generate AI roadmap right now.") from exc

            if attempt == max_attempts - 1:
                raise TemporaryAIServiceError(
                    "The AI roadmap service is busy. Please try again shortly."
                ) from exc

            logger.warning(
                "Temporary Gemini roadmap error; retrying request.",
                extra={"attempt": attempt + 1, "max_attempts": max_attempts, "model": model_name},
            )
            _sleep_before_retry(attempt)

    raise TemporaryAIServiceError("The AI roadmap service is busy. Please try again shortly.")


def generate_career_roadmap(analysis: dict[str, object]) -> CareerRoadmap:
    settings = get_settings()

    try:
        return _generate_with_retry(
            model_name=settings.gemini_model,
            analysis=analysis,
            max_attempts=PRIMARY_TEMPORARY_ATTEMPTS,
        )
    except DailyQuotaExceededError as primary_error:
        fallback_model = settings.gemini_fallback_model.strip()

        if not fallback_model or fallback_model == settings.gemini_model:
            logger.warning(
                "Primary Gemini roadmap model quota exhausted; no fallback configured.",
                extra={"primary_model": settings.gemini_model},
            )
            raise primary_error

        logger.warning(
            "Primary Gemini roadmap model quota exhausted; trying fallback.",
            extra={"primary_model": settings.gemini_model, "fallback_model": fallback_model},
        )

        try:
            return _generate_with_retry(
                model_name=fallback_model,
                analysis=analysis,
                max_attempts=FALLBACK_TEMPORARY_ATTEMPTS,
            )
        except TemporaryAIServiceError as fallback_error:
            logger.warning(
                "Fallback Gemini roadmap model unavailable.",
                extra={"fallback_model": fallback_model},
            )
            raise fallback_error from primary_error
    except TemporaryAIServiceError as primary_error:
        fallback_model = settings.gemini_fallback_model.strip()

        if not fallback_model or fallback_model == settings.gemini_model:
            logger.warning("Primary Gemini roadmap model unavailable; no fallback configured.")
            raise primary_error

        logger.warning(
            "Primary Gemini roadmap model unavailable; trying fallback.",
            extra={"primary_model": settings.gemini_model, "fallback_model": fallback_model},
        )

        try:
            return _generate_with_retry(
                model_name=fallback_model,
                analysis=analysis,
                max_attempts=FALLBACK_TEMPORARY_ATTEMPTS,
            )
        except TemporaryAIServiceError as fallback_error:
            logger.warning(
                "Fallback Gemini roadmap model unavailable.",
                extra={"fallback_model": fallback_model},
            )
            raise fallback_error from primary_error


def get_active_roadmap(analysis_id: str, user_id: str) -> RoadmapGenerateResponse | None:
    try:
        roadmap_response = (
            get_supabase_client()
            .table(ROADMAPS_TABLE)
            .select(
                "id,user_id,analysis_id,target_role,duration_weeks,summary,status,"
                "estimated_job_readiness_before,estimated_job_readiness_after,created_at,updated_at"
            )
            .eq("analysis_id", analysis_id)
            .eq("user_id", user_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to load active roadmap.")
        raise RuntimeError("Unable to load roadmap.") from exc

    roadmap = _extract_response_data(roadmap_response, "select active roadmap")

    if roadmap is None:
        return None

    if not isinstance(roadmap, dict):
        raise RuntimeError("Unexpected roadmap database response.")

    return _build_response_from_rows(roadmap, _load_steps(str(roadmap["id"])))


def save_roadmap(
    user_id: str,
    analysis: dict[str, object],
    roadmap: CareerRoadmap,
) -> RoadmapGenerateResponse:
    try:
        roadmap_response = (
            get_supabase_client()
            .table(ROADMAPS_TABLE)
            .insert(
                {
                    "user_id": user_id,
                    "analysis_id": str(analysis["id"]),
                    "target_role": str(analysis["target_role"]),
                    "duration_weeks": roadmap.duration_weeks,
                    "summary": roadmap.summary,
                    "status": "active",
                    "estimated_job_readiness_before": roadmap.estimated_job_readiness_before,
                    "estimated_job_readiness_after": roadmap.estimated_job_readiness_after,
                }
            )
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to save roadmap.")
        raise RuntimeError("Unable to save roadmap.") from exc

    saved_roadmap = _require_row(
        roadmap_response,
        "insert roadmap",
        "Unable to save roadmap.",
    )

    step_payloads = [
        {
            "roadmap_id": str(saved_roadmap["id"]),
            "week_number": step.week_number,
            "title": step.title,
            "description": step.description,
            "reason": step.reason,
            "estimated_hours": step.estimated_hours,
            "priority": step.priority,
            "resources": [resource.model_dump() for resource in step.resources],
            "mini_project": step.mini_project,
        }
        for step in roadmap.steps
    ]

    try:
        steps_response = (
            get_supabase_client()
            .table(ROADMAP_STEPS_TABLE)
            .insert(step_payloads)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to save roadmap steps.")
        raise RuntimeError("Unable to save roadmap steps.") from exc

    saved_steps = _extract_rows(steps_response, "insert roadmap steps")

    if not saved_steps:
        raise RuntimeError("Unable to save roadmap steps.")

    return _build_response_from_rows(saved_roadmap, saved_steps)


def _load_steps(roadmap_id: str) -> list[dict[str, object]]:
    try:
        response = (
            get_supabase_client()
            .table(ROADMAP_STEPS_TABLE)
            .select(
                "week_number,title,description,reason,estimated_hours,priority,resources,mini_project"
            )
            .eq("roadmap_id", roadmap_id)
            .order("week_number", desc=False)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to load roadmap steps.")
        raise RuntimeError("Unable to load roadmap steps.") from exc

    return _extract_rows(response, "select roadmap steps")


def _build_response_from_rows(
    roadmap_row: dict[str, object],
    step_rows: list[dict[str, object]],
) -> RoadmapGenerateResponse:
    steps = [RoadmapStep.model_validate(step) for step in step_rows]
    roadmap = CareerRoadmap(
        summary=str(roadmap_row["summary"]),
        duration_weeks=int(roadmap_row["duration_weeks"]),
        estimated_job_readiness_before=int(roadmap_row["estimated_job_readiness_before"]),
        estimated_job_readiness_after=int(roadmap_row["estimated_job_readiness_after"]),
        steps=steps,
    )

    return RoadmapGenerateResponse(
        id=roadmap_row["id"],
        user_id=roadmap_row["user_id"],
        analysis_id=roadmap_row["analysis_id"],
        target_role=str(roadmap_row["target_role"]),
        status=str(roadmap_row["status"]),
        roadmap=roadmap,
        created_at=roadmap_row.get("created_at"),
        updated_at=roadmap_row.get("updated_at"),
    )
