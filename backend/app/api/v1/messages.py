import asyncio
import base64
import json
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.csrf import verify_csrf
from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.database import get_db
from app.middleware.rate_limit import rate_limit
from app.models.attachment import Attachment, AttachmentKind
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole, MessageStatus
from app.models.user import User
from app.providers.base import ChatMessage, ImagePart
from app.providers.exceptions import AllProvidersExhaustedError, ProviderMidStreamError
from app.providers.factory import get_provider
from app.providers.router import stream_chat_with_fallback
from app.schemas.message import MessageRead, SendMessageRequest
from app.security.sanitize import normalize_user_content
from app.services.conversation_service import get_owned_conversation
from app.services.knowledge_service import augment_with_business_knowledge
from app.services.message_service import build_context_messages, get_routing_candidates
from app.services.title_service import generate_title_from_message
from app.storage.local import read_file

router = APIRouter(prefix="/conversations", tags=["messages"], dependencies=[Depends(verify_csrf)])
settings = get_settings()

# Dev-only in-memory idempotency guard: prevents a client network retry from creating a
# duplicate user message. Keyed by (user_id, idempotency_key); entries expire after 5 minutes.
_IDEMPOTENCY_TTL_SECONDS = 300.0
_seen_idempotency_keys: dict[str, float] = {}


def _check_idempotency(user_id: uuid.UUID, key: str | None) -> None:
    if not key:
        return
    cache_key = f"{user_id}:{key}"
    now = time.monotonic()
    for k in [k for k, ts in _seen_idempotency_keys.items() if now - ts > _IDEMPOTENCY_TTL_SECONDS]:
        _seen_idempotency_keys.pop(k, None)
    if cache_key in _seen_idempotency_keys:
        raise HTTPException(status.HTTP_409_CONFLICT, "This message was already submitted")
    _seen_idempotency_keys[cache_key] = now


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


async def _claim_attachments(
    db: AsyncSession, conversation: Conversation, user: User, attachment_ids: list[uuid.UUID]
) -> list[Attachment]:
    """Validates the requested attachments belong to this user/conversation and haven't
    already been used by another message, then returns them (still unattached — the caller
    sets message_id once the user Message row exists).
    """
    if not attachment_ids:
        return []

    if len(attachment_ids) > settings.max_attachments_per_message:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"You can attach at most {settings.max_attachments_per_message} files"
        )

    result = await db.execute(select(Attachment).where(Attachment.id.in_(attachment_ids)))
    found = {a.id: a for a in result.scalars().all()}

    attachments = []
    for attachment_id in attachment_ids:
        attachment = found.get(attachment_id)
        if (
            not attachment
            or attachment.user_id != user.id
            or attachment.conversation_id != conversation.id
            or attachment.message_id is not None
        ):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "One or more attachments are invalid or already used")
        attachments.append(attachment)
    return attachments


async def _augment_last_message_with_attachments(context: list[ChatMessage], attachments: list[Attachment]) -> bool:
    """Mutates the last (just-sent) ChatMessage in `context` to include document text and
    image data for the provider call. Returns True if any image attachment requires routing
    to a vision-capable model.
    """
    if not attachments or not context:
        return False

    last = context[-1]
    doc_blocks = []
    images: list[ImagePart] = []

    for attachment in attachments:
        if attachment.kind == AttachmentKind.document:
            text = attachment.extracted_text or "(no extractable text found in this document)"
            doc_blocks.append(f"[Document: {attachment.original_filename}]\n{text}")
        else:
            data = await asyncio.to_thread(read_file, attachment.storage_key)
            images.append(ImagePart(mime_type=attachment.mime_type, data_base64=base64.b64encode(data).decode()))

    augmented_content = last.content
    if doc_blocks:
        augmented_content = (augmented_content + "\n\n" + "\n\n".join(doc_blocks)).strip()

    context[-1] = ChatMessage(role=last.role, content=augmented_content, images=images or None)
    return bool(images)


@router.get("/{conversation_id}/messages", response_model=list[MessageRead])
async def list_messages(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Message]:
    await get_owned_conversation(db, conversation_id, user.id)
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .options(selectinload(Message.attachments))
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


