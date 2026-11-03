"""Kiểm tra cây tiền tố: kết quả phải trùng với tính khoảng cách tiền tố từng từ."""

from __future__ import annotations

import random

from app.core.levenshtein import prefix_levenshtein_distance
from app.core.trie import PrefixTrie


def test_search_matches_brute_force() -> None:
    rng = random.Random(99)
    alphabet = "abcd "
    words = [
        "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 9))) for _ in range(150)
    ]
    trie = PrefixTrie(words)

    for _ in range(60):
        query = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 8)))
        for bound in (0, 1, 2, 4):
            expected = {
                index: prefix_levenshtein_distance(query, word)
                for index, word in enumerate(words)
                if prefix_levenshtein_distance(query, word) <= bound
            }
            assert trie.search(query, bound) == expected, (query, bound)


def test_node_count_shares_prefixes() -> None:
    trie = PrefixTrie(["abc", "abd", "abc"])
    assert trie.node_count == 5  # gốc, a, ab, abc, abd
