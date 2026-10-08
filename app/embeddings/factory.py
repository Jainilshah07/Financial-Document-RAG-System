from app.core.config import Settings
from app.embeddings.base import Embedder, EmbeddingError
from app.embeddings.gemini import GeminiEmbedder


def build_embedder(settings: Settings) -> Embedder:
    """Create the configured embedder. Gemini is the only provider so far; a new
    provider means one more class and one more branch here."""
    if settings.gemini_api_key is None:
        raise EmbeddingError("GEMINI_API_KEY is not set (add it to .env).")
    return GeminiEmbedder(
        api_key=settings.gemini_api_key.get_secret_value(),
        model=settings.embedding_model,
        dimension=settings.embedding_dim,
        batch_size=settings.embedding_batch_size,
        tokens_per_minute=settings.embedding_tokens_per_minute,
    )
