import logging

from google.genai import types
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.supabase import get_supabase_client
from app.prompts.cv_optimizer_prompt import SYSTEM_PROMPT, build_cv_optimizer_user_prompt
from app.schemas.cv_optimizer import CVOptimizerResult, JobProvider
from app.services import pdf_service, storage_service
from app.services import career_profile_service
from app.services import job_match_service
from app.services.ai.providers.gemini_provider import (
    DailyQuotaExceededError,
    FALLBACK_TEMPORARY_ATTEMPTS,
    PRIMARY_TEMPORARY_ATTEMPTS,
    TemporaryAIServiceError,
    _extract_response_text,
    _get_model_sequence,
    _is_auth_error,
    _is_daily_quota_error,
    _is_temporary_ai_error,
    _sleep_before_retry,
    get_gemini_client,
)
from app.services.jobs.provider_registry import get_provider_registrations
from app.services.jobs.providers.base import JobDiscoveryConfigurationError, TemporaryJobDiscoveryError


logger = logging.getLogger(__name__)

ANALYSES_TABLE = "cv_analyses"
UPLOADS_TABLE = "cv_uploads"
JOB_POSTINGS_TABLE = "job_postings"
JOB_MATCHES_TABLE = "job_matches"
MAX_CV_TEXT_CHARACTERS = 30000
JOB_LOOKUP_RESULTS_PER_QUERY = 50


class CVOptimizerInputNotFoundError(ValueError):
    """Raised when the analysis, CV upload, or external job cannot be found."""


class CVOptimizerAIError(RuntimeError):
    """Raised when AI optimization cannot be completed safely."""


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

        logger.error("Unexpected CV optimizer %s list item type: %s", action, type(first_item).__name__)
        raise RuntimeError("Unexpected CV optimizer database response.")

    if isinstance(data, dict):
        return data

    logger.error("Unexpected CV optimizer %s response type: %s", action, type(data).__name__)
    raise RuntimeError("Unexpected CV optimizer database response.")


