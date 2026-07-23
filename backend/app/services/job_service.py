from datetime import UTC, datetime
import logging

from app.core.supabase import get_supabase_client
from app.schemas.job import CreateJobPostingRequest, JobMatchAIResult


logger = logging.getLogger(__name__)

JOB_POSTINGS_TABLE = "job_postings"
JOB_MATCHES_TABLE = "job_matches"
ANALYSES_TABLE = "cv_analyses"
ROADMAPS_TABLE = "career_roadmaps"
UPLOADS_TABLE = "cv_uploads"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


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

        logger.error("Unexpected %s list item type: %s", action, type(first_item).__name__)
        raise RuntimeError("Unexpected job database response.")

    if isinstance(data, dict):
        return data

    logger.error("Unexpected %s response type: %s", action, type(data).__name__)
    raise RuntimeError("Unexpected job database response.")


def _extract_rows(response: object, action: str) -> list[dict[str, object]]:
    if response is None:
        return []

    data = getattr(response, "data", None)

    if data is None:
        return []

    if isinstance(data, list):
        if all(isinstance(item, dict) for item in data):
            return data

        logger.error("Unexpected %s rows item type.", action)
        raise RuntimeError("Unexpected job database response.")

    if isinstance(data, dict):
        return [data]

    logger.error("Unexpected %s rows response type: %s", action, type(data).__name__)
    raise RuntimeError("Unexpected job database response.")


def _require_row(response: object, action: str, empty_message: str) -> dict[str, object]:
    data = _extract_response_data(response, action)

    if data is None:
        raise RuntimeError(empty_message)

    if not isinstance(data, dict):
        raise RuntimeError("Unexpected job database response.")

    return data


