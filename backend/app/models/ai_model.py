from sqlalchemy import Boolean, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AIModel(Base):
    """Database-driven model registry. Admins enable/disable/reprioritize without a redeploy."""

    __tablename__ = "ai_models"

    model_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(150))
    provider: Mapped[str] = mapped_column(String(50), index=True)
    context_length: Mapped[int] = mapped_column(Integer, default=8192)
    multimodal: Mapped[bool] = mapped_column(Boolean, default=False)
    vision_support: Mapped[bool] = mapped_column(Boolean, default=False)
    document_support: Mapped[bool] = mapped_column(Boolean, default=False)
    coding_support: Mapped[bool] = mapped_column(Boolean, default=True)
    reasoning_support: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    free_or_paid: Mapped[str] = mapped_column(String(10), default="free")
    rate_limit_info: Mapped[dict] = mapped_column(JSON, default=dict)
