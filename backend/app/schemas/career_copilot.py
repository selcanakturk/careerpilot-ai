from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CareerCopilotRequest(BaseModel):
    analysis_id: UUID
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("Message is required.")

        return normalized_value


class CareerCopilotResponse(BaseModel):
    reply: str
