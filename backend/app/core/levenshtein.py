"""Khoảng cách chỉnh sửa Levenshtein theo quy hoạch động.

Module cung cấp hai hàm:

``levenshtein_distance``
    Bản quy hoạch động chuẩn như ``algorithm.py`` của repo: thời gian
    ``O(m*n)``, bộ nhớ ``O(min(m, n))``. Dùng làm chuẩn đối chiếu.

``bounded_levenshtein_distance``
    Bản tối ưu cho truy vấn thời gian thực: chỉ tính các ô nằm trong dải
    chéo cách đường chéo chính tối đa ``max_distance`` (thuật toán Ukkonen),
    dừng sớm khi mọi ô của một hàng đều lớn hơn ngưỡng. Thời gian
    ``O(m * max_distance)``. Kết quả trả về ``max_distance + 1`` khi khoảng
    cách thật lớn hơn ngưỡng, nhờ vậy bên gọi vẫn so sánh được mà không cần
    tính chính xác.

Cả hai hàm đều giữ nguyên thứ tự ký tự Unicode (không tách dấu tiếng Việt),
khớp với cách thuật toán gốc đang làm.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EditStep:
    """Một bước trên đường đi tối ưu của bảng quy hoạch động."""

    row: int
    column: int
    operation: str  # "match" | "substitute" | "insert" | "delete"
    source_char: str
    target_char: str
    value: int


def levenshtein_distance(source: str, target: str) -> int:
    """Số phép chèn/xóa/thay thế tối thiểu để biến ``source`` thành ``target``.

    Quy hoạch động hai hàng: ``D[i][j] = min(D[i-1][j] + 1,
    D[i][j-1] + 1, D[i-1][j-1] + (source[i-1] != target[j-1]))``.
    """
    if source == target:
        return 0
    if not source:
        return len(target)
    if not target:
        return len(source)

    # Dùng chuỗi ngắn hơn làm cột để tốn ít bộ nhớ hơn.
    if len(source) < len(target):
        source, target = target, source

    previous = list(range(len(target) + 1))
    for row, source_char in enumerate(source, start=1):
        current = [row]
        for column, target_char in enumerate(target, start=1):
            current.append(
                min(
                    current[column - 1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (source_char != target_char),
                )
            )
        previous = current
    return previous[-1]


def bounded_levenshtein_distance(source: str, target: str, max_distance: int) -> int:
    """Khoảng cách Levenshtein nếu ``<= max_distance``, ngược lại ``max_distance + 1``.

    Ý tưởng: nếu khoảng cách cuối cùng không vượt quá ``k = max_distance``
    thì trên mỗi hàng ``i`` chỉ những cột ``j`` thỏa ``|i - j| <= k`` mới có
    thể chứa giá trị ``<= k``. Ta bỏ hẳn phần ngoài dải, và nếu giá trị nhỏ
    nhất của cả hàng đã lớn hơn ``k`` thì chắc chắn không còn đường đi nào
    rẻ hơn, dừng ngay.
    """
    if max_distance < 0:
        raise ValueError("max_distance phải là số nguyên không âm")

    if source == target:
        return 0

    source_length, target_length = len(source), len(target)
    if abs(source_length - target_length) > max_distance:
        return max_distance + 1
    if not source:
        return min(target_length, max_distance + 1)
    if not target:
        return min(source_length, max_distance + 1)

    # Số hàng = độ dài chuỗi đóng vai trò "source"; chọn chuỗi ngắn hơn để
    # giảm số vòng lặp ngoài, dải vẫn giữ nguyên độ rộng.
    if source_length > target_length:
        source, target = target, source
        source_length, target_length = target_length, source_length

    limit = max_distance
    out_of_band = limit + 1

    # Hàng 0: D[0][j] = j, chỉ cần các cột 0..min(target_length, limit).
    previous_low = 0
    previous = list(range(min(target_length, limit) + 1))
    previous_high = len(previous) - 1

    for row in range(1, source_length + 1):
        low = max(0, row - limit)
        high = min(target_length, row + limit)
        current = [out_of_band] * (high - low + 1)
        row_minimum = out_of_band
        source_char = source[row - 1]

        for column in range(low, high + 1):
            if column == 0:
                value = row  # xóa toàn bộ row ký tự của source
            else:
                if previous_low <= column <= previous_high:
                    deletion = previous[column - previous_low] + 1
                else:
                    deletion = out_of_band

                if column - 1 >= low:
                    insertion = current[column - 1 - low] + 1
                else:
                    insertion = out_of_band

                if previous_low <= column - 1 <= previous_high:
                    substitution = previous[column - 1 - previous_low] + (
                        source_char != target[column - 1]
                    )
                else:  # pragma: no cover - |i-j| <= k nên ô chéo luôn trong dải
                    substitution = out_of_band

                value = min(insertion, deletion, substitution)

            current[column - low] = value
            if value < row_minimum:
                row_minimum = value

        if row_minimum > limit:
            return out_of_band

        previous, previous_low, previous_high = current, low, high

    if previous_low <= target_length <= previous_high:
        result = previous[target_length - previous_low]
    else:  # pragma: no cover - không xảy ra khi |m - n| <= limit
        result = out_of_band
    return result if result <= limit else out_of_band


def levenshtein_matrix(source: str, target: str) -> list[list[int]]:
    """Bảng quy hoạch động đầy đủ ``(len(source)+1) x (len(target)+1)``.

    Khác hai hàm trên (chỉ giữ hai hàng cho tiết kiệm bộ nhớ), bản này giữ
    toàn bộ bảng để phục vụ minh họa thuật toán và truy vết đường đi tối ưu.
    Chi phí ``O(m*n)`` bộ nhớ, chỉ dùng cho chuỗi ngắn.
    """
    rows = len(source) + 1
    columns = len(target) + 1
    matrix = [[0] * columns for _ in range(rows)]

    for column in range(columns):
        matrix[0][column] = column
    for row in range(1, rows):
        matrix[row][0] = row
        source_char = source[row - 1]
        previous_row = matrix[row - 1]
        current_row = matrix[row]
        for column in range(1, columns):
            substitution_cost = 0 if source_char == target[column - 1] else 1
            current_row[column] = min(
                previous_row[column] + 1,
                current_row[column - 1] + 1,
                previous_row[column - 1] + substitution_cost,
            )
    return matrix


def optimal_alignment(
    source: str,
    target: str,
    matrix: list[list[int]] | None = None,
) -> tuple[EditStep, ...]:
    """Truy vết một đường đi tối ưu từ góc dưới phải về góc trên trái.

    Khi nhiều đường đi cùng chi phí, ưu tiên theo thứ tự: chéo (giữ nguyên
    hoặc thay thế) → xóa → chèn. Kết quả trả về theo thứ tự xuôi từ đầu
    chuỗi tới cuối chuỗi để dễ hiển thị.
    """
    table = matrix if matrix is not None else levenshtein_matrix(source, target)
    row, column = len(source), len(target)
    steps: list[EditStep] = []

    while row > 0 or column > 0:
        if row > 0 and column > 0:
            source_char = source[row - 1]
            target_char = target[column - 1]
            cost = 0 if source_char == target_char else 1
            if table[row][column] == table[row - 1][column - 1] + cost:
                steps.append(
                    EditStep(
                        row=row,
                        column=column,
                        operation="match" if cost == 0 else "substitute",
                        source_char=source_char,
                        target_char=target_char,
                        value=cost,
                    )
                )
                row -= 1
                column -= 1
                continue

        if row > 0 and table[row][column] == table[row - 1][column] + 1:
            steps.append(
                EditStep(
                    row=row,
                    column=column,
                    operation="delete",
                    source_char=source[row - 1],
                    target_char="",
                    value=1,
                )
            )
            row -= 1
            continue

        steps.append(
            EditStep(
                row=row,
                column=column,
                operation="insert",
                source_char="",
                target_char=target[column - 1],
                value=1,
            )
        )
        column -= 1

    steps.reverse()
    return tuple(steps)
