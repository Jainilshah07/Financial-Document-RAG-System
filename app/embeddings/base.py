from collections.abc import Sequence
from typing import Protocol


class EmbeddingError(RuntimeError):
    """The embedding provider failed (after retries) or returned something unusable."""


class Embedder(Protocol):
    """Anything that turns text into vectors. The rest of the app depends on this
    protocol, so switching provider (Gemini -> OpenAI -> a local model) is one new class."""

    @property
    def model_id(self) -> str:
        """Stable identifier stored with every vector (model + dimension)."""

    @property
    def dimension(self) -> int: ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed passages to be searched (chunks)."""

    def embed_query(self, text: str) -> list[float]:
        """Embed a user question. Some models embed queries differently from passages."""
