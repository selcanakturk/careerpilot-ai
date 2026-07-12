from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CVAnalysisResult(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    summary: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    skill_gaps: list[str] = Field(default_factory=list)
    cv_suggestions: list[str] = Field(default_factory=list)


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
    created_at: datetime
    updated_at: datetime
