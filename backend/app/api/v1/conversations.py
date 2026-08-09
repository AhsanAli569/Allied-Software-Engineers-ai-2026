import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.csrf import verify_csrf
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.conversation import ConversationCreate, ConversationRead, ConversationUpdate
from app.services.conversation_service import get_owned_conversation, list_conversations

router = APIRouter(prefix="/conversations", tags=["conversations"], dependencies=[Depends(verify_csrf)])


@router.get("", response_model=list[ConversationRead])
async def list_my_conversations(
    search: str | None = Query(default=None, max_length=200),
    archived: bool | None = Query(default=None),
    pinned: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Conversation]:
    return await list_conversations(
        db, user.id, search=search, archived=archived, pinned=pinned, limit=limit, offset=offset
    )


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Conversation:
    conversation = Conversation(user_id=user.id, title=payload.title or "New chat", model_id=payload.model_id)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get("/{conversation_id}", response_model=ConversationRead)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Conversation:
    return await get_owned_conversation(db, conversation_id, user.id)


@router.patch("/{conversation_id}", response_model=ConversationRead)
async def update_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Conversation:
    conversation = await get_owned_conversation(db, conversation_id, user.id)

    if payload.title is not None:
        conversation.title = payload.title
    if payload.pinned is not None:
        conversation.pinned = payload.pinned
    if payload.archived is not None:
        conversation.archived = payload.archived

    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    conversation = await get_owned_conversation(db, conversation_id, user.id)
    conversation.deleted_at = datetime.now(timezone.utc)
    await db.commit()
