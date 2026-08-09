import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    username: str
    email: str
    role: UserRole
    created_at: datetime
