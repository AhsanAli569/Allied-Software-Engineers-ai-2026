import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.types import GUID


class MessageRole(str, enum.Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"


class MessageStatus(str, enum.Enum):
    pending = "pending"
    streaming = "streaming"
    complete = "complete"
    cancelled = "cancelled"
    failed = "failed"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, native_enum=False))
    content: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[MessageStatus] = mapped_column(Enum(MessageStatus, native_enum=False), default=MessageStatus.complete)
    parent_message_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("messages.id"), nullable=True)
    edited: Mapped[bool] = mapped_column(Boolean, default=False)
    regeneration_number: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    attachments: Mapped[list["Attachment"]] = relationship(order_by="Attachment.created_at")
