"""Pydantic schema cho request/response của API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .core.text import normalize_text

MAX_QUERY_LENGTH = 200
MAX_LIMIT = 20
MAX_ALLOWED_DISTANCE = 100


class SuggestionItem(BaseModel):
    """Một từ khóa gợi ý."""

    keyword: str = Field(
        ..., description="Từ khóa gợi ý (đã chuẩn hóa).", examples=["điện thoại samsung"]
    )
    distance: int = Field(..., ge=0, description="Số phép chỉnh sửa so với truy vấn.", examples=[1])


class SuggestRequest(BaseModel):
    """Body của ``POST /api/v1/suggest``."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"query": "điện thoại samsng", "limit": 5},
                {"query": "tai nghe blutooth", "limit": 10, "max_distance": 4},
            ]
        }
    )

    query: str = Field(
        ...,
        min_length=1,
        max_length=MAX_QUERY_LENGTH,
        description="Từ khóa người dùng nhập, giữ nguyên dấu tiếng Việt.",
        examples=["điện thoại samsng"],
    )
    limit: int = Field(5, ge=1, le=MAX_LIMIT, description="Số gợi ý tối đa.")
    max_distance: int | None = Field(
        None,
        ge=0,
        le=MAX_ALLOWED_DISTANCE,
        description="Nếu có, chỉ trả về gợi ý có khoảng cách <= giá trị này.",
    )

    @field_validator("query")
    @classmethod
    def _require_meaningful_query(cls, value: str) -> str:
        if not normalize_text(value):
            raise ValueError("Truy vấn không được rỗng hoặc chỉ gồm ký tự đặc biệt.")
        return value


class SuggestResponse(BaseModel):
    """Kết quả gợi ý kèm vài số liệu đo để tiện demo và làm báo cáo."""

    query: str = Field(..., description="Truy vấn gốc người dùng gửi lên.")
    normalized_query: str = Field(
        ..., description="Truy vấn sau khi chuẩn hóa (NFC, chữ thường, bỏ dấu câu)."
    )
    suggestions: list[SuggestionItem]
    count: int = Field(..., ge=0, description="Số gợi ý trả về.")
    limit: int = Field(..., ge=1)
    max_distance: int | None = None
    took_ms: float = Field(..., ge=0, description="Thời gian xử lý phía server (mili giây).")
    cached: bool = Field(..., description="Kết quả lấy từ bộ đệm LRU hay tính mới.")
    evaluated_candidates: int = Field(
        ...,
        ge=0,
        description="Số từ khóa đã tính khoảng cách; cho thấy mức độ hiệu quả của bộ lọc.",
    )


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    version: str
    dictionary_size: int = Field(..., ge=0)
    uptime_seconds: float = Field(..., ge=0)


MAX_VISUALIZE_LENGTH = 60
MAX_PAGE_SIZE = 200
MAX_SEARCH_LIMIT = 100
MAX_BENCHMARK_QUERIES = 25


class DistanceResponse(BaseModel):
    """Kết quả ``GET /algorithm/distance``."""

    source: str = Field(..., description="Chuỗi gốc thứ nhất (người dùng gửi).")
    target: str = Field(..., description="Chuỗi gốc thứ hai (người dùng gửi).")
    normalized_source: str = Field(..., description="Chuỗi thứ nhất sau chuẩn hóa.")
    normalized_target: str = Field(..., description="Chuỗi thứ hai sau chuẩn hóa.")
    distance: int = Field(..., ge=0, description="Khoảng cách trên hai chuỗi đã chuẩn hóa.")
    raw_distance: int = Field(..., ge=0, description="Khoảng cách trên hai chuỗi nguyên bản.")
    source_length: int = Field(..., ge=0)
    target_length: int = Field(..., ge=0)


