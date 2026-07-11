from pydantic import BaseModel, Field


class CVAnalysisResult(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    summary: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    skill_gaps: list[str] = Field(default_factory=list)
    cv_suggestions: list[str] = Field(default_factory=list)

