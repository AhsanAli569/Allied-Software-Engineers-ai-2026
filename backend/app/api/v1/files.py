import asyncio
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.csrf import verify_csrf
from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.database import get_db
from app.middleware.rate_limit import rate_limit
from app.models.attachment import Attachment, AttachmentKind, AttachmentStatus
from app.models.user import User
from app.schemas.attachment import AttachmentRead
from app.services.conversation_service import get_owned_conversation
from app.services.document_service import extract_text
from app.storage.local import delete_file, read_file, save_file
from app.security.file_validation import validate_upload

router = APIRouter(prefix="/conversations", tags=["files"], dependencies=[Depends(verify_csrf)])
settings = get_settings()


async def _get_owned_attachment(db: AsyncSession, conversation_id: uuid.UUID, file_id: uuid.UUID) -> Attachment:
    attachment = await db.get(Attachment, file_id)
    if not attachment or attachment.conversation_id != conversation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    return attachment


@router.post(
    "/{conversation_id}/files",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[rate_limit("upload", settings.rate_limit_upload_per_minute)],
)
async def upload_file(
    conversation_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Attachment:
    conversation = await get_owned_conversation(db, conversation_id, user.id)

    pending_count = await db.execute(
        select(func.count())
        .select_from(Attachment)
        .where(Attachment.conversation_id == conversation.id, Attachment.message_id.is_(None))
    )
    if pending_count.scalar_one() >= settings.max_attachments_per_message:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"You can attach at most {settings.max_attachments_per_message} files to a single message",
        )

    content = await file.read()
    validated = validate_upload(file.filename or "upload", content)
    storage_key = await asyncio.to_thread(save_file, user.id, validated.extension, content)

    attachment = Attachment(
        user_id=user.id,
        conversation_id=conversation.id,
        original_filename=(file.filename or "upload")[:255],
        storage_key=storage_key,
        mime_type=validated.mime_type,
        size_bytes=len(content),
        kind=validated.kind,
        status=AttachmentStatus.processing,
    )
    db.add(attachment)
    await db.flush()

    if validated.kind == AttachmentKind.document:
        attachment.extracted_text = await asyncio.to_thread(extract_text, validated.mime_type, content)

    attachment.status = AttachmentStatus.ready
    await db.commit()
    await db.refresh(attachment)
    return attachment


@router.get("/{conversation_id}/files", response_model=list[AttachmentRead])
async def list_files(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Attachment]:
    conversation = await get_owned_conversation(db, conversation_id, user.id)
    result = await db.execute(
        select(Attachment).where(Attachment.conversation_id == conversation.id).order_by(Attachment.created_at.asc())
    )
    return list(result.scalars().all())


@router.delete("/{conversation_id}/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file_endpoint(
    conversation_id: uuid.UUID,
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    conversation = await get_owned_conversation(db, conversation_id, user.id)
    attachment = await _get_owned_attachment(db, conversation.id, file_id)

    if attachment.message_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This file was already sent in a message and can't be removed")

    await asyncio.to_thread(delete_file, attachment.storage_key)
    await db.delete(attachment)
    await db.commit()


@router.get("/{conversation_id}/files/{file_id}/content")
async def get_file_content(
    conversation_id: uuid.UUID,
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    conversation = await get_owned_conversation(db, conversation_id, user.id)
    attachment = await _get_owned_attachment(db, conversation.id, file_id)
    content = await asyncio.to_thread(read_file, attachment.storage_key)
    return Response(content=content, media_type=attachment.mime_type)
