import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.types import GUID


class KnowledgeChunk(Base):
    """A chunk of ingested business-knowledge text plus its embedding vector, used to give
    ASE AI grounded answers about Allied Software Engineers (services, policies, etc.)
    instead of guessing. Populated via `python -m app.cli ingest-knowledge <path>`, not
    user-facing — this is separate from per-conversation file attachments.
    """

    __tablename__ = "knowledge_chunks"
    __table_args__ = (UniqueConstraint("source", "chunk_index", name="uq_knowledge_chunk_source_index"),)

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(255), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    # JSON list[float] rather than a pgvector column — keeps the same schema working on
    # SQLite (tests/local dev) and Postgres (prod) with no extension dependency. Retrieval
    # does cosine similarity in Python, which is fine at the scale a hand-curated business
    # knowledge base reaches; revisit with pgvector only if that stops being true.
    embedding: Mapped[list[float]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
