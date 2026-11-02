"""Router cho chức năng gợi ý từ khóa."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request

from ..schemas import (
    MAX_ALLOWED_DISTANCE,
    MAX_LIMIT,
    MAX_QUERY_LENGTH,
    SuggestRequest,
    SuggestResponse,
)
from .common import build_suggest_response, require_meaningful_query

router = APIRouter(tags=["Gợi ý"])


@router.post(
    "/suggest",
    response_model=SuggestResponse,
    summary="Gợi ý từ khóa (JSON body)",
    description=(
        "Nhận từ khóa người dùng nhập (có thể sai chính tả), trả về tối đa "
        "`limit` từ khóa gần nhất trong từ điển theo khoảng cách Levenshtein."
    ),
)
def suggest_post(payload: SuggestRequest, request: Request) -> SuggestResponse:
    return build_suggest_response(request, payload.query, payload.limit, payload.max_distance)


@router.get(
    "/suggest",
    response_model=SuggestResponse,
    summary="Gợi ý từ khóa (query string)",
    description="Biến thể GET của `/suggest`, tiện thử nhanh bằng trình duyệt hoặc curl.",
)
def suggest_get(
    request: Request,
    q: Annotated[
        str,
        Query(
            min_length=1,
            max_length=MAX_QUERY_LENGTH,
            description="Từ khóa cần gợi ý.",
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
