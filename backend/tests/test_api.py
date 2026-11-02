"""Kiểm tra API HTTP end-to-end."""

from __future__ import annotations

import pytest


def test_health(client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["dictionary_size"] == 30
    assert payload["version"] == "1.0.0"


def test_suggest_post(client) -> None:
    response = client.post(
        "/api/v1/suggest",
        json={"query": "điện thoại samsng", "limit": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "điện thoại samsng"
    assert payload["normalized_query"] == "điện thoại samsng"
    assert payload["count"] == 5
    assert payload["cached"] is False
    assert payload["took_ms"] >= 0
    assert payload["evaluated_candidates"] > 0
    assert payload["suggestions"][0] == {"keyword": "điện thoại samsung", "distance": 1}


def test_suggest_get(client) -> None:
    response = client.get("/api/v1/suggest", params={"q": "tai nghe blutooth", "limit": 3})

    assert response.status_code == 200
    payload = response.json()
    assert payload["suggestions"][0]["keyword"] == "tai nghe bluetooth"
    assert payload["suggestions"][0]["distance"] == 1
    assert len(payload["suggestions"]) == 3


def test_suggest_respects_max_distance(client) -> None:
    response = client.post(
        "/api/v1/suggest",
        json={"query": "điện thoại samsng", "limit": 5, "max_distance": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["max_distance"] == 1


def test_cache_reports_hit(client) -> None:
    first = client.post("/api/v1/suggest", json={"query": "áo thun akko"}).json()
    second = client.post("/api/v1/suggest", json={"query": "áo thun akko"}).json()

    assert first["cached"] is False
    assert second["cached"] is True
    assert second["suggestions"] == first["suggestions"]


@pytest.mark.parametrize(
    "payload",
    [
        {"query": ""},
        {"query": "    "},
        {"query": "!!!"},
        {"query": "a" * 201},
        {"query": "điện thoại", "limit": 0},
        {"query": "điện thoại", "limit": 21},
        {"query": "điện thoại", "max_distance": -1},
        {"query": "điện thoại", "max_distance": 101},
        {},
    ],
)
def test_invalid_payloads(client, payload) -> None:
    response = client.post("/api/v1/suggest", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"
    assert body["details"]


def test_invalid_get_query(client) -> None:
    assert client.get("/api/v1/suggest", params={"q": ""}).status_code == 422
    assert client.get("/api/v1/suggest", params={"q": "!!!"}).status_code == 422
    assert client.get("/api/v1/suggest", params={"q": "abc", "limit": 0}).status_code == 422


def test_not_found_is_json(client) -> None:
    response = client.get("/api/v1/khong-ton-tai")

    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_stats_endpoint(client) -> None:
    response = client.get("/api/v1/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["dictionary"]["size"] == 30
    assert payload["algorithm"]["name"] == "Levenshtein"
    assert payload["cache"]["capacity"] == 32


def test_cors_headers(client) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})

    assert response.headers["access-control-allow-origin"] == "*"


def test_request_tracing_headers(client) -> None:
    response = client.get("/api/v1/health")

    assert len(response.headers["X-Request-ID"]) == 12
    assert float(response.headers["X-Process-Time-Ms"]) >= 0


def test_request_id_is_echoed(client) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "abc123"})

    assert response.headers["X-Request-ID"] == "abc123"


def test_demo_page_is_served(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Gợi ý từ khóa" in response.text


def test_api_index(client) -> None:
    response = client.get("/api/v1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["docs"] == "/docs"
    assert "POST /api/v1/suggest" in payload["endpoints"]


def test_unexpected_error_returns_json(settings, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from app.core.suggester import KeywordSuggester
    from app.main import create_app

    def boom(*args, **kwargs):
        raise RuntimeError("lỗi giả lập")

    monkeypatch.setattr(KeywordSuggester, "suggest", boom)
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post("/api/v1/suggest", json={"query": "điện thoại"})

    assert response.status_code == 500
    assert response.json()["error"] == "internal_error"


def test_method_not_allowed(client) -> None:
    response = client.put("/api/v1/suggest")

    assert response.status_code == 405
    assert response.json()["error"] == "http_error"
