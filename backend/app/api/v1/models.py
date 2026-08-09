from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.ai_model import AIModel
from app.models.user import User
from app.providers.factory import is_provider_configured

router = APIRouter(prefix="/models", tags=["models"])


class ModelRead(BaseModel):
    model_id: str
    display_name: str
    provider: str
    context_length: int
    multimodal: bool
    vision_support: bool
    document_support: bool
    coding_support: bool
    reasoning_support: bool
    free_or_paid: str
    configured: bool  # whether this provider currently has an API key set — the frontend
    # uses this to avoid defaulting to / letting the user pick a model that can't work yet


@router.get("", response_model=list[ModelRead])
async def list_active_models(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[ModelRead]:
    result = await db.execute(select(AIModel).where(AIModel.active.is_(True)).order_by(AIModel.priority.asc()))
    models = list(result.scalars().all())

    return [
        ModelRead(
            model_id=m.model_id,
            display_name=m.display_name,
            provider=m.provider,
            context_length=m.context_length,
            multimodal=m.multimodal,
            vision_support=m.vision_support,
            document_support=m.document_support,
            coding_support=m.coding_support,
            reasoning_support=m.reasoning_support,
            free_or_paid=m.free_or_paid,
            configured=is_provider_configured(m.provider),
        )
        for m in models
    ]
