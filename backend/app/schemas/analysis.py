from datetime import datetime
import re
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


MAX_TOP_SKILLS = 8
MAX_SKILL_WORDS = 4
MAX_SKILL_CHARACTERS = 36

KNOWN_TECH_SKILLS: tuple[tuple[str, str], ...] = (
    ("javascript", "JavaScript"),
    ("typescript", "TypeScript"),
    ("python", "Python"),
    ("django", "Django"),
    ("fastapi", "FastAPI"),
    ("flask", "Flask"),
    ("react native", "React Native"),
    ("react", "React"),
    ("flutter", "Flutter"),
    ("node.js", "Node.js"),
    ("node js", "Node.js"),
    ("nodejs", "Node.js"),
    ("express.js", "Express"),
    ("express", "Express"),
    ("mongodb", "MongoDB"),
    ("postgresql", "PostgreSQL"),
    ("postgres", "PostgreSQL"),
    ("mysql", "MySQL"),
    ("sql", "SQL"),
    ("redis", "Redis"),
    ("docker", "Docker"),
    ("kubernetes", "Kubernetes"),
    ("aws", "AWS"),
    ("azure", "Azure"),
    ("gcp", "GCP"),
    ("git", "Git"),
    ("graphql", "GraphQL"),
    ("rest api", "REST API"),
    ("restful api", "REST API"),
    ("api design", "API Design"),
    ("html", "HTML"),
    ("css", "CSS"),
    ("tailwind", "Tailwind CSS"),
    ("tailwind css", "Tailwind CSS"),
)

SENTENCE_MARKERS = (
    "experience with",
    "hands-on",
    "hands on",
    "knowledge of",
    "familiarity with",
    "proficiency in",
    "proficient in",
    "holds ",
    "degree",
    "university",
    "portfolio",
    "showcasing",
    "strong project",
    "worked on",
    "responsible for",
    "including ",
)


def _canonical_key(value: str) -> str:
    return re.sub(r"[^a-z0-9+#.]+", " ", value.casefold()).strip()


def _normalize_skill_label(value: str) -> str:
    normalized_value = re.sub(r"\s+", " ", value).strip(" .,:;•-\n\t")
    normalized_key = _canonical_key(normalized_value)

    for skill_key, label in KNOWN_TECH_SKILLS:
        if normalized_key == _canonical_key(skill_key):
            return label

    return normalized_value


def _looks_like_skill_sentence(value: str) -> bool:
    normalized_value = re.sub(r"\s+", " ", value).strip()
    normalized_key = normalized_value.casefold()
    word_count = len(re.findall(r"[A-Za-zÀ-ÿ0-9+#.]+", normalized_value))

    if len(normalized_value) > MAX_SKILL_CHARACTERS or word_count > MAX_SKILL_WORDS:
        return True

    return any(marker in normalized_key for marker in SENTENCE_MARKERS)


def _extract_known_skills(value: str) -> list[str]:
    normalized_key = f" {_canonical_key(value)} "
    extracted: list[str] = []
    seen: set[str] = set()

    for skill_key, label in KNOWN_TECH_SKILLS:
        skill_pattern = re.escape(_canonical_key(skill_key)).replace("\\ ", r"\s+")

        if not re.search(rf"(?<![a-z0-9+#.]){skill_pattern}(?![a-z0-9+#.])", normalized_key):
            continue

        dedupe_key = label.casefold()

        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        extracted.append(label)

    return extracted


def normalize_top_skills(values: object) -> list[str]:
    if not isinstance(values, list):
        return []

    normalized_skills: list[str] = []
    seen_skills: set[str] = set()

    for item in values:
        if not isinstance(item, str):
            continue

        normalized_item = re.sub(r"\s+", " ", item).strip(" .,:;•-\n\t")

        if not normalized_item:
            continue

        candidates = (
            _extract_known_skills(normalized_item)
            if _looks_like_skill_sentence(normalized_item)
            else [_normalize_skill_label(normalized_item)]
        )

        for candidate in candidates:
            dedupe_key = _canonical_key(candidate)

            if not dedupe_key or dedupe_key in seen_skills:
                continue

            seen_skills.add(dedupe_key)
            normalized_skills.append(candidate)

            if len(normalized_skills) >= MAX_TOP_SKILLS:
                return normalized_skills

    return normalized_skills


class CVAnalysisResult(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    summary: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    skill_gaps: list[str] = Field(default_factory=list)
    cv_suggestions: list[str] = Field(default_factory=list)
    primary_role: str | None = None
    alternative_roles: list[str] = Field(default_factory=list, max_length=3)
    top_skills: list[str] = Field(default_factory=list, max_length=8)
    preferred_job_types: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=lambda: ["Turkey"])
    remote_preference: bool | None = None

    @field_validator("top_skills", mode="before")
    @classmethod
    def validate_top_skills(cls, value: object) -> list[str]:
        return normalize_top_skills(value)


class CVAnalysisResponse(BaseModel):
    id: UUID
    user_id: UUID
    cv_upload_id: UUID
    target_role: str
    status: str
    overall_score: int
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    skill_gaps: list[str]
    cv_suggestions: list[str]
    primary_role: str | None = None
    alternative_roles: list[str] = Field(default_factory=list)
    top_skills: list[str] = Field(default_factory=list)
    preferred_job_types: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=lambda: ["Turkey"])
    remote_preference: bool | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("top_skills", mode="before")
    @classmethod
    def validate_top_skills(cls, value: object) -> list[str]:
        return normalize_top_skills(value)


class DeleteAnalysisResponse(BaseModel):
    id: UUID
    cv_upload_id: UUID
    message: str
