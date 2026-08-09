import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_model import AIModel
from app.models.message import Message, MessageRole, MessageStatus
from app.providers.base import ChatMessage
from app.services.system_prompt import SYSTEM_PROMPT

CONTEXT_WINDOW_MESSAGES = 20


async def get_routing_candidates(
    db: AsyncSession, requested_model_id: str | None, require_vision: bool = False
) -> list[AIModel]:
    """Active models ordered by priority, with the user's requested model (if active) moved
    to the front so it's tried first; the rest form the fallback chain. When the message
    includes image attachments, candidates are restricted to vision-capable models — a
    text-only model would just silently ignore the image, which is worse than a clear
    "no provider available" if none are configured.
    """
    query = select(AIModel).where(AIModel.active.is_(True))
    if require_vision:
        query = query.where(AIModel.vision_support.is_(True))
    result = await db.execute(query.order_by(AIModel.priority.asc()))
    models = list(result.scalars().all())

    if requested_model_id:
        preferred = next((m for m in models if m.model_id == requested_model_id), None)
        if preferred:
            models.remove(preferred)
            models.insert(0, preferred)

    return models


async def build_context_messages(
    db: AsyncSession, conversation_id: uuid.UUID, before: datetime | None = None
) -> list[ChatMessage]:
    """Builds the recent-message context window. `before` excludes anything at or after that
    timestamp — used by regenerate so the response being replaced (and anything after it)
    isn't fed back in as its own context.
    """
    query = select(Message).where(
        Message.conversation_id == conversation_id,
        Message.status == MessageStatus.complete,
        Message.role.in_([MessageRole.user, MessageRole.assistant]),
    )
    if before is not None:
        query = query.where(Message.created_at < before)

    result = await db.execute(query.order_by(Message.created_at.desc()).limit(CONTEXT_WINDOW_MESSAGES))
    recent = list(reversed(result.scalars().all()))

    history = [ChatMessage(role="system", content=SYSTEM_PROMPT)]
    history.extend(ChatMessage(role=m.role.value, content=m.content) for m in recent)
    return history
