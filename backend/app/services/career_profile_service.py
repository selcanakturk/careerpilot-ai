import logging
import re

from pydantic import BaseModel, Field

from app.core.supabase import get_supabase_client
from app.schemas.analysis import normalize_top_skills


logger = logging.getLogger(__name__)

ANALYSES_TABLE = "cv_analyses"
UPLOADS_TABLE = "cv_uploads"
DEFAULT_PREFERRED_LOCATIONS = ["Turkey"]
DEFAULT_EXPERIENCE_LEVEL = "Not specified"
MAX_SEARCH_QUERIES = 3


class CareerProfile(BaseModel):
    user_id: str
    analysis_id: str
    primary_role: str
    alternative_roles: list[str] = Field(default_factory=list)
    experience_level: str
    skills: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    overall_score: int
    preferred_locations: list[str] = Field(default_factory=lambda: DEFAULT_PREFERRED_LOCATIONS.copy())
    remote_preference: bool | None = None


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

        logger.error("Unexpected career profile %s list item type: %s", action, type(first_item).__name__)
        raise RuntimeError("Unexpected career profile database response.")

    if isinstance(data, dict):
        return data

    logger.error("Unexpected career profile %s response type: %s", action, type(data).__name__)
    raise RuntimeError("Unexpected career profile database response.")


def _to_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized_values: list[str] = []

    for item in value:
        if not isinstance(item, str):
            continue

        normalized_item = re.sub(r"\s+", " ", item).strip()

        if normalized_item:
            normalized_values.append(normalized_item)

    return normalized_values


def _first_non_empty_string(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _normalize_skill(value: str) -> str | None:
    normalized_value = re.sub(r"\s+", " ", value).strip(" .,:;•-\n\t")

    if not normalized_value:
        return None

    return normalized_value


def _build_skills_from_strengths(strengths: list[str]) -> list[str]:
    return normalize_top_skills(strengths)


def _append_unique_query(queries: list[str], query: str) -> None:
    normalized_query = re.sub(r"\s+", " ", query).strip()

    if not normalized_query:
        return

    if any(existing_query.casefold() == normalized_query.casefold() for existing_query in queries):
        return

    queries.append(normalized_query)


def _deterministic_role_variations(primary_role: str, skills: list[str]) -> list[str]:
    normalized_role = re.sub(r"\s+", " ", primary_role).strip()
    normalized_role_lower = normalized_role.casefold()
    variations: list[str] = []

    if "backend" in normalized_role_lower:
        variations.append("Backend Developer")

    if any("python" in skill.casefold() for skill in skills):
        variations.append("Python Developer")

    if "software engineer" in normalized_role_lower:
        variations.append(normalized_role.replace("Software Engineer", "Software Developer"))
        variations.append("Software Engineer")

    if "developer" not in normalized_role_lower and "engineer" in normalized_role_lower:
        variations.append(normalized_role.replace("Engineer", "Developer"))

    return variations


def generate_search_queries(profile: CareerProfile) -> list[str]:
    queries: list[str] = []

    _append_unique_query(queries, profile.primary_role)

    for role in profile.alternative_roles:
        _append_unique_query(queries, role)

        if len(queries) >= MAX_SEARCH_QUERIES:
            return queries[:MAX_SEARCH_QUERIES]

    for role in _deterministic_role_variations(profile.primary_role, profile.skills):
        _append_unique_query(queries, role)

        if len(queries) >= MAX_SEARCH_QUERIES:
            break

    return queries[:MAX_SEARCH_QUERIES]


def _get_latest_completed_analysis(user_id: str) -> dict[str, object] | None:
    response = (
        get_supabase_client()
        .table(ANALYSES_TABLE)
        .select("*")
        .eq("user_id", user_id)
        .eq("status", "completed")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    data = _extract_response_data(response, "select latest completed analysis")
    return data if isinstance(data, dict) else None


def _get_completed_analysis_by_id(user_id: str, analysis_id: str) -> dict[str, object] | None:
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

    data = _extract_response_data(response, "select selected completed analysis")
    return data if isinstance(data, dict) else None


def _get_upload_experience_level(cv_upload_id: object, user_id: str) -> str:
    if not isinstance(cv_upload_id, str) or not cv_upload_id.strip():
        return DEFAULT_EXPERIENCE_LEVEL

    response = (
        get_supabase_client()
        .table(UPLOADS_TABLE)
        .select("id,experience_level")
        .eq("id", cv_upload_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    upload = _extract_response_data(response, "select upload experience level")

    if not isinstance(upload, dict):
        return DEFAULT_EXPERIENCE_LEVEL

    experience_level = upload.get("experience_level")

    if isinstance(experience_level, str) and experience_level.strip():
        return experience_level.strip()

    return DEFAULT_EXPERIENCE_LEVEL


def _build_career_profile(analysis: dict[str, object], experience_level: str) -> CareerProfile | None:
    user_id = analysis.get("user_id")
    analysis_id = analysis.get("id")
    primary_role = _first_non_empty_string(analysis.get("primary_role"), analysis.get("target_role"))
    overall_score = analysis.get("overall_score")

    if not isinstance(user_id, str) or not isinstance(analysis_id, str):
        return None

    if primary_role is None:
        return None

    if not isinstance(overall_score, int):
        return None

    strengths = _to_string_list(analysis.get("strengths"))
    weaknesses = _to_string_list(analysis.get("weaknesses"))
    top_skills = normalize_top_skills(analysis.get("top_skills"))
    preferred_locations = _to_string_list(analysis.get("preferred_locations")) or DEFAULT_PREFERRED_LOCATIONS.copy()
    remote_preference = analysis.get("remote_preference")

    return CareerProfile(
        user_id=user_id,
        analysis_id=analysis_id,
        primary_role=primary_role,
        alternative_roles=_to_string_list(analysis.get("alternative_roles"))[:MAX_SEARCH_QUERIES],
        experience_level=experience_level,
        skills=top_skills or _build_skills_from_strengths(strengths),
        strengths=strengths,
        weaknesses=weaknesses,
        overall_score=overall_score,
        preferred_locations=preferred_locations,
        remote_preference=remote_preference if isinstance(remote_preference, bool) else None,
    )


def get_latest_career_profile(user_id: str) -> CareerProfile | None:
    try:
        normalized_user_id = user_id.strip()

        if not normalized_user_id:
            return None

        analysis = _get_latest_completed_analysis(normalized_user_id)

        if analysis is None:
            return None

        experience_level = _get_upload_experience_level(
            cv_upload_id=analysis.get("cv_upload_id"),
            user_id=normalized_user_id,
        )
        return _build_career_profile(analysis, experience_level)
    except Exception:
        logger.exception("Unable to build latest career profile.")
        return None


def get_career_profile_for_analysis(user_id: str, analysis_id: str) -> CareerProfile | None:
    try:
        normalized_user_id = user_id.strip()
        normalized_analysis_id = analysis_id.strip()

        if not normalized_user_id or not normalized_analysis_id:
            return None

        analysis = _get_completed_analysis_by_id(normalized_user_id, normalized_analysis_id)

        if analysis is None:
            return None

        experience_level = _get_upload_experience_level(
            cv_upload_id=analysis.get("cv_upload_id"),
            user_id=normalized_user_id,
        )
        return _build_career_profile(analysis, experience_level)
    except Exception:
        logger.exception("Unable to build selected career profile.")
        return None
