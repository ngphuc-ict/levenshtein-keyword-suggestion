"""Hàm dùng chung cho các router gợi ý."""

from __future__ import annotations

from fastapi import HTTPException, Request

from ..core.text import normalize_text
from ..schemas import SuggestionItem, SuggestResponse


def build_suggest_response(
    request: Request,
    query: str,
    limit: int,
    max_distance: int | None,
) -> SuggestResponse:
    """Chạy bộ gợi ý và đóng gói kết quả thành ``SuggestResponse``.

    Dùng chung cho ``/api/v1/suggest`` và ``/search/suggest`` để hai đường
    dẫn luôn trả về cùng một cấu trúc.
    """
    suggester = request.app.state.suggester
    result = suggester.suggest(query, limit=limit, max_distance=max_distance)
    return SuggestResponse(
        query=result.query,
        normalized_query=result.normalized_query,
        suggestions=[
            SuggestionItem(keyword=item.keyword, distance=item.distance)
            for item in result.suggestions
        ],
        count=len(result.suggestions),
        limit=limit,
        max_distance=max_distance,
        took_ms=result.took_ms,
        cached=result.cached,
        evaluated_candidates=result.evaluated,
    )


def require_meaningful_query(value: str, field_name: str = "q") -> str:
    """Chuẩn hóa và bắt lỗi truy vấn rỗng/chỉ có ký tự đặc biệt.

    Trả về chuỗi đã chuẩn hóa để bên gọi dùng luôn, tránh chuẩn hóa hai lần.
    """
    normalized = normalize_text(value)
    if not normalized:
        raise HTTPException(
            status_code=422,
            detail=f"Tham số '{field_name}' không được rỗng hoặc chỉ gồm ký tự đặc biệt.",
        )
    return normalized
