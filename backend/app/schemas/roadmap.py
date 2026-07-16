from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


RoadmapPriority = Literal["low", "medium", "high", "critical"]
RoadmapStepStatus = Literal["not_started", "in_progress", "completed"]
RoadmapTaskStatus = Literal["not_started", "completed"]
RoadmapDayName = Literal[
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


class RoadmapResource(BaseModel):
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)


class RoadmapTask(BaseModel):
    id: UUID | None = None
    title: str = Field(min_length=1)
    estimated_minutes: int = Field(ge=20, le=90)
    status: RoadmapTaskStatus = "not_started"
    task_order: int | None = Field(default=None, ge=1)
    updated_at: datetime | None = None


class RoadmapDay(BaseModel):
    day_name: RoadmapDayName
    tasks: list[RoadmapTask] = Field(min_length=1, max_length=4)


class RoadmapStep(BaseModel):
    id: UUID | None = None
    week_number: int = Field(ge=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    estimated_hours: int = Field(ge=1, le=80)
    priority: RoadmapPriority
    status: RoadmapStepStatus = "not_started"
    resources: list[RoadmapResource] = Field(default_factory=list)
    mini_project: str = Field(min_length=1)
    days: list[RoadmapDay] = Field(min_length=1, max_length=7)
    updated_at: datetime | None = None


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


class UpdateRoadmapStepRequest(BaseModel):
    status: RoadmapStepStatus


class UpdateRoadmapTaskRequest(BaseModel):
    status: RoadmapTaskStatus


class RoadmapStepProgressResponse(BaseModel):
    id: UUID
    roadmap_id: UUID
    week_number: int
    status: RoadmapStepStatus
    updated_at: datetime


class RoadmapTaskProgressResponse(BaseModel):
    id: UUID
    roadmap_id: UUID
    step_id: UUID
    day_name: RoadmapDayName
    task_order: int
    title: str
    estimated_minutes: int
    status: RoadmapTaskStatus
    step_status: RoadmapStepStatus
    updated_at: datetime
