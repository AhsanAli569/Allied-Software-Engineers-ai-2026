import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.message import MessageRole, MessageStatus
from app.schemas.attachment import AttachmentRead


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    model: str | None
    provider: str | None
    status: MessageStatus
    parent_message_id: uuid.UUID | None
    edited: bool
    regeneration_number: int
    created_at: datetime
    attachments: list[AttachmentRead] = []


class SendMessageRequest(BaseModel):
    content: str = Field(default="", max_length=32000)
    model_id: str | None = None
    idempotency_key: str | None = Field(default=None, max_length=100)
    attachment_ids: list[uuid.UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_content_or_attachments(self) -> "SendMessageRequest":
        if not self.content.strip() and not self.attachment_ids:
            raise ValueError("Message must include text or at least one attachment")
        return self
