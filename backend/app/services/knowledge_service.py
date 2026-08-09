import logging
import math

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_chunk import KnowledgeChunk
from app.providers.base import AIProvider, ChatMessage
from app.providers.exceptions import ProviderAuthError, ProviderRateLimitError, ProviderTimeoutError, ProviderUnavailableError

logger = logging.getLogger("ase_ai.knowledge")

CHUNK_SIZE_CHARS = 1200
CHUNK_OVERLAP_CHARS = 150
RETRIEVAL_TOP_K = 5
MIN_SIMILARITY = 0.72


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    """Splits on paragraph boundaries where possible, packing paragraphs into ~chunk_size
    windows with a small trailing overlap so a fact split across a boundary is still findable
    from either neighboring chunk. Falls back to a hard character split for single paragraphs
    longer than chunk_size on their own.
    """
    paragraphs = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)
        if len(paragraph) <= chunk_size:
            current = paragraph
        else:
            for start in range(0, len(paragraph), chunk_size - overlap):
                chunks.append(paragraph[start : start + chunk_size])
            current = ""

    if current:
        chunks.append(current)

    # Carry a small tail of each chunk into the next one's start, for continuity at boundaries.
    overlapped = []
    for i, chunk in enumerate(chunks):
        if i > 0 and overlap > 0:
            tail = chunks[i - 1][-overlap:]
            chunk = f"{tail}\n\n{chunk}"
        overlapped.append(chunk)
    return overlapped


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def ingest_document(db: AsyncSession, provider: AIProvider, source: str, text: str) -> int:
    """Chunks `text`, embeds each chunk, and stores it under `source`. Re-ingesting the same
    `source` replaces its previous chunks entirely, so updating a business document is just
    running ingestion again with the same filename. Returns the number of chunks stored.
    """
    chunks = chunk_text(text)
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source == source))

    for index, chunk in enumerate(chunks):
        embedding = await provider.embeddings(chunk)
        db.add(KnowledgeChunk(source=source, chunk_index=index, content=chunk, embedding=embedding))

    await db.commit()
    return len(chunks)


async def retrieve_relevant_chunks(
    db: AsyncSession, provider: AIProvider, query: str, top_k: int = RETRIEVAL_TOP_K, min_similarity: float = MIN_SIMILARITY
) -> list[KnowledgeChunk]:
    """Best-effort semantic search over the ingested business knowledge base. Returns []
    (never raises) on any embedding failure or when the knowledge base is empty, so a
    provider hiccup or an unpopulated KB never blocks a chat response — it just means that
    turn answers without extra business context, same as before RAG existed.
    """
    exists = await db.execute(select(KnowledgeChunk.id).limit(1))
    if exists.scalar_one_or_none() is None:
        return []

    try:
        query_embedding = await provider.embeddings(query)
    except (ProviderAuthError, ProviderRateLimitError, ProviderTimeoutError, ProviderUnavailableError) as exc:
        logger.warning("knowledge_retrieval_embedding_failed error=%s", exc)
        return []

    result = await db.execute(select(KnowledgeChunk))
    scored = [(cosine_similarity(query_embedding, c.embedding), c) for c in result.scalars().all()]
    scored = [pair for pair in scored if pair[0] >= min_similarity]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def build_context_system_message(chunks: list[KnowledgeChunk]) -> ChatMessage | None:
    if not chunks:
        return None
    body = "\n\n---\n\n".join(c.content for c in chunks)
    return ChatMessage(
        role="system",
        content=(
            "The following excerpts are from Allied Software Engineers' own business "
            "knowledge base and may be relevant to the user's question. Use them when "
            "relevant; if they don't answer the question, say so honestly instead of "
            f"guessing.\n\n{body}"
        ),
    )


async def augment_with_business_knowledge(db: AsyncSession, provider: AIProvider, context: list[ChatMessage]) -> None:
    """Mutates `context` in place, inserting a system message with relevant business-
    knowledge excerpts right after the main system prompt. The retrieval query is the most
    recent user message (the one about to be answered)."""
    last_user = next((m for m in reversed(context) if m.role == "user"), None)
    if last_user is None or not last_user.content.strip():
        return

    chunks = await retrieve_relevant_chunks(db, provider, last_user.content)
    knowledge_message = build_context_system_message(chunks)
    if knowledge_message is None:
        return

    insert_at = 1 if context and context[0].role == "system" else 0
    context.insert(insert_at, knowledge_message)