def create_job_posting(user_id: str, payload: CreateJobPostingRequest) -> dict[str, object]:
    try:
        response = (
            get_supabase_client()
            .table(JOB_POSTINGS_TABLE)
            .insert(
                {
                    "user_id": user_id,
                    "title": payload.title,
                    "company_name": payload.company_name,
                    "location": payload.location,
                    "employment_type": payload.employment_type,
                    "work_mode": payload.work_mode,
                    "source_url": payload.source_url,
                    "description": payload.description,
                    "status": "saved",
                }
            )
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to create job posting.")
        raise RuntimeError("Unable to create job posting.") from exc

    return _require_row(response, "insert job posting", "Unable to create job posting.")


def get_job_posting(job_posting_id: str, user_id: str) -> dict[str, object] | None:
    try:
        response = (
            get_supabase_client()
            .table(JOB_POSTINGS_TABLE)
            .select(
                "id,user_id,title,company_name,location,employment_type,work_mode,"
                "source_url,description,status,created_at,updated_at"
            )
            .eq("id", job_posting_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to load job posting.")
        raise RuntimeError("Unable to load job posting.") from exc

    data = _extract_response_data(response, "select job posting")
    return data if isinstance(data, dict) else None


def list_job_postings(user_id: str) -> list[dict[str, object]]:
    try:
        response = (
            get_supabase_client()
            .table(JOB_POSTINGS_TABLE)
            .select(
                "id,user_id,title,company_name,location,employment_type,work_mode,"
                "source_url,description,status,created_at,updated_at"
            )
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to list job postings.")
        raise RuntimeError("Unable to list job postings.") from exc

    return _extract_rows(response, "select job postings")


def delete_job_posting(job_posting_id: str, user_id: str) -> bool:
    existing_job = get_job_posting(job_posting_id=job_posting_id, user_id=user_id)

    if existing_job is None:
        return False

    try:
        (
            get_supabase_client()
            .table(JOB_POSTINGS_TABLE)
            .delete()
            .eq("id", job_posting_id)
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to delete job posting.")
        raise RuntimeError("Unable to delete job posting.") from exc

    return True


def get_completed_analysis(analysis_id: str, user_id: str) -> dict[str, object] | None:
    try:
        response = (
            get_supabase_client()
            .table(ANALYSES_TABLE)
            .select(
                "id,user_id,cv_upload_id,target_role,status,overall_score,summary,"
                "strengths,weaknesses,skill_gaps,cv_suggestions,created_at,updated_at"
            )
            .eq("id", analysis_id)
            .eq("user_id", user_id)
            .eq("status", "completed")
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to load completed analysis for job matching.")
        raise RuntimeError("Unable to load analysis.") from exc

    data = _extract_response_data(response, "select completed analysis")
    return data if isinstance(data, dict) else None


def get_latest_completed_analysis(user_id: str) -> dict[str, object] | None:
    try:
        response = (
            get_supabase_client()
            .table(ANALYSES_TABLE)
            .select("id,target_role,created_at")
            .eq("user_id", user_id)
            .eq("status", "completed")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to load latest completed analysis.")
        raise RuntimeError("Unable to load analysis.") from exc

    data = _extract_response_data(response, "select latest completed analysis")
    return data if isinstance(data, dict) else None


def get_active_roadmap_target_role(user_id: str) -> str | None:
    try:
        response = (
            get_supabase_client()
            .table(ROADMAPS_TABLE)
            .select("target_role")
            .eq("user_id", user_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to load active roadmap target role.")
        raise RuntimeError("Unable to load roadmap context.") from exc

    data = _extract_response_data(response, "select active roadmap target role")

    if not isinstance(data, dict):
        return None

    target_role = data.get("target_role")
    return target_role if isinstance(target_role, str) and target_role.strip() else None


def get_latest_analysis_target_role(user_id: str) -> str | None:
    analysis = get_latest_completed_analysis(user_id)

    if not analysis:
        return None

    target_role = analysis.get("target_role")
    return target_role if isinstance(target_role, str) and target_role.strip() else None


def list_completed_analysis_options(user_id: str) -> list[dict[str, object]]:
    try:
        analyses_response = (
            get_supabase_client()
            .table(ANALYSES_TABLE)
            .select("id,cv_upload_id,target_role,overall_score,created_at")
            .eq("user_id", user_id)
            .eq("status", "completed")
            .order("created_at", desc=True)
            .execute()
        )
        uploads_response = (
            get_supabase_client()
            .table(UPLOADS_TABLE)
            .select("id,file_name,created_at")
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to list completed analysis options.")
        raise RuntimeError("Unable to load completed CV analyses.") from exc

    analyses = _extract_rows(analyses_response, "select completed analysis options")
    uploads = _extract_rows(uploads_response, "select cv uploads for analysis options")
    uploads_by_id = {str(upload.get("id")): upload for upload in uploads}
    options: list[dict[str, object]] = []

    for analysis in analyses:
        analysis_id = analysis.get("id")
        upload_id = analysis.get("cv_upload_id")
        target_role = analysis.get("target_role")
        overall_score = analysis.get("overall_score")
        analyzed_at = analysis.get("created_at")

        if not all(
            [
                isinstance(analysis_id, str),
                isinstance(upload_id, str),
                isinstance(target_role, str),
                isinstance(overall_score, int),
                isinstance(analyzed_at, str),
            ]
        ):
            continue

        upload = uploads_by_id.get(upload_id)
        filename = upload.get("file_name") if isinstance(upload, dict) else None

        options.append(
            {
                "upload_id": upload_id,
                "analysis_id": analysis_id,
                "filename": filename if isinstance(filename, str) and filename.strip() else "Uploaded CV",
                "analyzed_at": analyzed_at,
                "target_role": target_role,
                "overall_score": overall_score,
            }
        )

    return options


def get_existing_job_match(
    job_posting_id: str,
    analysis_id: str,
    user_id: str,
) -> dict[str, object] | None:
    try:
        response = (
            get_supabase_client()
            .table(JOB_MATCHES_TABLE)
            .select(
                "id,user_id,job_posting_id,analysis_id,match_score,summary,matched_skills,"
                "missing_skills,strengths,risks,recommendations,application_readiness,created_at,updated_at"
            )
            .eq("job_posting_id", job_posting_id)
            .eq("analysis_id", analysis_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to load existing job match.")
        raise RuntimeError("Unable to load job match.") from exc

    data = _extract_response_data(response, "select existing job match")
    return data if isinstance(data, dict) else None


def save_job_match(
    user_id: str,
    job_posting_id: str,
    analysis_id: str,
    result: JobMatchAIResult,
) -> dict[str, object]:
    try:
        response = (
            get_supabase_client()
            .table(JOB_MATCHES_TABLE)
            .insert(
                {
                    "user_id": user_id,
                    "job_posting_id": job_posting_id,
                    "analysis_id": analysis_id,
                    "match_score": result.match_score,
                    "summary": result.summary,
                    "matched_skills": result.matched_skills,
                    "missing_skills": result.missing_skills,
                    "strengths": result.strengths,
                    "risks": result.risks,
                    "recommendations": result.recommendations,
                    "application_readiness": result.application_readiness,
                }
            )
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to save job match.")
        raise RuntimeError("Unable to save job match.") from exc

    return _require_row(response, "insert job match", "Unable to save job match.")


def mark_job_posting_analyzed(job_posting_id: str, user_id: str) -> None:
    try:
        response = (
            get_supabase_client()
            .table(JOB_POSTINGS_TABLE)
            .update({"status": "analyzed", "updated_at": _now_iso()})
            .eq("id", job_posting_id)
            .eq("user_id", user_id)
            .execute()
        )

        if response is not None:
            _extract_response_data(response, "update job posting analyzed")
    except Exception:
        logger.exception("Unable to mark job posting as analyzed.")
