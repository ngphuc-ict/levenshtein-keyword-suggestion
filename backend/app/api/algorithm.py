"""Router minh họa thuật toán: khoảng cách và bảng quy hoạch động.

Phục vụ trang "Algorithm" của UI và phần minh họa trong báo cáo: cho phép
tính khoảng cách giữa hai chuỗi bất kỳ và xem toàn bộ bảng ``D[i][j]`` kèm
đường đi tối ưu (những ô nào tạo nên kết quả cuối cùng).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ..core.levenshtein import (
    levenshtein_distance,
    levenshtein_matrix,
    optimal_alignment,
)
from ..core.text import normalize_text
from ..schemas import (
    MAX_QUERY_LENGTH,
    MAX_VISUALIZE_LENGTH,
    DistanceResponse,
    EditStepModel,
    VisualizeRequest,
    VisualizeResponse,
)

router = APIRouter(tags=["Thuật toán"])


@router.get(
    "/algorithm/distance",
    response_model=DistanceResponse,
    summary="Tính khoảng cách chỉnh sửa giữa hai chuỗi",
    description=(
        "Trả về khoảng cách Levenshtein trên hai chuỗi đã chuẩn hóa (mặc định) "
        "và cả trên hai chuỗi nguyên bản (`raw_distance`), tiện đối chiếu khi "
        "làm báo cáo."
    ),
)
def algorithm_distance(
    source: Annotated[
        str,
        Query(min_length=1, max_length=MAX_QUERY_LENGTH, description="Chuỗi thứ nhất."),
    ],
    target: Annotated[
        str,
        Query(min_length=1, max_length=MAX_QUERY_LENGTH, description="Chuỗi thứ hai."),
    ],
    normalize: Annotated[
        bool, Query(description="Chuẩn hóa tiếng Việt trước khi tính khoảng cách.")
    ] = True,
) -> DistanceResponse:
    normalized_source = normalize_text(source) if normalize else source
    normalized_target = normalize_text(target) if normalize else target

    if not normalized_source or not normalized_target:
        raise HTTPException(
            status_code=422,
            detail="Hai chuỗi phải chứa ít nhất một ký tự chữ hoặc số.",
        )

    return DistanceResponse(
        source=source,
        target=target,
        normalized_source=normalized_source,
        normalized_target=normalized_target,
        distance=levenshtein_distance(normalized_source, normalized_target),
        raw_distance=levenshtein_distance(source, target),
        source_length=len(normalized_source),
        target_length=len(normalized_target),
    )


@router.post(
    "/algorithm/visualize",
    response_model=VisualizeResponse,
    summary="Dựng bảng quy hoạch động và đường đi tối ưu",
    description=(
        "Trả về toàn bộ bảng `D[i][j]` (kèm nhãn hàng/cột) và đường đi tối ưu "
        "gồm các bước match / substitute / insert / delete. Giới hạn mỗi chuỗi "
        f"{MAX_VISUALIZE_LENGTH} ký tự để bảng không quá lớn."
    ),
)
def algorithm_visualize(payload: VisualizeRequest) -> VisualizeResponse:
    source = normalize_text(payload.source) if payload.normalize else payload.source
    target = normalize_text(payload.target) if payload.normalize else payload.target

    if not source or not target:
        raise HTTPException(
            status_code=422,
            detail="Hai chuỗi phải chứa ít nhất một ký tự chữ hoặc số.",
        )
    matrix = levenshtein_matrix(source, target)
    path = optimal_alignment(source, target, matrix)

    return VisualizeResponse(
        source=payload.source,
        target=payload.target,
        normalized_source=source,
        normalized_target=target,
        distance=matrix[-1][-1],
        rows=len(matrix),
        columns=len(matrix[0]),
        matrix=matrix,
        row_labels=["", *source],
        column_labels=["", *target],
        path=[
            EditStepModel(
                row=step.row,
                column=step.column,
                operation=step.operation,
                source_char=step.source_char,
                target_char=step.target_char,
                value=step.value,
            )
            for step in path
        ],
    )
