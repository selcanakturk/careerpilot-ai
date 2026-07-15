from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


RoadmapPriority = Literal["low", "medium", "high", "critical"]


class RoadmapResource(BaseModel):
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)


class RoadmapStep(BaseModel):
    week_number: int = Field(ge=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    estimated_hours: int = Field(ge=1, le=80)
    priority: RoadmapPriority
    resources: list[RoadmapResource] = Field(default_factory=list)
    mini_project: str = Field(min_length=1)


class CareerRoadmap(BaseModel):
    summary: str = Field(min_length=1)
    duration_weeks: int = Field(ge=4, le=24)
    estimated_job_readiness_before: int = Field(ge=0, le=100)
    estimated_job_readiness_after: int = Field(ge=0, le=100)
    steps: list[RoadmapStep] = Field(min_length=4, max_length=24)


class RoadmapGenerateResponse(BaseModel):
    id: UUID
    user_id: UUID
    analysis_id: UUID
    target_role: str
    status: str
    roadmap: CareerRoadmap
    created_at: datetime | None = None
    updated_at: datetime | None = None
