from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass
class ImagePart:
    mime_type: str
    data_base64: str


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str
    images: list[ImagePart] | None = None


@dataclass
class ChatResult:
    content: str
    model: str
    provider: str


class AIProvider(ABC):
    """Common interface every AI backend implements, so providers can be swapped or added
    without touching the rest of the application. Phase 1 implements chat/stream_chat for
    text-only conversation; vision/document/embedding/transcription are wired up in later phases.
    """

    name: str

    @abstractmethod
    async def chat(self, messages: list[ChatMessage], model: str, **params: Any) -> ChatResult: ...

    @abstractmethod
    def stream_chat(self, messages: list[ChatMessage], model: str, **params: Any) -> AsyncIterator[str]: ...

    async def vision(self, *args: Any, **kwargs: Any) -> ChatResult:
        raise NotImplementedError(f"{self.name} does not implement vision() yet")

    async def analyze_document(self, *args: Any, **kwargs: Any) -> ChatResult:
        raise NotImplementedError(f"{self.name} does not implement analyze_document() yet")

    async def embeddings(self, *args: Any, **kwargs: Any) -> list[float]:
        raise NotImplementedError(f"{self.name} does not implement embeddings() yet")

    async def transcribe(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError(f"{self.name} does not implement transcribe() yet")

    @abstractmethod
    async def health_check(self) -> bool: ...

    @abstractmethod
    async def list_models(self) -> list[str]: ...
