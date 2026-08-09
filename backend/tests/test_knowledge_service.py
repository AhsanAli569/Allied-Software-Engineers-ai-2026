import pytest

from app.providers.base import AIProvider, ChatMessage
from app.providers.exceptions import ProviderAuthError
from app.services.knowledge_service import (
    augment_with_business_knowledge,
    chunk_text,
    cosine_similarity,
    ingest_document,
    retrieve_relevant_chunks,
)


class FakeEmbeddingProvider(AIProvider):
    """Deterministic stand-in for GeminiProvider: returns whatever vector was registered
    for the exact input text, so retrieval ranking is fully controlled by the test."""

    def __init__(self, vectors: dict[str, list[float]] | None = None, fail: bool = False):
        self.name = "fake"
        self._vectors = vectors or {}
        self._fail = fail

    async def chat(self, messages, model, **params):
        raise NotImplementedError

    def stream_chat(self, messages, model, **params):
        raise NotImplementedError

    async def health_check(self) -> bool:
        return True

    async def list_models(self) -> list[str]:
        return []

    async def embeddings(self, text: str, model: str = "fake-embed") -> list[float]:
        if self._fail:
            raise ProviderAuthError("no key configured")
        return self._vectors.get(text, [0.0, 0.0, 1.0])


def test_chunk_text_splits_on_paragraph_boundaries():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = chunk_text(text, chunk_size=1000, overlap=0)
    assert len(chunks) == 1
    assert "First paragraph." in chunks[0]
    assert "Third paragraph." in chunks[0]


def test_chunk_text_respects_chunk_size():
    paragraphs = [f"Paragraph number {i} with some filler text to add length." for i in range(20)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, chunk_size=200, overlap=20)
    assert len(chunks) > 1
    for chunk in chunks:
        # Overlap can push slightly over chunk_size; it should never balloon far past it.
        assert len(chunk) <= 200 + 20 + 5


def test_chunk_text_hard_splits_a_single_oversized_paragraph():
    huge_paragraph = "word " * 1000
    chunks = chunk_text(huge_paragraph, chunk_size=500, overlap=50)
    assert len(chunks) > 1


def test_chunk_text_empty_input_returns_no_chunks():
    assert chunk_text("   \n\n  ") == []


def test_cosine_similarity_identical_vectors_is_one():
    assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors_is_zero():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_similarity_handles_zero_vector():
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


@pytest.mark.asyncio
async def test_ingest_document_splits_long_content_into_multiple_chunks(db_session):
    provider = FakeEmbeddingProvider()
    # Each paragraph alone fits in a chunk, but the two together don't (default chunk_size
    # is 1200 chars) — packing should stop at the boundary and start a new chunk.
    paragraph_a = "Allied Software Engineers builds custom software solutions. " * 15
    paragraph_b = "We also offer ongoing consulting and long-term support. " * 15
    count = await ingest_document(db_session, provider, "about.txt", f"{paragraph_a}\n\n{paragraph_b}")
    assert count == 2


@pytest.mark.asyncio
async def test_ingest_document_reingesting_same_source_replaces_old_chunks(db_session):
    provider = FakeEmbeddingProvider()
    await ingest_document(db_session, provider, "about.txt", "Old content here.")
    count = await ingest_document(db_session, provider, "about.txt", "New content only.")
    assert count == 1

    chunks = await retrieve_relevant_chunks(
        db_session, FakeEmbeddingProvider(vectors={"query": [0.0, 0.0, 1.0]}), "query", min_similarity=-1.0
    )
    contents = {c.content for c in chunks}
    assert not any("Old content" in c for c in contents)
    assert any("New content only" in c for c in contents)


@pytest.mark.asyncio
async def test_retrieve_relevant_chunks_returns_empty_when_kb_is_empty(db_session):
    provider = FakeEmbeddingProvider()
    result = await retrieve_relevant_chunks(db_session, provider, "anything")
    assert result == []


@pytest.mark.asyncio
async def test_retrieve_relevant_chunks_ranks_by_similarity_and_applies_threshold(db_session):
    ingest_provider = FakeEmbeddingProvider(
        vectors={
            "Pricing starts at $500 per project.": [1.0, 0.0, 0.0],
            "We are located in downtown.": [0.0, 1.0, 0.0],
        }
    )
    await ingest_document(db_session, ingest_provider, "pricing.txt", "Pricing starts at $500 per project.")
    await ingest_document(db_session, ingest_provider, "location.txt", "We are located in downtown.")

    query_provider = FakeEmbeddingProvider(vectors={"how much does it cost?": [0.9, 0.1, 0.0]})
    results = await retrieve_relevant_chunks(db_session, query_provider, "how much does it cost?", min_similarity=0.5)

    assert len(results) == 1
    assert "Pricing" in results[0].content


@pytest.mark.asyncio
async def test_retrieve_relevant_chunks_fails_open_on_provider_error(db_session):
    ingest_provider = FakeEmbeddingProvider()
    await ingest_document(db_session, ingest_provider, "about.txt", "Some business info.")

    failing_provider = FakeEmbeddingProvider(fail=True)
    result = await retrieve_relevant_chunks(db_session, failing_provider, "anything")
    assert result == []


@pytest.mark.asyncio
async def test_augment_with_business_knowledge_inserts_system_message_after_main_prompt(db_session):
    ingest_provider = FakeEmbeddingProvider(vectors={"We offer 24/7 support.": [1.0, 0.0, 0.0]})
    await ingest_document(db_session, ingest_provider, "support.txt", "We offer 24/7 support.")

    query_provider = FakeEmbeddingProvider(vectors={"Do you offer support?": [1.0, 0.0, 0.0]})
    context = [
        ChatMessage(role="system", content="You are ASE AI."),
        ChatMessage(role="user", content="Do you offer support?"),
    ]
    await augment_with_business_knowledge(db_session, query_provider, context)

    assert len(context) == 3
    assert context[1].role == "system"
    assert "24/7 support" in context[1].content
    assert context[0].content == "You are ASE AI."
    assert context[2].content == "Do you offer support?"


@pytest.mark.asyncio
async def test_augment_with_business_knowledge_is_noop_when_nothing_relevant(db_session):
    context = [
        ChatMessage(role="system", content="You are ASE AI."),
        ChatMessage(role="user", content="Do you offer support?"),
    ]
    await augment_with_business_knowledge(db_session, FakeEmbeddingProvider(), context)
    assert len(context) == 2
