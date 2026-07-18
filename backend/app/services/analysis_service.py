from datetime import UTC, datetime
import logging

from app.core.supabase import get_supabase_client
from app.schemas.analysis import CVAnalysisResult, CVAnalysisResponse


logger = logging.getLogger(__name__)

ANALYSES_TABLE = "cv_analyses"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _safe_database_error(action: str, error: object | None = None) -> RuntimeError:
    if error is not None:
        logger.error("Supabase cv_analyses %s failed: %s", action, error)
    return RuntimeError("Unable to update analysis record.")


def _validate_response(data: object) -> CVAnalysisResponse:
    try:
        return CVAnalysisResponse.model_validate(data)
    except Exception as exc:
        logger.exception("Invalid cv_analyses response shape.")
        raise RuntimeError("Unable to validate analysis record.") from exc


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

        logger.error("Unexpected cv_analyses %s list item type: %s", action, type(first_item).__name__)
        raise RuntimeError("Unexpected analysis database response.")

    if isinstance(data, dict):
        return data

    logger.error("Unexpected cv_analyses %s response type: %s", action, type(data).__name__)
    raise RuntimeError("Unexpected analysis database response.")


def _extract_single_row(response: object, operation_name: str, empty_message: str) -> dict[str, object]:
    data = _extract_response_data(response, operation_name)

    if data is None:
        logger.error("Empty cv_analyses response while running %s.", operation_name)
        raise RuntimeError(empty_message)

    if isinstance(data, dict):
        return data

    logger.error("Unexpected normalized cv_analyses response for %s: %s", operation_name, type(data).__name__)
    raise RuntimeError(f"Unexpected response while running {operation_name}.")


def get_completed_analysis(user_id: str, cv_upload_id: str) -> CVAnalysisResponse | None:
    try:
        response = (
            get_supabase_client()
            .table(ANALYSES_TABLE)
            .select(
                "id,user_id,cv_upload_id,target_role,status,overall_score,summary,"
                "strengths,weaknesses,skill_gaps,cv_suggestions,created_at,updated_at"
            )
            .eq("user_id", user_id)
            .eq("cv_upload_id", cv_upload_id)
            .eq("status", "completed")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to check existing completed analysis.")
        raise RuntimeError("Unable to load analysis record.") from exc

    data = _extract_response_data(response, "select completed")

    if data is None:
        return None

    return _validate_response(data)


def create_processing_analysis(
    user_id: str,
    cv_upload_id: str,
    target_role: str,
) -> dict[str, object]:
    try:
        payload = {
            "user_id": user_id,
            "cv_upload_id": cv_upload_id,
            "target_role": target_role,
            "status": "processing",
        }
        response = (
            get_supabase_client()
            .table(ANALYSES_TABLE)
            .insert(payload)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to create processing analysis.")
        raise RuntimeError("Unable to create analysis record.") from exc

    return _extract_single_row(
        response,
        "create analysis record",
        "Unable to create analysis record.",
    )


def complete_analysis(analysis_id: str, result: CVAnalysisResult) -> CVAnalysisResponse:
    try:
        response = (
            get_supabase_client()
            .table(ANALYSES_TABLE)
            .update(
                {
                    "status": "completed",
                    "overall_score": result.overall_score,
                    "summary": result.summary,
                    "strengths": result.strengths,
                    "weaknesses": result.weaknesses,
                    "skill_gaps": result.skill_gaps,
                    "cv_suggestions": result.cv_suggestions,
                    "updated_at": _now_iso(),
                }
            )
            .eq("id", analysis_id)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to complete analysis.")
        raise RuntimeError("Unable to complete analysis record.") from exc

    data = _extract_single_row(
        response,
        "complete analysis record",
        "Unable to complete analysis record.",
    )

    enriched_data = {
        **data,
        "primary_role": result.primary_role,
        "alternative_roles": result.alternative_roles,
        "top_skills": result.top_skills,
        "preferred_job_types": result.preferred_job_types,
        "preferred_locations": result.preferred_locations,
        "remote_preference": result.remote_preference,
    }

    return _validate_response(enriched_data)


def fail_analysis(analysis_id: str, safe_error_message: str) -> None:
    try:
        response = (
            get_supabase_client()
            .table(ANALYSES_TABLE)
            .update(
                {
                    "status": "failed",
                    "error_message": safe_error_message,
                    "updated_at": _now_iso(),
                }
            )
            .eq("id", analysis_id)
            .execute()
        )
        if response is not None:
            _extract_response_data(response, "update failed")
    except Exception:
        logger.exception("Unable to mark analysis as failed.")


def delete_analysis(analysis_id: str, user_id: str) -> dict[str, object] | None:
    try:
        existing_response = (
            get_supabase_client()
            .table(ANALYSES_TABLE)
            .select("id,cv_upload_id")
            .eq("id", analysis_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to load analysis before deletion.")
        raise RuntimeError("Unable to load analysis record.") from exc

    existing = _extract_response_data(existing_response, "select before delete")

    if existing is None:
        return None

    if not isinstance(existing, dict):
        logger.error("Unexpected normalized cv_analyses delete lookup response.")
        raise RuntimeError("Unexpected analysis database response.")

    try:
        delete_response = (
            get_supabase_client()
            .table(ANALYSES_TABLE)
            .delete()
            .eq("id", analysis_id)
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to delete analysis.")
        raise RuntimeError("Unable to delete analysis record.") from exc

    deleted = _extract_response_data(delete_response, "delete analysis record")

    if deleted is None:
        deleted = existing

    if not isinstance(deleted, dict):
        logger.error("Unexpected normalized cv_analyses delete response.")
        raise RuntimeError("Unexpected analysis database response.")

    return {
        "id": deleted.get("id", existing.get("id")),
        "cv_upload_id": deleted.get("cv_upload_id", existing.get("cv_upload_id")),
    }


def delete_analyses_for_upload(upload_id: str, user_id: str) -> None:
    try:
        response = (
            get_supabase_client()
            .table(ANALYSES_TABLE)
            .delete()
            .eq("cv_upload_id", upload_id)
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to delete analyses for upload.")
        raise RuntimeError("Unable to delete analysis records.") from exc

    if response is not None:
        _extract_response_data(response, "delete analyses for upload")
