"""Kiểm tra nhóm endpoint theo hợp đồng UI (``UI/src/API_List.md``)."""

from __future__ import annotations

from fastapi.testclient import TestClient

SAMPLE_SIZE = 30


# --------------------------------------------------------------------------
# /health
# --------------------------------------------------------------------------
def test_health_root(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["dictionary_size"] == SAMPLE_SIZE


def test_health_matches_api_v1(client: TestClient) -> None:
    root = client.get("/health").json()
    versioned = client.get("/api/v1/health").json()

    assert root["status"] == versioned["status"]
    assert root["version"] == versioned["version"]
    assert root["dictionary_size"] == versioned["dictionary_size"]


# --------------------------------------------------------------------------
# /dictionary
# --------------------------------------------------------------------------
def test_dictionary_default_page(client: TestClient) -> None:
    response = client.get("/dictionary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == SAMPLE_SIZE
    assert payload["pages"] == 1
    assert payload["count"] == SAMPLE_SIZE
    assert payload["items"][0]["keyword"] == payload["items"][0]["keyword"].lower()
    keywords = [item["keyword"] for item in payload["items"]]
    assert keywords == sorted(keywords)


def test_dictionary_pagination(client: TestClient) -> None:
    first = client.get("/dictionary", params={"page": 1, "page_size": 10}).json()
    last = client.get("/dictionary", params={"page": 3, "page_size": 10}).json()
    empty = client.get("/dictionary", params={"page": 4, "page_size": 10}).json()

    assert first["pages"] == 3
    assert first["count"] == 10
    assert last["count"] == 10
    assert empty["count"] == 0
    assert empty["total"] == SAMPLE_SIZE
    keywords = [item["keyword"] for item in first["items"]]
    assert keywords == sorted(keywords)
    assert set(keywords).isdisjoint(item["keyword"] for item in last["items"])


def test_dictionary_filter_by_substring(client: TestClient) -> None:
    payload = client.get("/dictionary", params={"q": "samsung"}).json()

    assert payload["total"] == 5
    assert all("samsung" in item["keyword"] for item in payload["items"])


def test_dictionary_filter_by_length(client: TestClient) -> None:
    payload = client.get("/dictionary", params={"length": 11}).json()

    assert payload["total"] >= 1
    assert all(item["length"] == 11 for item in payload["items"])


def test_dictionary_sort_by_length(client: TestClient) -> None:
    payload = client.get("/dictionary", params={"sort": "length", "page_size": 30}).json()

    lengths = [item["length"] for item in payload["items"]]
    assert lengths == sorted(lengths)


def test_dictionary_rejects_blank_filter(client: TestClient) -> None:
    response = client.get("/dictionary", params={"q": "!!!"})

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


def test_dictionary_rejects_bad_pagination(client: TestClient) -> None:
    assert client.get("/dictionary", params={"page": 0}).status_code == 422
    assert client.get("/dictionary", params={"page_size": 0}).status_code == 422
    assert client.get("/dictionary", params={"page_size": 500}).status_code == 422
    assert client.get("/dictionary", params={"length": 0}).status_code == 422


def test_dictionary_stats(client: TestClient) -> None:
    response = client.get("/dictionary/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["dictionary"]["size"] == SAMPLE_SIZE
    assert payload["algorithm"]["name"] == "Levenshtein"
    assert "cache" in payload


# --------------------------------------------------------------------------
# /search và /search/suggest
# --------------------------------------------------------------------------
def test_search_contains(client: TestClient) -> None:
    payload = client.get("/search", params={"q": "tai nghe"}).json()

    assert payload["total"] == 6
    assert payload["count"] == 6
    assert payload["mode"] == "contains"
    assert payload["items"][0]["match_index"] == 0
    assert all("tai nghe" in item["keyword"] for item in payload["items"])


def test_search_prefix_mode(client: TestClient) -> None:
    prefixed = client.get("/search", params={"q": "tai nghe", "mode": "prefix"}).json()
    middle = client.get("/search", params={"q": "nghe", "mode": "prefix"}).json()
    anywhere = client.get("/search", params={"q": "nghe"}).json()

    assert prefixed["total"] == 6
    assert middle["total"] == 0
    assert anywhere["total"] == 6


def test_search_limit_and_total(client: TestClient) -> None:
    payload = client.get("/search", params={"q": "điện thoại", "limit": 3}).json()

    assert payload["total"] == 9
    assert payload["count"] == 3
    assert all(item["match_index"] == 0 for item in payload["items"])


def test_search_validation(client: TestClient) -> None:
    assert client.get("/search", params={"q": "!!!"}).status_code == 422
    assert client.get("/search", params={"q": ""}).status_code == 422
    assert client.get("/search", params={"q": "tai", "limit": 0}).status_code == 422
    assert client.get("/search", params={"q": "tai", "limit": 1000}).status_code == 422
    assert client.get("/search", params={"q": "tai", "mode": "fuzzy"}).status_code == 422


def test_search_suggest_matches_api_v1(client: TestClient) -> None:
    contract = client.get("/search/suggest", params={"q": "điện thoại samsng", "limit": 3})
    versioned = client.get("/api/v1/suggest", params={"q": "điện thoại samsng", "limit": 3})

    assert contract.status_code == 200
    contract_payload = contract.json()
    versioned_payload = versioned.json()

    # Bỏ qua took_ms/cached vì lần gọi thứ hai chắc chắn trúng bộ đệm.
    for field in ("query", "normalized_query", "suggestions", "count", "limit", "max_distance"):
        assert contract_payload[field] == versioned_payload[field]


def test_search_suggest_max_distance(client: TestClient) -> None:
    payload = client.get(
        "/search/suggest", params={"q": "điện thoại samsng", "max_distance": 1}
    ).json()

    assert payload["max_distance"] == 1
    assert all(item["distance"] <= 1 for item in payload["suggestions"])


def test_search_suggest_validation(client: TestClient) -> None:
    assert client.get("/search/suggest", params={"q": "!!!"}).status_code == 422
    assert client.get("/search/suggest").status_code == 422


# --------------------------------------------------------------------------
# /algorithm
# --------------------------------------------------------------------------
def test_algorithm_distance_basic(client: TestClient) -> None:
    payload = client.get(
        "/algorithm/distance", params={"source": "kitten", "target": "sitting"}
    ).json()

    assert payload["distance"] == 3
    assert payload["raw_distance"] == 3
    assert payload["normalized_source"] == "kitten"
    assert payload["source_length"] == 6


def test_algorithm_distance_uses_normalization(client: TestClient) -> None:
    payload = client.get(
        "/algorithm/distance", params={"source": "Áo Thun Akko", "target": "áo thun akko"}
    ).json()

    assert payload["distance"] == 0
    assert payload["raw_distance"] == 3
    assert payload["normalized_source"] == payload["normalized_target"]


def test_algorithm_distance_can_skip_normalization(client: TestClient) -> None:
    payload = client.get(
        "/algorithm/distance",
        params={"source": "Áo Thun Akko", "target": "áo thun akko", "normalize": False},
    ).json()

    assert payload["distance"] == 3
    assert payload["normalized_source"] == "Áo Thun Akko"


def test_algorithm_distance_validation(client: TestClient) -> None:
    assert client.get("/algorithm/distance", params={"target": "abc"}).status_code == 422
    assert (
        client.get("/algorithm/distance", params={"source": "!!!", "target": "abc"}).status_code
        == 422
    )
    assert (
        client.get("/algorithm/distance", params={"source": "a" * 300, "target": "abc"}).status_code
        == 422
    )


def test_algorithm_visualize_matrix(client: TestClient) -> None:
    response = client.post("/algorithm/visualize", json={"source": "kitten", "target": "sitting"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["distance"] == 3
    assert payload["rows"] == 7
    assert payload["columns"] == 8
    assert payload["row_labels"] == ["", "k", "i", "t", "t", "e", "n"]
    assert payload["column_labels"] == ["", "s", "i", "t", "t", "i", "n", "g"]
    assert payload["matrix"][1] == [1, 1, 2, 3, 4, 5, 6, 7]
    assert len(payload["path"]) == 7
    operations = [step["operation"] for step in payload["path"]]
    assert operations.count("substitute") == 2
    assert operations.count("insert") == 1
    assert sum(step["value"] for step in payload["path"]) == 3


def test_algorithm_visualize_vietnamese(client: TestClient) -> None:
    payload = client.post(
        "/algorithm/visualize",
        json={"source": "điện thoại samsng", "target": "điện thoại samsung"},
    ).json()

    assert payload["distance"] == 1
    assert payload["rows"] == len("điện thoại samsng") + 1
    assert payload["columns"] == len("điện thoại samsung") + 1


def test_algorithm_visualize_normalization(client: TestClient) -> None:
    normalized = client.post(
        "/algorithm/visualize", json={"source": "Áo-Thun", "target": "áo thun"}
    ).json()
    raw = client.post(
        "/algorithm/visualize",
        json={"source": "Áo-Thun", "target": "áo thun", "normalize": False},
    ).json()

    assert normalized["distance"] == 1  # "áothun" vs "áo thun"
    assert raw["distance"] == 3


def test_algorithm_visualize_validation(client: TestClient) -> None:
    assert (
        client.post("/algorithm/visualize", json={"source": "", "target": "abc"}).status_code == 422
    )
    assert (
        client.post("/algorithm/visualize", json={"source": "a" * 61, "target": "abc"}).status_code
        == 422
    )
    assert client.post("/algorithm/visualize", json={"target": "abc"}).status_code == 422
    assert (
        client.post("/algorithm/visualize", json={"source": "!!!", "target": "abc"}).status_code
        == 422
    )


# --------------------------------------------------------------------------
# /benchmark
# --------------------------------------------------------------------------
def test_benchmark_default_run(client: TestClient) -> None:
    response = client.post("/benchmark/runs", json={})

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["query_count"] == 5
    assert len(payload["results"]) == 5
    assert payload["summary"]["query_count"] == 5
    assert payload["summary"]["min_ms"] <= payload["summary"]["mean_ms"]
    assert all(result["suggestions"] for result in payload["results"])
    assert "T" in payload["created_at"]


def test_benchmark_with_queries_and_baseline(client: TestClient) -> None:
    response = client.post(
        "/benchmark/runs",
        json={
            "queries": ["tai nghe blutooth", "áo thun akko"],
            "limit": 3,
            "repeats": 2,
            "include_baseline": True,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["repeats"] == 2
    assert payload["include_baseline"] is True
    assert payload["summary"]["baseline_mismatches"] == 0
    assert payload["summary"]["speedup_vs_baseline"] is not None
    assert all(item["baseline_ms"] is not None for item in payload["results"])
    assert all(item["matches_baseline"] is True for item in payload["results"])


def test_benchmark_run_can_be_fetched(client: TestClient) -> None:
    created = client.post("/benchmark/runs", json={"queries": ["áo thun akko"]}).json()

    fetched = client.get(f"/benchmark/runs/{created['run_id']}")

    assert fetched.status_code == 200
    assert fetched.json()["run_id"] == created["run_id"]
    assert fetched.json()["results"] == created["results"]


def test_benchmark_run_not_found(client: TestClient) -> None:
    response = client.get("/benchmark/runs/khong-ton-tai")

    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_benchmark_export_csv(client: TestClient) -> None:
    created = client.post(
        "/benchmark/runs", json={"queries": ["tai nghe blutooth", "áo thun akko"], "limit": 3}
    ).json()

    response = client.get(f"/benchmark/runs/{created['run_id']}/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert created["run_id"] in response.headers["content-disposition"]
    assert response.content.startswith(b"\xef\xbb\xbf")

    lines = response.text.lstrip("\ufeff").strip().splitlines()
    expected_rows = 1 + sum(len(result["suggestions"]) for result in created["results"])
    assert len(lines) == expected_rows
    assert lines[0].startswith("run_id,query,rank,keyword,distance")


def test_benchmark_export_not_found(client: TestClient) -> None:
    assert client.get("/benchmark/runs/thieu/export").status_code == 404


def test_benchmark_validation(client: TestClient) -> None:
    assert client.post("/benchmark/runs", json={"queries": []}).status_code == 422
    assert client.post("/benchmark/runs", json={"queries": ["!!!"]}).status_code == 422
    assert client.post("/benchmark/runs", json={"limit": 0}).status_code == 422
    assert client.post("/benchmark/runs", json={"repeats": 0}).status_code == 422
    assert client.post("/benchmark/runs", json={"queries": ["a" * 300]}).status_code == 422


def test_api_index_lists_contract_endpoints(client: TestClient) -> None:
    payload = client.get("/api/v1").json()

    assert "POST /api/v1/suggest" in payload["endpoints"]
    assert "POST /benchmark/runs" in payload["contract_endpoints"]
    assert "GET /algorithm/visualize" not in payload["contract_endpoints"]
    assert "POST /algorithm/visualize" in payload["contract_endpoints"]
