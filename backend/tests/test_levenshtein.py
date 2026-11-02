"""Kiểm tra khoảng cách Levenshtein, gồm cả bản có chặn."""

from __future__ import annotations

import random

import pytest

from app.core.levenshtein import (
    bounded_levenshtein_distance,
    levenshtein_distance,
)

ALPHABET = "abcđeêghiklmnôơpqrstuưvxyáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọ "


def test_known_distances() -> None:
    assert levenshtein_distance("kitten", "sitting") == 3
    assert levenshtein_distance("", "abc") == 3
    assert levenshtein_distance("abc", "") == 3
    assert levenshtein_distance("áo", "áo") == 0
    assert levenshtein_distance("điện thoại samsng", "điện thoại samsung") == 1


def test_symmetry() -> None:
    rng = random.Random(2024)
    for _ in range(200):
        left = "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 12)))
        right = "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 12)))
        assert levenshtein_distance(left, right) == levenshtein_distance(right, left)


def test_bounded_matches_reference() -> None:
    rng = random.Random(99)
    for _ in range(500):
        source = "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 16)))
        target = "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 16)))
        exact = levenshtein_distance(source, target)
        for limit in (0, 1, 2, 3, exact, exact + 1, 40):
            expected = exact if exact <= limit else limit + 1
            assert bounded_levenshtein_distance(source, target, limit) == expected


def test_bounded_early_exit_on_length_gap() -> None:
    assert bounded_levenshtein_distance("a", "abcdefgh", 3) == 4
    assert bounded_levenshtein_distance("abcdefgh", "a", 0) == 1


def test_bounded_zero_only_exact_match() -> None:
    assert bounded_levenshtein_distance("samsung", "samsung", 0) == 0
    assert bounded_levenshtein_distance("samsung", "samsunh", 0) == 1


def test_bounded_rejects_negative_limit() -> None:
    with pytest.raises(ValueError):
        bounded_levenshtein_distance("a", "b", -1)


def test_bounded_is_not_worse_than_limit() -> None:
    assert bounded_levenshtein_distance("kitten", "sitting", 2) == 3
    assert bounded_levenshtein_distance("kitten", "sitting", 3) == 3