def _get_completed_analysis(analysis_id: str, user_id: str) -> dict[str, object] | None:
    try:
        response = (
            get_supabase_client()
            .table(ANALYSES_TABLE)
            .select("*")
            .eq("id", analysis_id)
            .eq("user_id", user_id)
            .eq("status", "completed")
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to load analysis for CV optimization.")
        raise RuntimeError("Unable to load CV analysis.") from exc

    data = _extract_response_data(response, "select completed analysis")
    return data if isinstance(data, dict) else None


def _get_cv_upload(cv_upload_id: object, user_id: str) -> dict[str, object] | None:
    if not isinstance(cv_upload_id, str) or not cv_upload_id.strip():
        return None

    try:
        response = (
            get_supabase_client()
            .table(UPLOADS_TABLE)
            .select("id,user_id,file_name,file_path,file_type,file_size,target_role,experience_level,created_at")
            .eq("id", cv_upload_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to load CV upload for optimization.")
        raise RuntimeError("Unable to load CV upload.") from exc

    data = _extract_response_data(response, "select CV upload")
    return data if isinstance(data, dict) else None


def _truncate_cv_text(cv_text: str) -> str:
    if len(cv_text) <= MAX_CV_TEXT_CHARACTERS:
        return cv_text

    logger.debug(
        "CV optimizer text exceeded maximum length and was truncated.",
        extra={"original_length": len(cv_text), "truncated_length": MAX_CV_TEXT_CHARACTERS},
    )
    return cv_text[:MAX_CV_TEXT_CHARACTERS]


def _extract_cv_text(upload: dict[str, object]) -> str:
    file_type = upload.get("file_type")
    file_path = upload.get("file_path")

    if not isinstance(file_path, str) or not file_path.strip():
        raise CVOptimizerInputNotFoundError("CV file not found.")

    if not isinstance(file_type, str) or "pdf" not in file_type.lower():
        raise ValueError("Only PDF CV optimization is supported right now.")

    try:
        file_bytes = storage_service.download_cv(file_path)
        return _truncate_cv_text(pdf_service.extract_text_from_pdf(file_bytes).text)
    except FileNotFoundError as exc:
        raise CVOptimizerInputNotFoundError("CV file not found.") from exc
    except ValueError as exc:
        raise ValueError("The CV file could not be read.") from exc
    except Exception as exc:
        logger.exception("Unable to read CV text for optimization.")
        raise RuntimeError("Unable to read CV file.") from exc


def _provider_registration(provider: JobProvider):
    registration = next(
        (
            registration
            for registration in get_provider_registrations()
            if registration.name == provider and registration.configured
        ),
        None,
    )

    if registration is None:
        raise CVOptimizerInputNotFoundError("Job posting not found.")

    return registration


def _find_external_job(
    *,
    analysis: dict[str, object],
    user_id: str,
    job_external_id: str,
    provider: JobProvider,
) -> dict[str, object] | None:
    profile = career_profile_service.get_career_profile_for_analysis(user_id, str(analysis["id"]))

    if profile is None:
        return None

    registration = _provider_registration(provider)
    locations = profile.preferred_locations or ["Turkey"]
    location = locations[0] if locations else "Turkey"

    for query in career_profile_service.generate_search_queries(profile):
        try:
            result = registration.provider.search_jobs(
                query=query,
                location=location,
                page=1,
                results_per_page=JOB_LOOKUP_RESULTS_PER_QUERY,
            )
        except (JobDiscoveryConfigurationError, TemporaryJobDiscoveryError):
            logger.warning(
                "Unable to load external job for CV optimization.",
                extra={"provider": provider, "query": query},
            )
            continue
        except Exception:
            logger.exception("Unexpected external job lookup error for CV optimization.")
            continue

        for job in result.jobs:
            if job.external_id != job_external_id:
                continue

            return {
                "external_id": job.external_id,
                "provider": job.source,
                "title": job.title,
                "company_name": job.company_name,
                "location": job.location,
                "employment_type": job.employment_type,
                "work_mode": job.work_mode,
                "description": job.description,
                "source_url": job.source_url,
            }

    return None


def _clamp_score(value: object) -> int | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return max(0, min(100, value))

    if isinstance(value, float):
        return max(0, min(100, round(value)))

    return None


def _get_saved_job_posting_by_source_url(source_url: object, user_id: str) -> dict[str, object] | None:
    if not isinstance(source_url, str) or not source_url.strip():
        return None

    try:
        response = (
            get_supabase_client()
            .table(JOB_POSTINGS_TABLE)
            .select("id,user_id,source_url")
            .eq("source_url", source_url)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to load saved job posting for CV optimization match score.")
        raise RuntimeError("Unable to load saved job match context.") from exc

    data = _extract_response_data(response, "select saved job posting by source URL")
    return data if isinstance(data, dict) else None


def _get_existing_job_match_score(
    *,
    job_posting_id: object,
    analysis_id: str,
    user_id: str,
) -> int | None:
    if not isinstance(job_posting_id, str) or not job_posting_id.strip():
        return None

    try:
        response = (
            get_supabase_client()
            .table(JOB_MATCHES_TABLE)
            .select("match_score")
            .eq("job_posting_id", job_posting_id)
            .eq("analysis_id", analysis_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to load existing job match score for CV optimization.")
        raise RuntimeError("Unable to load existing job match score.") from exc

    data = _extract_response_data(response, "select existing job match score")

    if not isinstance(data, dict):
        return None

    return _clamp_score(data.get("match_score"))


def _calculate_deterministic_match_before(
    *,
    analysis: dict[str, object],
    user_id: str,
    job_posting: dict[str, object],
) -> int:
    profile = career_profile_service.get_career_profile_for_analysis(user_id, str(analysis["id"]))

    if profile is None:
        return 0

    return job_match_service.calculate_job_match(job_posting, profile).match_score


def _resolve_match_before(
    *,
    analysis: dict[str, object],
    user_id: str,
    job_posting: dict[str, object],
) -> int:
    saved_job_posting = _get_saved_job_posting_by_source_url(job_posting.get("source_url"), user_id)

    if saved_job_posting is not None:
        existing_score = _get_existing_job_match_score(
            job_posting_id=saved_job_posting.get("id"),
            analysis_id=str(analysis["id"]),
            user_id=user_id,
        )

        if existing_score is not None:
            return existing_score

    return _calculate_deterministic_match_before(
        analysis=analysis,
        user_id=user_id,
        job_posting=job_posting,
    )


def _apply_backend_match_scores(result: CVOptimizerResult, match_before: int) -> CVOptimizerResult:
    result.match_before = match_before
    result.estimated_match_after = max(match_before, min(100, result.estimated_match_after))
    return result


def build_gemini_cv_optimizer_schema() -> dict[str, object]:
    string_array_schema = {"type": "array", "items": {"type": "string"}}
    flexible_object_array_schema = {
        "type": "array",
        "items": {"type": "object"},
    }

    return {
        "type": "object",
        "properties": {
            "match_before": {"type": "integer", "minimum": 0, "maximum": 100},
            "estimated_match_after": {"type": "integer", "minimum": 0, "maximum": 100},
            "changes": {"type": "array", "items": {"type": "string"}},
            "optimized_cv": {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "summary": {"type": "string"},
                    "experience": flexible_object_array_schema,
                    "projects": flexible_object_array_schema,
                    "skills": string_array_schema,
                    "education": flexible_object_array_schema,
                    "certifications": flexible_object_array_schema,
                    "additional_sections": {"type": "object"},
                },
                "required": [
                    "headline",
                    "summary",
                    "experience",
                    "projects",
                    "skills",
                    "education",
                    "certifications",
                    "additional_sections",
                ],
            },
        },
        "required": [
            "match_before",
            "estimated_match_after",
            "changes",
            "optimized_cv",
        ],
    }


def _build_optimizer_prompt(
    *,
    cv_text: str,
    analysis: dict[str, object],
    job_posting: dict[str, object],
) -> str:
    return "\n\n".join(
        [
            SYSTEM_PROMPT,
            build_cv_optimizer_user_prompt(
                cv_text=cv_text,
                analysis=analysis,
                job_posting=job_posting,
            ),
        ]
    )


def _generate_optimizer_with_model(model_name: str, prompt: str) -> CVOptimizerResult:
    logger.info("Attempting Gemini CV optimizer model.", extra={"model": model_name})

    response = get_gemini_client().models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=build_gemini_cv_optimizer_schema(),
        ),
    )

    try:
        return CVOptimizerResult.model_validate_json(_extract_response_text(response))
    except ValidationError as exc:
        logger.exception("Gemini returned an invalid structured CV optimizer response.")
        raise CVOptimizerAIError("The CV optimization response could not be validated.") from exc
    except RuntimeError as exc:
        logger.exception("Gemini returned an unreadable CV optimizer response.")
        raise CVOptimizerAIError("The CV optimization response could not be validated.") from exc


def _generate_optimizer_with_retry(
    *,
    model_name: str,
    prompt: str,
    max_attempts: int,
) -> CVOptimizerResult:
    for attempt in range(max_attempts):
        try:
            return _generate_optimizer_with_model(model_name=model_name, prompt=prompt)
        except CVOptimizerAIError:
            raise
        except Exception as exc:
            if _is_auth_error(exc):
                logger.exception("Gemini CV optimizer authentication failed.", extra={"model": model_name})
                raise CVOptimizerAIError("Unable to authenticate with the CV optimization service.") from exc

            if _is_daily_quota_error(exc):
                raise DailyQuotaExceededError("The CV optimization model daily quota is exhausted.") from exc

            if not _is_temporary_ai_error(exc):
                logger.exception("Gemini CV optimizer request failed.", extra={"model": model_name})
                raise CVOptimizerAIError("Unable to optimize CV right now.") from exc

            if attempt == max_attempts - 1:
                raise TemporaryAIServiceError("The CV optimization service is temporarily unavailable.") from exc

            logger.warning(
                "Temporary Gemini CV optimizer error; retrying request.",
                extra={"attempt": attempt + 1, "max_attempts": max_attempts, "model": model_name},
            )
            _sleep_before_retry(attempt)

    raise TemporaryAIServiceError("The CV optimization service is temporarily unavailable.")


def _optimize_with_gemini(
    *,
    cv_text: str,
    analysis: dict[str, object],
    job_posting: dict[str, object],
) -> CVOptimizerResult:
    settings = get_settings()
    prompt = _build_optimizer_prompt(cv_text=cv_text, analysis=analysis, job_posting=job_posting)

    for model_index, model_name in enumerate(_get_model_sequence(settings.gemini_model)):
        max_attempts = PRIMARY_TEMPORARY_ATTEMPTS if model_index == 0 else FALLBACK_TEMPORARY_ATTEMPTS

        try:
            return _generate_optimizer_with_retry(
                model_name=model_name,
                prompt=prompt,
                max_attempts=max_attempts,
            )
        except DailyQuotaExceededError:
            logger.warning(
                "Gemini CV optimizer model quota exhausted; trying next model.",
                extra={"model": model_name},
            )
            continue
        except TemporaryAIServiceError:
            logger.warning(
                "Gemini CV optimizer model unavailable; trying next model.",
                extra={"model": model_name},
            )
            continue

    raise CVOptimizerAIError("The CV optimization service is temporarily rate limited or unavailable.")


def optimize_cv_for_job(
    *,
    user_id: str,
    analysis_id: str,
    job_external_id: str,
    provider: JobProvider,
) -> CVOptimizerResult:
    analysis = _get_completed_analysis(analysis_id=analysis_id, user_id=user_id)

    if analysis is None:
        raise CVOptimizerInputNotFoundError("CV analysis not found.")

    upload = _get_cv_upload(analysis.get("cv_upload_id"), user_id=user_id)

    if upload is None:
        raise CVOptimizerInputNotFoundError("CV upload not found.")

    job_posting = _find_external_job(
        analysis=analysis,
        user_id=user_id,
        job_external_id=job_external_id,
        provider=provider,
    )

    if job_posting is None:
        raise CVOptimizerInputNotFoundError("Job posting not found.")

    cv_text = _extract_cv_text(upload)
    match_before = _resolve_match_before(analysis=analysis, user_id=user_id, job_posting=job_posting)
    result = _optimize_with_gemini(cv_text=cv_text, analysis=analysis, job_posting=job_posting)
    return _apply_backend_match_scores(result, match_before)
