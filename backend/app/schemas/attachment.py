import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.attachment import AttachmentKind, AttachmentStatus


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    kind: AttachmentKind
    status: AttachmentStatus
    created_at: datetime
