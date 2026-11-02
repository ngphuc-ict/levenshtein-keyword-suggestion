"""Router benchmark: chạy đo hiệu năng, tra cứu kết quả và xuất CSV.

Kết quả được giữ trong bộ nhớ (20 lần chạy gần nhất) nên UI có thể tạo lần
chạy, xem lại chi tiết và tải CSV mà không cần cơ sở dữ liệu.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Response

from ..core.benchmark import (
    DEFAULT_QUERIES,
    BenchmarkRun,
    run_benchmark,
    run_to_csv,
)
from ..schemas import (
    BenchmarkQueryResult,
    BenchmarkRequest,
    BenchmarkRunResponse,
    SuggestionItem,
)

router = APIRouter(tags=["Benchmark"])


def _to_response(run: BenchmarkRun) -> BenchmarkRunResponse:
    """Chuyển bản ghi trong kho thành response Pydantic."""
    return BenchmarkRunResponse(
        run_id=run.run_id,
        status=run.status,
        created_at=datetime.fromtimestamp(run.created_at)
        .astimezone()
        .isoformat(timespec="seconds"),
        duration_ms=run.duration_ms,
        limit=run.limit,
        repeats=run.repeats,
        include_baseline=run.include_baseline,
        query_count=len(run.measurements),
        summary=run.summary,
        results=[
            BenchmarkQueryResult(
                query=measurement.query,
                normalized_query=measurement.normalized_query,
                took_ms=measurement.took_ms,
                candidates=measurement.candidates,
                suggestions=[
                    SuggestionItem(keyword=keyword, distance=distance)
                    for keyword, distance in measurement.suggestions
                ],
                baseline_ms=measurement.baseline_ms,
                matches_baseline=measurement.matches_baseline,
            )
            for measurement in run.measurements
        ],
    )


def _get_run_or_404(request: Request, run_id: str) -> BenchmarkRun:
    run = request.app.state.benchmark_store.get(run_id)
    if run is None:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy lần chạy benchmark '{run_id}'.",
        )
    return run


@router.post(
    "/benchmark/runs",
    response_model=BenchmarkRunResponse,
    status_code=201,
    summary="Chạy benchmark và lưu kết quả",
    description=(
        "Đo thời gian gợi ý cho từng truy vấn, tùy chọn so với mốc quét toàn "
        "bộ từ điển (`include_baseline`). Bỏ trống `queries` thì dùng 5 truy "
        "vấn mẫu trong báo cáo. Kết quả được lưu theo `run_id`."
    ),
)
def create_benchmark_run(payload: BenchmarkRequest, request: Request) -> BenchmarkRunResponse:
    run = run_benchmark(
        request.app.state.suggester,
        request.app.state.dictionary,
        payload.queries or list(DEFAULT_QUERIES),
        limit=payload.limit,
        repeats=payload.repeats,
        include_baseline=payload.include_baseline,
    )
    request.app.state.benchmark_store.add(run)
    return _to_response(run)


@router.get(
    "/benchmark/runs/{run_id}",
    response_model=BenchmarkRunResponse,
    summary="Xem lại kết quả một lần chạy",
)
def get_benchmark_run(run_id: str, request: Request) -> BenchmarkRunResponse:
    return _to_response(_get_run_or_404(request, run_id))


@router.get(
    "/benchmark/runs/{run_id}/export",
    summary="Xuất kết quả benchmark ra CSV",
    response_class=Response,
    responses={
        200: {
            "content": {"text/csv": {"schema": {"type": "string"}}},
            "description": "Tệp CSV, mỗi dòng một gợi ý của một truy vấn.",
        }
    },
)
def export_benchmark_run(run_id: str, request: Request) -> Response:
    run = _get_run_or_404(request, run_id)
    csv_text = run_to_csv(run)
    return Response(
        content="\ufeff" + csv_text,  # BOM để Excel nhận đúng UTF-8
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="benchmark-{run.run_id}.csv"',
            "X-Benchmark-Run-Id": run.run_id,
        },
    )
