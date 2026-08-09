import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message


async def get_owned_conversation(db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Conversation:
    """Every conversation lookup MUST go through this: scoped by user_id, never conversation_id alone.
    Prevents IDOR — a user requesting another user's conversation_id gets a 404, not a 403,
    so existence of other users' conversations is never leaked.
    """
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
            Conversation.deleted_at.is_(None),
        )
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return conversation


async def list_conversations(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    search: str | None = None,
    archived: bool | None = None,
    pinned: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Conversation]:
    query = select(Conversation).where(Conversation.user_id == user_id, Conversation.deleted_at.is_(None))

    if search:
        like = f"%{search}%"
        query = query.where(
            or_(
                Conversation.title.ilike(like),
                Conversation.id.in_(
                    select(Message.conversation_id).where(Message.content.ilike(like))
                ),
            )
        )
    if archived is not None:
        query = query.where(Conversation.archived == archived)
    if pinned is not None:
        query = query.where(Conversation.pinned == pinned)

    query = query.order_by(Conversation.pinned.desc(), Conversation.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())
