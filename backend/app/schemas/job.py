from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


EmploymentType = Literal["full_time", "part_time", "internship", "contract", "freelance"]
WorkMode = Literal["onsite", "hybrid", "remote"]
ApplicationReadiness = Literal["low", "medium", "high"]


class CreateJobPostingRequest(BaseModel):
    title: str
    company_name: str
    location: str | None = None
    employment_type: EmploymentType | None = None
    work_mode: WorkMode | None = None
    source_url: str | None = None
    description: str

    @field_validator("title", "company_name", "description")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("This field is required.")

        return normalized_value

    @field_validator("location", "source_url")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None


class JobPostingResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    company_name: str
    location: str | None = None
    employment_type: EmploymentType | None = None
    work_mode: WorkMode | None = None
    source_url: str | None = None
    description: str
    status: Literal["saved", "analyzing", "analyzed", "archived"]
    created_at: datetime
    updated_at: datetime


class JobMatchAIResult(BaseModel):
    match_score: int = Field(ge=0, le=100)
    summary: str = Field(min_length=1)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    application_readiness: ApplicationReadiness


class JobMatchResponse(BaseModel):
    id: UUID
    user_id: UUID
    job_posting_id: UUID
    analysis_id: UUID
    match_score: int
    summary: str
    matched_skills: list[str]
    missing_skills: list[str]
    strengths: list[str]
    risks: list[str]
    recommendations: list[str]
    application_readiness: ApplicationReadiness
    created_at: datetime
    updated_at: datetime


class ExternalJobPosting(BaseModel):
    external_id: str
    source: Literal["jsearch", "jooble", "adzuna"]
    title: str
    company_name: str
    location: str | None = None
    description: str
    source_url: str
    created_at: datetime | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    employment_type: EmploymentType | None = None
    work_mode: WorkMode | None = None
    category: str | None = None


class JobSearchResponse(BaseModel):
    jobs: list[ExternalJobPosting]
    page: int
    results_per_page: int
    total_results: int | None = None
    query: str
    location: str | None = None
    providers_used: list[str] = Field(default_factory=list)
    providers_failed: list[str] = Field(default_factory=list)
