"""Kiểm tra bảng quy hoạch động và truy vết đường đi tối ưu."""

from __future__ import annotations

import random

from app.core.levenshtein import (
    levenshtein_distance,
    levenshtein_matrix,
    optimal_alignment,
)

ALPHABET = "abcdeáàảãạăâđêôơư "


def _random_pair(rng: random.Random, max_length: int = 12) -> tuple[str, str]:
    return (
        "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, max_length))),
        "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, max_length))),
    )


def test_matrix_shape_and_corner() -> None:
    matrix = levenshtein_matrix("kitten", "sitting")

    assert len(matrix) == 7
    assert all(len(row) == 8 for row in matrix)
    assert matrix[0] == list(range(8))
    assert [row[0] for row in matrix] == list(range(7))
    assert matrix[-1][-1] == 3


def test_matrix_row_matches_known_values() -> None:
    matrix = levenshtein_matrix("kitten", "sitting")

    assert matrix[1] == [1, 1, 2, 3, 4, 5, 6, 7]
    assert matrix[5] == [5, 5, 4, 3, 2, 2, 3, 4]


def test_matrix_matches_distance_on_random_pairs() -> None:
    rng = random.Random(20261102)

    for _ in range(200):
        source, target = _random_pair(rng)
        matrix = levenshtein_matrix(source, target)
        assert matrix[-1][-1] == levenshtein_distance(source, target)


def test_empty_strings() -> None:
    assert levenshtein_matrix("", "") == [[0]]
    assert levenshtein_matrix("", "abc")[-1][-1] == 3
    assert levenshtein_matrix("abc", "")[-1][-1] == 3


def test_alignment_kitten_sitting() -> None:
    path = optimal_alignment("kitten", "sitting")

    assert [step.operation for step in path] == [
        "substitute",
        "match",
        "match",
        "match",
        "substitute",
        "match",
        "insert",
    ]
    assert sum(step.value for step in path) == 3


def test_alignment_reconstructs_target() -> None:
    rng = random.Random(7)

    for _ in range(200):
        source, target = _random_pair(rng)
        path = optimal_alignment(source, target)

        rebuilt = "".join(step.target_char for step in path if step.operation != "delete")
        deleted = sum(1 for step in path if step.operation == "delete")
        inserted = sum(1 for step in path if step.operation == "insert")

        assert rebuilt == target
        assert sum(step.value for step in path) == levenshtein_distance(source, target)
        assert len(source) - deleted + inserted == len(target)


def test_alignment_accepts_precomputed_matrix() -> None:
    matrix = levenshtein_matrix("áo thun", "ao thun")

    path = optimal_alignment("áo thun", "ao thun", matrix)

    assert sum(step.value for step in path) == matrix[-1][-1] == 1
    assert [step.operation for step in path].count("substitute") == 1
