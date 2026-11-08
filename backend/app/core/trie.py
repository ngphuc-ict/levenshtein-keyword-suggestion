"""Cây tiền tố (trie) chạy quy hoạch động chung cho các từ khóa cùng tiền tố.

Từ điển sản phẩm có rất nhiều từ khóa chung phần đầu ("điện thoại samsung
..."). Với mỗi nút của trie ta giữ một cột bảng DP ``col[i] = D(query[:i],
tiền tố của nút)``, nên phần tiền tố chung chỉ được tính *một lần* thay vì
một lần cho mỗi từ khóa.

Khoảng cách tiền tố của một từ khóa là ``min`` của ``col[m]`` dọc đường đi
từ gốc tới từ khóa đó. Giá trị nhỏ nhất của cột không bao giờ giảm khi đi
sâu hơn, nên khi ``min(col) > ngưỡng`` ta cắt cả nhánh: không từ khóa nào
bên dưới có thể cải thiện khoảng cách đã đạt. Kết quả là chính xác, không
phải gần đúng.
"""

from __future__ import annotations

from collections.abc import Sequence


class PrefixTrie:
    """Trie trên danh sách từ khóa (thường đã bỏ dấu), trả về id theo vị trí."""

    __slots__ = ("_children", "_ends", "_low", "_high", "_order")

    def __init__(self, words: Sequence[str]) -> None:
        # Sắp xếp để mỗi nút ứng với một đoạn liên tiếp [low, high) của _order.
        self._order: list[int] = sorted(range(len(words)), key=words.__getitem__)
        self._children: list[dict[str, int]] = [{}]
        self._ends: dict[int, list[int]] = {}
        self._low: list[int] = [0]
        self._high: list[int] = [len(words)]

        for position, word_id in enumerate(self._order):
            node = 0
            for char in words[word_id]:
                child = self._children[node].get(char)
                if child is None:
                    child = len(self._children)
                    self._children[node][char] = child
                    self._children.append({})
                    self._low.append(position)
                    self._high.append(position)
                node = child
                self._high[node] = position + 1
            self._ends.setdefault(node, []).append(word_id)

    @property
    def node_count(self) -> int:
        return len(self._children)

    def search(self, query: str, max_distance: int) -> dict[int, int]:
        """``{id: khoảng cách tiền tố}`` của mọi từ khóa có khoảng cách ``<= max_distance``."""
        length = len(query)
        found: dict[int, int] = {}
        children, ends, order = self._children, self._ends, self._order
        low, high = self._low, self._high

        # Gốc: tiền tố rỗng, D(query[:i], "") = i, khoảng cách tiền tố hiện tại = length.
        stack: list[tuple[int, list[int], int]] = [(0, list(range(length + 1)), length)]
        while stack:
            node, column, best = stack.pop()
            if best <= max_distance:
                for word_id in ends.get(node, ()):
                    found[word_id] = best
                if min(column) > max_distance:
                    # Cả nhánh còn lại giữ nguyên khoảng cách ``best``.
                    for word_id in order[low[node] : high[node]]:
                        found[word_id] = best
                    continue
            elif min(column) > max_distance:
                continue

            for char, child in children[node].items():
                new_column = [column[0] + 1]
                for index in range(1, length + 1):
                    new_column.append(
                        min(
                            new_column[index - 1] + 1,
                            column[index] + 1,
                            column[index - 1] + (query[index - 1] != char),
                        )
                    )
                stack.append((child, new_column, min(best, new_column[length])))
        return found
