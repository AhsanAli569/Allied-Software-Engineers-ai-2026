import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    model_id: str | None
    pinned: bool
    archived: bool
    created_at: datetime
    updated_at: datetime


class ConversationCreate(BaseModel):
    model_id: str | None = None
    title: str | None = None


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    pinned: bool | None = None
    archived: bool | None = None
