import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make(**overrides) -> Settings:
    # _env_file=None: ignore any real .env so the test only sees what we pass in.
    return Settings(_env_file=None, **overrides)


def test_defaults_are_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")

    s = make()

    assert s.llm_provider == "groq"
    assert s.embedding_dim == 768
    assert s.qdrant_url is None


def test_env_var_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    monkeypatch.setenv("EMBEDDING_DIM", "1536")

    assert make().embedding_dim == 1536


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        make()


def test_invalid_provider_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    monkeypatch.setenv("LLM_PROVIDER", "not-a-provider")

    with pytest.raises(ValidationError):
        make()


def test_secrets_do_not_leak_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:hunter2@localhost/db")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_supersecret")

    text = repr(make())

    assert "hunter2" not in text
    assert "gsk_supersecret" not in text
