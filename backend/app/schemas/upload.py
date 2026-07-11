from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CVUploadResponse(BaseModel):
    id: UUID
    user_id: UUID
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    target_role: str
    experience_level: str
    created_at: datetime

