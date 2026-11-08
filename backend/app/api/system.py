"""Router hệ thống: kiểm tra sức khỏe và thống kê.

Hai endpoint được phục vụ ở cả hai tiền tố:

* ``/api/v1/health``, ``/api/v1/stats`` — hợp đồng gốc của backend.
* ``/health`` — đường dẫn gọn theo ``UI/src/API_List.md`` cho frontend.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, FastAPI, Request

from ..schemas import HealthResponse

router = APIRouter(tags=["Hệ thống"])
root_router = APIRouter(tags=["Hệ thống"])


def health_payload(app: FastAPI) -> HealthResponse:
    """Số liệu sức khỏe dịch vụ, dùng chung cho mọi đường dẫn."""
    return HealthResponse(
        status="ok",
        version=app.state.settings.version,
        dictionary_size=len(app.state.dictionary),
        uptime_seconds=round(time.time() - app.state.started_at, 1),
    )


def stats_payload(app: FastAPI) -> dict:
    """Thống kê từ điển, thuật toán và bộ đệm."""
    dictionary = app.state.dictionary
    stats_data = dictionary.stats
    return {
        "dictionary": {
            "size": stats_data.size,
            "min_length": stats_data.min_length,
            "max_length": stats_data.max_length,
            "average_length": stats_data.average_length,
            "distinct_lengths": stats_data.distinct_lengths,
            "source": stats_data.source,
            "load_ms": stats_data.load_ms,
        },
        "algorithm": {
            "name": "Levenshtein",
            "distance": "quy hoạch động, hai hàng, O(m*n)",
            "candidate_filter": "trie tiền tố, ngưỡng tăng dần, cắt nhánh",
            "bounded_distance": "khoảng cách tiền tố không dấu, cột DP dùng chung",
            "default_limit": 5,
            "max_limit": 20,
        },
        "cache": app.state.suggester.cache_stats(),
        "uptime_seconds": round(time.time() - app.state.started_at, 1),
    }


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Kiểm tra dịch vụ đã sẵn sàng",
)
def health(request: Request) -> HealthResponse:
    return health_payload(request.app)


@router.get(
    "/stats",
    summary="Thống kê từ điển, thuật toán và bộ đệm",
    description="Số liệu phục vụ báo cáo: kích thước từ điển, thời gian nạp, tỉ lệ cache hit.",
)
def stats(request: Request) -> dict:
    return stats_payload(request.app)


root_router.add_api_route(
    "/health",
    health,
    methods=["GET"],
    response_model=HealthResponse,
    summary="Kiểm tra dịch vụ (đường dẫn gốc cho UI)",
)