async def _generate_and_stream(
    request: Request,
    db: AsyncSession,
    conversation: Conversation,
    context: list[ChatMessage],
    model_id: str | None,
    parent_message_id: uuid.UUID | None,
    regeneration_number: int,
    require_vision: bool = False,
) -> AsyncIterator[bytes]:
    candidates = await get_routing_candidates(db, model_id or conversation.model_id, require_vision=require_vision)

    assistant_message: Message | None = None
    selected: dict[str, str] = {}

    def on_provider_selected(selected_model: str, provider_name: str) -> None:
        selected["model"] = selected_model
        selected["provider"] = provider_name

    accumulated = ""
    try:
        async for text_chunk in stream_chat_with_fallback(candidates, context, on_provider_selected):
            if assistant_message is None:
                assistant_message = Message(
                    conversation_id=conversation.id,
                    role=MessageRole.assistant,
                    content="",
                    model=selected.get("model"),
                    provider=selected.get("provider"),
                    status=MessageStatus.streaming,
                    parent_message_id=parent_message_id,
                    regeneration_number=regeneration_number,
                )
                db.add(assistant_message)
                await db.commit()
                await db.refresh(assistant_message)
                yield _sse("start", {"message_id": str(assistant_message.id), "model": selected.get("model"), "provider": selected.get("provider")})

            accumulated += text_chunk
            yield _sse("chunk", {"text": text_chunk})

            if await request.is_disconnected():
                assistant_message.content = accumulated
                assistant_message.status = MessageStatus.cancelled
                await db.commit()
                return

        if assistant_message is not None:
            assistant_message.content = accumulated
            assistant_message.status = MessageStatus.complete
            conversation.updated_at = datetime.now(timezone.utc)
            await db.commit()
            yield _sse("done", {"message_id": str(assistant_message.id)})
        else:
            yield _sse("error", {"message": "No response was generated. Please try again."})

    except ProviderMidStreamError:
        if assistant_message is not None:
            assistant_message.content = accumulated
            assistant_message.status = MessageStatus.failed
            await db.commit()
        yield _sse("error", {"message": "ASE AI is experiencing high demand. Please try again."})

    except AllProvidersExhaustedError:
        if require_vision:
            yield _sse("error", {"message": "No vision-capable AI provider is currently available for image attachments."})
        else:
            yield _sse("error", {"message": "No AI provider is currently available. Please try again shortly."})


@router.post("/{conversation_id}/messages/stream", dependencies=[rate_limit("chat", settings.rate_limit_chat_per_minute)])
async def send_message(
    conversation_id: uuid.UUID,
    payload: SendMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    conversation = await get_owned_conversation(db, conversation_id, user.id)
    _check_idempotency(user.id, payload.idempotency_key)

    attachments = await _claim_attachments(db, conversation, user, payload.attachment_ids)
    content = normalize_user_content(payload.content)

    existing_count = await db.execute(select(Message.id).where(Message.conversation_id == conversation.id).limit(1))
    is_first_message = existing_count.scalar_one_or_none() is None

    user_message = Message(
        conversation_id=conversation.id, role=MessageRole.user, content=content, status=MessageStatus.complete
    )
    db.add(user_message)
    await db.flush()

    for attachment in attachments:
        attachment.message_id = user_message.id

    if is_first_message:
        if content:
            conversation.title = generate_title_from_message(content)
        elif attachments:
            conversation.title = attachments[0].original_filename[:60]
        else:
            conversation.title = "New chat"
    conversation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user_message)

    context = await build_context_messages(db, conversation.id)
    await augment_with_business_knowledge(db, get_provider("gemini"), context)
    require_vision = await _augment_last_message_with_attachments(context, attachments)

    return StreamingResponse(
        _generate_and_stream(request, db, conversation, context, payload.model_id, user_message.id, 0, require_vision),
        media_type="text/event-stream",
    )


@router.post("/{conversation_id}/messages/{message_id}/regenerate")
async def regenerate_message(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    conversation = await get_owned_conversation(db, conversation_id, user.id)

    original = await db.get(Message, message_id)
    if not original or original.conversation_id != conversation.id or original.role != MessageRole.assistant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found")

    result = await db.execute(
        select(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.created_at < original.created_at,
            Message.role == MessageRole.user,
        )
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    prior_user_message = result.scalar_one_or_none()
    parent_id = original.parent_message_id or (prior_user_message.id if prior_user_message else None)

    result = await db.execute(
        select(Message).where(
            Message.conversation_id == conversation.id, Message.parent_message_id == parent_id
        )
    )
    max_regen = max((m.regeneration_number for m in result.scalars().all()), default=original.regeneration_number)

    # Context excludes the response being replaced and anything after it.
    context = await build_context_messages(db, conversation.id, before=original.created_at)
    await augment_with_business_knowledge(db, get_provider("gemini"), context)

    require_vision = False
    if prior_user_message:
        attachments_result = await db.execute(
            select(Attachment).where(Attachment.message_id == prior_user_message.id)
        )
        require_vision = await _augment_last_message_with_attachments(context, list(attachments_result.scalars().all()))

    return StreamingResponse(
        _generate_and_stream(request, db, conversation, context, original.model, parent_id, max_regen + 1, require_vision),
        media_type="text/event-stream",
    )