class VisualizeRequest(BaseModel):
    """Body của ``POST /algorithm/visualize``."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"source": "kitten", "target": "sitting"}]}
    )

    source: str = Field(
        ...,
        min_length=1,
        max_length=MAX_VISUALIZE_LENGTH,
        description="Chuỗi nguồn (hàng của bảng quy hoạch động).",
        examples=["kitten"],
    )
    target: str = Field(
        ...,
        min_length=1,
        max_length=MAX_VISUALIZE_LENGTH,
        description="Chuỗi đích (cột của bảng quy hoạch động).",
        examples=["sitting"],
    )
    normalize: bool = Field(
        True,
        description="Chuẩn hóa tiếng Việt trước khi tính, giống hành vi của bộ gợi ý.",
    )


class EditStepModel(BaseModel):
    """Một bước trên đường đi tối ưu."""

    row: int = Field(..., ge=0)
    column: int = Field(..., ge=0)
    operation: str = Field(..., examples=["substitute"])
    source_char: str = ""
    target_char: str = ""
    value: int = Field(..., ge=0)


class VisualizeResponse(BaseModel):
    """Bảng quy hoạch động đầy đủ kèm đường đi tối ưu."""

    source: str
    target: str
    normalized_source: str
    normalized_target: str
    distance: int = Field(..., ge=0)
    rows: int = Field(..., ge=1, description="Số hàng của bảng = len(source) + 1.")
    columns: int = Field(..., ge=1, description="Số cột của bảng = len(target) + 1.")
    matrix: list[list[int]] = Field(..., description="Bảng D[i][j], hàng 0 và cột 0 là mốc.")
    row_labels: list[str] = Field(..., description='Nhãn hàng: ["", *source].')
    column_labels: list[str] = Field(..., description='Nhãn cột: ["", *target].')
    path: list[EditStepModel] = Field(..., description="Đường đi tối ưu, thứ tự từ đầu tới cuối.")


class DictionaryEntry(BaseModel):
    """Một từ khóa trong danh sách từ điển."""

    keyword: str
    length: int = Field(..., ge=1)


class DictionaryPage(BaseModel):
    """Một trang của ``GET /dictionary``."""

    total: int = Field(..., ge=0, description="Tổng số từ khóa khớp bộ lọc.")
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)
    pages: int = Field(..., ge=0, description="Tổng số trang, 0 nếu không có kết quả.")
    count: int = Field(..., ge=0, description="Số từ khóa trong trang này.")
    items: list[DictionaryEntry]


class SearchHit(BaseModel):
    """Một từ khóa khớp trong ``GET /search``."""

    keyword: str
    length: int = Field(..., ge=1)
    match_index: int = Field(..., ge=0, description="Vị trí chuỗi con khớp trong từ khóa.")


class SearchResponse(BaseModel):
    """Kết quả ``GET /search``."""

    query: str
    normalized_query: str
    mode: str = Field(..., description="contains hoặc prefix.")
    total: int = Field(..., ge=0, description="Tổng số từ khóa khớp (không chỉ trong trang).")
    count: int = Field(..., ge=0)
    items: list[SearchHit]


class BenchmarkRequest(BaseModel):
    """Body của ``POST /benchmark/runs``."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"queries": ["điện thoại samsng", "tai nghe blutooth"], "limit": 5},
                {"include_baseline": True, "repeats": 2},
            ]
        }
    )

    queries: list[str] | None = Field(
        None,
        max_length=MAX_BENCHMARK_QUERIES,
        description="Danh sách truy vấn; bỏ trống thì dùng 5 truy vấn mẫu của báo cáo.",
    )
    limit: int = Field(5, ge=1, le=MAX_LIMIT, description="Số gợi ý lấy mỗi truy vấn.")
    repeats: int = Field(
        1, ge=1, le=10, description="Số lần chạy mỗi truy vấn; lấy lần nhanh nhất."
    )
    include_baseline: bool = Field(
        False,
        description=(
            "Đo thêm mốc quét toàn bộ từ điển (giống algorithm.py) để tính tốc độ "
            "tăng. Mỗi truy vấn tốn thêm ~0,6 giây với từ điển đầy đủ."
        ),
    )

    @field_validator("queries")
    @classmethod
    def _validate_queries(cls, value: list[str] | None) -> list[str] | None:
        if value is None:  # pragma: no cover - Pydantic bỏ qua validator khi thiếu trường
            return None
        cleaned = []
        for item in value:
            if not isinstance(item, str) or not normalize_text(item):
                raise ValueError("Mỗi truy vấn phải là chuỗi có ký tự chữ hoặc số.")
            if len(item) > MAX_QUERY_LENGTH:
                raise ValueError(f"Truy vấn không được dài quá {MAX_QUERY_LENGTH} ký tự.")
            cleaned.append(item)
        if not cleaned:
            raise ValueError("Danh sách truy vấn không được rỗng.")
        return cleaned


class BenchmarkQueryResult(BaseModel):
    """Kết quả đo của một truy vấn."""

    query: str
    normalized_query: str
    took_ms: float = Field(..., ge=0)
    candidates: int = Field(..., ge=0)
    suggestions: list[SuggestionItem]
    baseline_ms: float | None = None
    matches_baseline: bool | None = Field(
        None, description="Top-k của bộ lọc có trùng với bản quét toàn bộ hay không."
    )


class BenchmarkRunResponse(BaseModel):
    """Kết quả một lần chạy benchmark."""

    run_id: str
    status: str = Field(..., examples=["completed"])
    created_at: str = Field(..., description="Thời điểm chạy (ISO 8601, giờ máy chủ).")
    duration_ms: float = Field(..., ge=0, description="Tổng thời gian chạy cả lần đo.")
    limit: int = Field(..., ge=1)
    repeats: int = Field(..., ge=1)
    include_baseline: bool
    query_count: int = Field(..., ge=0)
    summary: dict[str, float | int | None]
    results: list[BenchmarkQueryResult]
