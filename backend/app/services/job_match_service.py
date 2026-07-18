import re
from typing import Any

from pydantic import BaseModel

from app.schemas.job import ExternalJobPosting
from app.services.career_profile_service import CareerProfile


MAX_PROFILE_SKILLS = 10
TECHNICAL_SKILL_KEYWORDS = (
    "python",
    "fastapi",
    "django",
    "flask",
    "typescript",
    "javascript",
    "react",
    "node.js",
    "nodejs",
    "sql",
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "rest api",
    "graphql",
    "ci cd",
    "git",
    "linux",
    "microservices",
)


class DeterministicJobMatch(BaseModel):
    match_score: int
    matched_skills: list[str]
    missing_skills: list[str]


def _normalize_token(token: str) -> str:
    if len(token) > 3 and token.endswith("ies"):
        return f"{token[:-3]}y"

    if len(token) > 3 and token.endswith("s"):
        return token[:-1]

    return token


def normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return ""

    normalized = value.casefold()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9+#.]+", " ", normalized)
    normalized = normalized.replace("node js", "nodejs")
    tokens = [_normalize_token(token) for token in normalized.split()]
    return " ".join(tokens)


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9+#]+", "", value)


def _contains_skill(job_text: str, skill: str) -> bool:
    normalized_skill = normalize_text(skill)

    if not normalized_skill:
        return False

    return normalized_skill in job_text or _compact(normalized_skill) in _compact(job_text)


def _unique_skills(skills: list[str]) -> list[str]:
    unique_skills: list[str] = []
    seen_skills: set[str] = set()

    for skill in skills:
        normalized_skill = normalize_text(skill)

        if not normalized_skill or normalized_skill in seen_skills:
            continue

        seen_skills.add(normalized_skill)
        unique_skills.append(skill.strip())

    return unique_skills


def _job_value(job: ExternalJobPosting | dict[str, Any], field_name: str) -> object:
    if isinstance(job, dict):
        return job.get(field_name)

    return getattr(job, field_name, None)


def _job_text(job: ExternalJobPosting | dict[str, Any]) -> str:
    text_parts = [
        _job_value(job, "title"),
        _job_value(job, "company_name"),
        _job_value(job, "description"),
        _job_value(job, "employment_type"),
        _job_value(job, "location"),
        _job_value(job, "category"),
        _job_value(job, "requirements"),
        _job_value(job, "skills"),
    ]
    flattened_parts: list[str] = []

    for part in text_parts:
        if isinstance(part, str):
            flattened_parts.append(part)
        elif isinstance(part, list):
            flattened_parts.extend(item for item in part if isinstance(item, str))

    return normalize_text(" ".join(flattened_parts))


def _title_text(job: ExternalJobPosting | dict[str, Any]) -> str:
    return normalize_text(_job_value(job, "title"))


def _role_score(job: ExternalJobPosting | dict[str, Any], profile: CareerProfile) -> int | None:
    title = _title_text(job)

    if not title:
        return None

    primary_role = normalize_text(profile.primary_role)

    if primary_role and primary_role in title:
        return 100

    for alternative_role in profile.alternative_roles:
        normalized_alternative = normalize_text(alternative_role)

        if normalized_alternative and normalized_alternative in title:
            return 75

    role_tokens = set(primary_role.split())
    title_tokens = set(title.split())

    if not role_tokens or not title_tokens:
        return 0

    overlap_ratio = len(role_tokens & title_tokens) / len(role_tokens)
    return round(overlap_ratio * 60)


def _extract_experience_level(job_text: str) -> str | None:
    level_patterns = (
        ("junior", ("intern", "internship", "junior", "entry level", "entry")),
        ("mid", ("mid", "mid level", "intermediate")),
        ("senior", ("senior", "lead", "principal", "staff")),
    )

    for level, markers in level_patterns:
        if any(marker in job_text for marker in markers):
            return level

    return None


def _normalize_profile_experience(experience_level: str) -> str | None:
    normalized = normalize_text(experience_level)

    if "junior" in normalized or "entry" in normalized or "intern" in normalized:
        return "junior"

    if "senior" in normalized or "lead" in normalized or "principal" in normalized or "staff" in normalized:
        return "senior"

    if "mid" in normalized or "intermediate" in normalized:
        return "mid"

    return None


def _experience_score(job: ExternalJobPosting | dict[str, Any], profile: CareerProfile) -> int | None:
    job_level = _extract_experience_level(_job_text(job))
    profile_level = _normalize_profile_experience(profile.experience_level)

    if job_level is None or profile_level is None:
        return None

    if job_level == profile_level:
        return 100

    ordered_levels = {"junior": 0, "mid": 1, "senior": 2}
    distance = abs(ordered_levels[job_level] - ordered_levels[profile_level])
    return 60 if distance == 1 else 20


def _skill_match(job: ExternalJobPosting | dict[str, Any], profile: CareerProfile) -> tuple[int | None, list[str]]:
    profile_skills = _unique_skills(profile.skills[:MAX_PROFILE_SKILLS])

    if not profile_skills:
        return None, []

    job_text = _job_text(job)
    matched_skills = [skill for skill in profile_skills if _contains_skill(job_text, skill)]
    score = round((len(matched_skills) / len(profile_skills)) * 100)

    return score, matched_skills


def _extract_missing_skills(job: ExternalJobPosting | dict[str, Any], profile: CareerProfile) -> list[str]:
    job_text = _job_text(job)
    profile_skill_keys = {normalize_text(skill) for skill in profile.skills}
    missing_skills: list[str] = []

    for skill in TECHNICAL_SKILL_KEYWORDS:
        normalized_skill = normalize_text(skill)

        if normalized_skill in profile_skill_keys:
            continue

        if _contains_skill(job_text, normalized_skill):
            label = "Node.js" if normalized_skill == "nodejs" else skill.upper() if skill in {"aws", "gcp"} else skill.title()
            missing_skills.append(label)

    return _unique_skills(missing_skills)


def calculate_job_match(
    job: ExternalJobPosting | dict[str, Any],
    career_profile: CareerProfile,
) -> DeterministicJobMatch:
    weighted_scores: list[tuple[int, int]] = []

    skill_score, matched_skills = _skill_match(job, career_profile)

    if skill_score is not None:
        weighted_scores.append((skill_score, 70))

    role_score = _role_score(job, career_profile)

    if role_score is not None:
        weighted_scores.append((role_score, 20))

    experience_score = _experience_score(job, career_profile)

    if experience_score is not None:
        weighted_scores.append((experience_score, 10))

    if not weighted_scores:
        match_score = 0
    else:
        total_weight = sum(weight for _score, weight in weighted_scores)
        match_score = round(sum(score * weight for score, weight in weighted_scores) / total_weight)

    return DeterministicJobMatch(
        match_score=max(0, min(100, match_score)),
        matched_skills=matched_skills,
        missing_skills=_extract_missing_skills(job, career_profile),
    )
