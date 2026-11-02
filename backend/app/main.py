"""Điểm khởi động của backend gợi ý từ khóa.

Chạy từ thư mục ``backend``::

    uvicorn app.main:app --reload --no-access-log

Tài liệu tương tác: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import api_router, contract_router
from .config import Settings
from .core.benchmark import BenchmarkStore
from .core.dictionary import KeywordDictionary
from .core.suggester import KeywordSuggester

logger = logging.getLogger("app")

STATIC_DIR = Path(__file__).resolve().parent / "static"


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )
    # Thư viện HTTP tự log từng request ở mức INFO; hạ xuống để log của
    # dịch vụ không bị nhiễu.
    for noisy in ("httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Nạp từ điển đúng một lần khi khởi động và tái sử dụng cho mọi request."""
    settings: Settings = app.state.settings
    started = time.perf_counter()

    dictionary = KeywordDictionary.from_file(settings.dictionary_path)
    suggester = KeywordSuggester(dictionary, cache_size=settings.cache_size)

    app.state.dictionary = dictionary
    app.state.suggester = suggester
    app.state.benchmark_store = BenchmarkStore()
    app.state.started_at = time.time()

    logger.info(
        "Đã nạp %d từ khóa từ %s trong %.1f ms (cache tối đa %d mục)",
        dictionary.stats.size,
        dictionary.stats.source,
        (time.perf_counter() - started) * 1000,
        settings.cache_size,
    )
    try:
        yield
    finally:
        logger.info("Đã dừng dịch vụ gợi ý từ khóa.")


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    body: dict[str, object] = {"error": code, "message": message}
    if details:
        body["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Tạo ứng dụng; ``settings`` cho phép test truyền từ điển riêng."""
    settings = settings or Settings.from_env()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Levenshtein Keyword Suggestion API",
        description=(
            "Backend gợi ý từ khóa khi người dùng nhập sai chính tả, dùng "
            "khoảng cách Levenshtein và quy hoạch động. Từ điển mặc định có "
            "23.850 từ khóa tiếng Việt."
        ),
        version=settings.version,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "Gợi ý", "description": "Tìm từ khóa gần nhất với truy vấn."},
            {"name": "Tìm kiếm", "description": "Gợi ý mờ và tra cứu chuỗi con cho UI."},
            {"name": "Từ điển", "description": "Duyệt, lọc và thống kê từ điển."},
            {
                "name": "Thuật toán",
                "description": "Tính khoảng cách và minh họa bảng quy hoạch động.",
            },
            {"name": "Benchmark", "description": "Đo hiệu năng, xem lại và xuất kết quả CSV."},
            {"name": "Hệ thống", "description": "Kiểm tra sức khỏe và số liệu vận hành."},
        ],
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time-Ms"],
    )

    @app.middleware("http")
    async def log_request(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:  # pragma: no cover - nhánh lỗi bất ngờ
            logger.exception(
                "Lỗi không xử lý được [%s] %s %s", request_id, request.method, request.url.path
            )
            raise
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        logger.info(
            "%s %s -> %d (%.1f ms) [%s]",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error.get("loc", ()) if part != "body")
            message = str(error.get("msg", "")).removeprefix("Value error, ")
            details.append({"field": location or "body", "message": message})
        return _error_response(
            422,
            "validation_error",
            "Dữ liệu đầu vào không hợp lệ.",
            details,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return _error_response(404, "not_found", "Không tìm thấy tài nguyên.")
        if exc.status_code == 422:
            return _error_response(422, "validation_error", str(exc.detail))
        return _error_response(exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Lỗi máy chủ tại %s", request.url.path)
        return _error_response(
            500,
            "internal_error",
            "Máy chủ gặp lỗi không mong muốn, vui lòng thử lại sau.",
        )

    @app.get("/api/v1", include_in_schema=False)
    def api_index() -> dict[str, object]:
        return {
            "name": "Levenshtein Keyword Suggestion API",
            "version": settings.version,
            "docs": "/docs",
            "endpoints": [
                "POST /api/v1/suggest",
                "GET /api/v1/suggest?q=...",
                "GET /api/v1/health",
                "GET /api/v1/stats",
            ],
            "contract_endpoints": [
                "GET /health",
                "GET /search/suggest?q=...",
                "GET /search?q=...",
                "GET /dictionary?page=1&page_size=50",
                "GET /dictionary/stats",
                "GET /algorithm/distance?source=...&target=...",
                "POST /algorithm/visualize",
                "POST /benchmark/runs",
                "GET /benchmark/runs/{run_id}",
                "GET /benchmark/runs/{run_id}/export",
            ],
        }

    app.include_router(api_router, prefix="/api/v1")
    app.include_router(contract_router)

    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


app = create_app()
