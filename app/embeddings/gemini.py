import math
import random
import time
from collections import deque
from collections.abc import Sequence

import httpx
import structlog

from app.core.tokens import estimate_tokens
from app.embeddings.base import EmbeddingError

log = structlog.get_logger("embeddings.gemini")

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_BACKOFF_SECONDS = 60.0
WINDOW_SECONDS = 60.0


class GeminiEmbedder:
    """Gemini `gemini-embedding-001` over plain HTTPS (ADR-003).

    Why we manage the free tier ourselves:
      * limits are ~30k tokens/minute and ~1k requests/day, so texts are sent in batches
        (one request carries many chunks) and paced by a sliding token window;
      * 429/5xx responses are retried with exponential backoff (honouring Retry-After);
      * embeddings requested below the model's native size (768 < 3072) come back
        un-normalised, so we L2-normalise them (cosine similarity then equals dot product).
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-001",
        dimension: int = 768,
        *,
        batch_size: int = 50,
        tokens_per_minute: int = 25_000,
        max_retries: int = 5,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._dimension = dimension
        self._batch_size = batch_size
        self._tokens_per_minute = tokens_per_minute
        self._max_retries = max_retries
        self._client = client or httpx.Client(timeout=60.0)
        self._window: deque[tuple[float, int]] = deque()  # (sent_at, tokens)

    @property
    def model_id(self) -> str:
        return f"{self._model}:{self._dimension}"

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = list(texts[start : start + self._batch_size])
            vectors.extend(self._embed_batch(batch, "RETRIEVAL_DOCUMENT"))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed_batch([text], "RETRIEVAL_QUERY")[0]

    # --- internals ---------------------------------------------------------------

    def _embed_batch(self, texts: list[str], task_type: str) -> list[list[float]]:
        self._wait_for_token_budget(sum(estimate_tokens(t) for t in texts))
        payload = {
            "requests": [
                {
                    "model": f"models/{self._model}",
                    "content": {"parts": [{"text": text}]},
                    "taskType": task_type,
                    "outputDimensionality": self._dimension,
                }
                for text in texts
            ]
        }
        data = self._post(f"{BASE_URL}/models/{self._model}:batchEmbedContents", payload)
        embeddings = data.get("embeddings", [])
        if len(embeddings) != len(texts):
            raise EmbeddingError(f"Asked for {len(texts)} embeddings, received {len(embeddings)}.")
        vectors = [_l2_normalise(item["values"]) for item in embeddings]
        if any(len(v) != self._dimension for v in vectors):
            raise EmbeddingError(f"Provider returned vectors that are not {self._dimension}-d.")
        log.info("embedded", texts=len(texts), task_type=task_type, model=self.model_id)
        return vectors

    def _wait_for_token_budget(self, tokens: int) -> None:
        """Block until sending `tokens` more would stay under the per-minute limit."""
        while True:
            now = time.monotonic()
            while self._window and now - self._window[0][0] >= WINDOW_SECONDS:
                self._window.popleft()
            used = sum(t for _, t in self._window)
            if not self._window or used + tokens <= self._tokens_per_minute:
                self._window.append((now, tokens))
                return
            wait = WINDOW_SECONDS - (now - self._window[0][0])
            log.info("embedding_rate_wait", seconds=round(wait, 1), used=used, needed=tokens)
            time.sleep(max(wait, 0.1))

    def _post(self, url: str, payload: dict) -> dict:
        for attempt in range(self._max_retries + 1):
            last_attempt = attempt == self._max_retries
            try:
                response = self._client.post(
                    url, json=payload, headers={"x-goog-api-key": self._api_key}
                )
            except httpx.TransportError as exc:
                if last_attempt:
                    raise EmbeddingError(
                        f"Network error calling Gemini: {exc.__class__.__name__}"
                    ) from exc
                self._backoff(attempt, None)
                continue

            if response.status_code == 200:
                return response.json()
            if response.status_code in RETRYABLE_STATUS and not last_attempt:
                self._backoff(attempt, response.headers.get("retry-after"))
                continue
            hint = " (daily free quota may be exhausted)" if response.status_code == 429 else ""
            detail = response.text[:300]
            raise EmbeddingError(
                f"Gemini embeddings failed: HTTP {response.status_code}{hint}: {detail}"
            )
        raise EmbeddingError("unreachable")  # loop always returns or raises

    @staticmethod
    def _backoff(attempt: int, retry_after: str | None) -> None:
        try:
            delay = float(retry_after) if retry_after else None
        except ValueError:
            delay = None
        if delay is None:
            delay = min(2.0 ** (attempt + 1) + random.random(), MAX_BACKOFF_SECONDS)
        log.warning("embedding_retry", attempt=attempt + 1, sleep_seconds=round(delay, 1))
        time.sleep(delay)


def _l2_normalise(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    return vector if norm == 0 else [x / norm for x in vector]
