import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import GUID


class AttachmentKind(str, enum.Enum):
    image = "image"
    document = "document"


class AttachmentStatus(str, enum.Enum):
    uploading = "uploading"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[AttachmentKind] = mapped_column(Enum(AttachmentKind, native_enum=False))
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AttachmentStatus] = mapped_column(
        Enum(AttachmentStatus, native_enum=False), default=AttachmentStatus.uploading
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
