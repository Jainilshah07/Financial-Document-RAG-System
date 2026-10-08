import structlog
from fastapi.testclient import TestClient

from app.main import create_app


def build_client() -> TestClient:
    app = create_app()

    @app.get("/_trace")
    def trace() -> dict[str, str]:
        # What a log line emitted inside a route would carry.
        return {"trace_id": structlog.contextvars.get_contextvars()["trace_id"]}

    return TestClient(app)


def test_response_has_generated_trace_id() -> None:
    response = build_client().get("/health")

    assert len(response.headers["X-Trace-Id"]) == 32


def test_incoming_trace_id_is_reused() -> None:
    response = build_client().get("/health", headers={"X-Trace-Id": "abc123"})

    assert response.headers["X-Trace-Id"] == "abc123"


def test_trace_id_is_available_to_route_code() -> None:
    response = build_client().get("/_trace")

    assert response.json()["trace_id"] == response.headers["X-Trace-Id"]
