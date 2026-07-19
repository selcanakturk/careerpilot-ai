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

SKILL_ALIASES = {
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "node js": "Node.js",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "rest api": "REST API",
    "rest apis": "REST API",
    "restapi": "REST API",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "postgre sql": "PostgreSQL",
    "python": "Python",
    "fastapi": "FastAPI",
    "django": "Django",
    "docker": "Docker",
    "aws": "AWS",
    "gcp": "GCP",
}


class DeterministicJobMatch(BaseModel):
    match_score: int
    matched_skills: list[str]
    missing_skills: list[str]
    match_reasons: list[str]


def _normalize_token(token: str) -> str:
    if token in {"redis", "kubernetes", "javascript", "typescript", "express"}:
        return token

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


def canonical_skill(value: object) -> str:
    normalized = normalize_text(value)

    if not normalized:
        return ""

    compacted = _compact(normalized)

    alias_by_compact = {
        _compact(normalize_text(alias)): display_label
        for alias, display_label in SKILL_ALIASES.items()
    }

    if compacted in alias_by_compact:
        return _compact(normalize_text(alias_by_compact[compacted]))

    return compacted


def display_skill_label(value: str) -> str:
    skill_key = canonical_skill(value)

    for display_label in SKILL_ALIASES.values():
        if canonical_skill(display_label) == skill_key:
            return display_label

    normalized = re.sub(r"\s+", " ", value).strip()
    return normalized


def _contains_skill(job_text: str, skill: str) -> bool:
    normalized_skill = normalize_text(skill)

    if not normalized_skill:
        return False

    compacted_job_text = _compact(job_text)
    skill_key = canonical_skill(skill)

    if normalized_skill in job_text or skill_key in compacted_job_text:
        return True

    return any(
        alias_text in job_text or _compact(alias_text) in compacted_job_text
        for alias, display_label in SKILL_ALIASES.items()
        if canonical_skill(display_label) == skill_key
        for alias_text in (normalize_text(alias),)
    )


def _unique_skills(skills: list[str]) -> list[str]:
    unique_skills: list[str] = []
    seen_skills: set[str] = set()

    for skill in skills:
        normalized_skill = canonical_skill(skill)

        if not normalized_skill or normalized_skill in seen_skills:
            continue

        seen_skills.add(normalized_skill)
        unique_skills.append(display_skill_label(skill))

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


def _role_match_reason(job: ExternalJobPosting | dict[str, Any], profile: CareerProfile) -> str | None:
    title = _title_text(job)

    if not title:
        return None

    primary_role = normalize_text(profile.primary_role)

    if primary_role and primary_role in title:
        return "This role matches your primary career goal."

    for alternative_role in profile.alternative_roles:
        normalized_alternative = normalize_text(alternative_role)

        if normalized_alternative and normalized_alternative in title:
            return "Matches one of your preferred roles."

    return None


def _experience_match_reason(job: ExternalJobPosting | dict[str, Any], profile: CareerProfile) -> str | None:
    experience_score = _experience_score(job, profile)

    if experience_score is None or experience_score < 100:
        return None

    return "This role fits your experience level."


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
    profile_skill_keys = {canonical_skill(skill) for skill in profile.skills}
    missing_skills: list[str] = []

    for skill in TECHNICAL_SKILL_KEYWORDS:
        normalized_skill = canonical_skill(skill)

        if normalized_skill in profile_skill_keys:
            continue

        if _contains_skill(job_text, skill):
            missing_skills.append(display_skill_label(skill))

    return _unique_skills(missing_skills)


def generate_match_reasons(
    job: ExternalJobPosting | dict[str, Any],
    profile: CareerProfile,
    matched_skills: list[str] | None = None,
) -> list[str]:
    reasons: list[str] = []

    role_reason = _role_match_reason(job, profile)

    if role_reason:
        reasons.append(role_reason)

    skills = matched_skills if matched_skills is not None else _skill_match(job, profile)[1]

    for skill in skills[:2]:
        reasons.append(f"Your {skill} experience is relevant.")

        if len(reasons) >= 3:
            return reasons

    experience_reason = _experience_match_reason(job, profile)

    if experience_reason:
        reasons.append(experience_reason)

    return reasons[:3]


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
        match_reasons=generate_match_reasons(job, career_profile, matched_skills),
    )
