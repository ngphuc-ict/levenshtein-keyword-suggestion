"""Router duyệt từ điển: danh sách phân trang và thống kê."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request

from ..schemas import (
    MAX_PAGE_SIZE,
    DictionaryEntry,
    DictionaryPage,
)
from .common import require_meaningful_query
from .system import stats_payload

router = APIRouter(tags=["Từ điển"])


@router.get(
    "/dictionary",
    response_model=DictionaryPage,
    summary="Liệt kê từ khóa (phân trang, lọc)",
    description=(
        "Trả về danh sách từ khóa đã chuẩn hóa, sắp xếp theo bảng chữ cái "
        "(hoặc theo độ dài). Có thể lọc theo chuỗi con `q` và theo đúng độ "
        "dài `length`."
    ),
)
def list_dictionary(
    request: Request,
    q: Annotated[
        str | None,
        Query(
            max_length=200,
            description="Lọc từ khóa chứa chuỗi này (bỏ qua nếu không truyền).",
            examples=["samsung"],
        ),
    ] = None,
    length: Annotated[
        int | None,
        Query(ge=1, le=64, description="Chỉ lấy từ khóa có đúng độ dài này."),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Trang cần lấy, bắt đầu từ 1.")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=MAX_PAGE_SIZE, description="Số từ khóa mỗi trang.")
    ] = 50,
    sort: Annotated[
        Literal["alphabet", "length"],
        Query(description="alphabet: theo bảng chữ cái; length: theo độ dài rồi chữ cái."),
    ] = "alphabet",
) -> DictionaryPage:
    dictionary = request.app.state.dictionary

    keywords: list[str]
    if length is not None:
        keywords = list(dictionary.by_length.get(length, ()))
    else:
        keywords = list(dictionary.keywords)

    if q is not None:
        needle = require_meaningful_query(q)
        keywords = [keyword for keyword in keywords if needle in keyword]

    if sort == "length":
        keywords.sort(key=lambda keyword: (len(keyword), keyword))

    total = len(keywords)
    start = (page - 1) * page_size
    window = keywords[start : start + page_size]

    return DictionaryPage(
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
        count=len(window),
        items=[DictionaryEntry(keyword=keyword, length=len(keyword)) for keyword in window],
    )


@router.get(
    "/dictionary/stats",
    summary="Thống kê từ điển, thuật toán và bộ đệm",
    description="Tương đương `GET /api/v1/stats`, dùng cho trang thống kê của UI.",
)
def dictionary_stats(request: Request) -> dict:
    return stats_payload(request.app)
