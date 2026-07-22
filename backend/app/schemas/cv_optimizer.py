from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


JobProvider = Literal["jsearch", "adzuna", "jooble"]


class CVOptimizeRequest(BaseModel):
    analysis_id: str
    job_external_id: str
    provider: JobProvider

    @field_validator("analysis_id", "job_external_id")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("This field is required.")

        return normalized_value


class OptimizedCV(BaseModel):
    headline: str = ""
    summary: str = ""
    experience: list[dict[str, Any] | str] = Field(default_factory=list)
    projects: list[dict[str, Any] | str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    education: list[dict[str, Any] | str] = Field(default_factory=list)
    certifications: list[dict[str, Any] | str] = Field(default_factory=list)
    additional_sections: dict[str, Any] = Field(default_factory=dict)

    @field_validator("headline", "summary", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> str:
        return value.strip() if isinstance(value, str) else ""

    @field_validator(
        "experience",
        "projects",
        "skills",
        "education",
        "certifications",
        mode="before",
    )
    @classmethod
    def normalize_list_section(cls, value: object) -> list[object]:
        return value if isinstance(value, list) else []

    @field_validator("additional_sections", mode="before")
    @classmethod
    def normalize_additional_sections(cls, value: object) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @model_validator(mode="after")
    def validate_has_content(self) -> "OptimizedCV":
        has_text = bool(self.headline or self.summary)
        has_list_content = any(
            [
                self.experience,
                self.projects,
                self.skills,
                self.education,
                self.certifications,
            ]
        )
        has_additional_content = bool(self.additional_sections)

        if not (has_text or has_list_content or has_additional_content):
            raise ValueError("optimized_cv must include at least one populated section.")

        return self


class CVOptimizerResult(BaseModel):
    match_before: int = Field(ge=0, le=100)
    estimated_match_after: int = Field(ge=0, le=100)
    changes: list[str] = Field(default_factory=list)
    optimized_cv: OptimizedCV


class CVOptimizeResponse(CVOptimizerResult):
    analysis_id: str
    job_external_id: str
    provider: JobProvider
