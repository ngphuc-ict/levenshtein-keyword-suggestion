"""Router tìm kiếm: gợi ý khi gõ sai và tra cứu chuỗi con.

Hai đường dẫn phục vụ hai mục đích khác nhau:

``GET /search/suggest``
    Gợi ý *mờ* (fuzzy) theo khoảng cách Levenshtein — dùng cho ô nhập liệu.
``GET /search``
    Tìm *chính xác tương đối*: từ khóa có chứa (hoặc bắt đầu bằng) chuỗi
    người dùng nhập. Nhanh, không tính khoảng cách, phù hợp trang danh sách.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request

from ..schemas import (
    MAX_ALLOWED_DISTANCE,
    MAX_LIMIT,
    MAX_QUERY_LENGTH,
    MAX_SEARCH_LIMIT,
    SearchHit,
    SearchResponse,
    SuggestResponse,
)
from .common import build_suggest_response, require_meaningful_query

router = APIRouter(tags=["Tìm kiếm"])


@router.get(
    "/search/suggest",
    response_model=SuggestResponse,
    summary="Gợi ý từ khóa khi gõ sai chính tả",
    description=(
        "Tương đương `GET /api/v1/suggest`: trả về tối đa `limit` từ khóa gần "
        "nhất theo khoảng cách Levenshtein. Đây là đường dẫn mà UI gọi khi "
        "người dùng đang nhập."
    ),
)
def search_suggest(
    request: Request,
    q: Annotated[
        str,
        Query(
            min_length=1,
            max_length=MAX_QUERY_LENGTH,
            description="Từ khóa người dùng nhập.",
            examples=["điện thoại samsng"],
        ),
    ],
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT, description="Số gợi ý tối đa.")] = 5,
    max_distance: Annotated[
        int | None,
        Query(ge=0, le=MAX_ALLOWED_DISTANCE, description="Giới hạn khoảng cách tối đa."),
    ] = None,
) -> SuggestResponse:
    require_meaningful_query(q)
    return build_suggest_response(request, q, limit, max_distance)


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Tìm từ khóa chứa chuỗi (không tính khoảng cách)",
    description=(
        "Trả về danh sách từ khóa có chứa chuỗi truy vấn, ưu tiên khớp ở đầu "
        "từ khóa rồi tới từ khóa ngắn hơn. `total` là tổng số từ khóa khớp, "
        "`items` bị giới hạn bởi `limit`."
    ),
)
def search_keywords(
    request: Request,
    q: Annotated[
        str,
        Query(
            min_length=1,
            max_length=MAX_QUERY_LENGTH,
            description="Chuỗi cần tìm trong từ khóa.",
            examples=["tai nghe"],
        ),
    ],
    limit: Annotated[
        int, Query(ge=1, le=MAX_SEARCH_LIMIT, description="Số kết quả tối đa trả về.")
    ] = 20,
    mode: Annotated[
        Literal["contains", "prefix"],
        Query(description="contains: chứa ở bất kỳ đâu; prefix: chỉ khớp đầu từ khóa."),
    ] = "contains",
) -> SearchResponse:
    normalized = require_meaningful_query(q)
    dictionary = request.app.state.dictionary

    hits: list[tuple[int, int, str]] = []
    for keyword in dictionary.keywords:
        index = keyword.find(normalized)
        if index < 0:
            continue
        if mode == "prefix" and index != 0:
            continue
        hits.append((index, len(keyword), keyword))
    hits.sort()

    window = hits[:limit]
    return SearchResponse(
        query=q,
        normalized_query=normalized,
        mode=mode,
        total=len(hits),
        count=len(window),
        items=[
            SearchHit(keyword=keyword, length=length, match_index=index)
            for index, length, keyword in window
        ],
    )
