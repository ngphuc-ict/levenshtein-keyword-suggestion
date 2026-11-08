"""Kiểm tra bộ gợi ý: xếp hạng, giới hạn, bộ đệm và tính đúng đắn."""

from __future__ import annotations

import random

import pytest

from app.core.dictionary import KeywordDictionary
from app.core.levenshtein import levenshtein_distance, prefix_levenshtein_distance
from app.core.suggester import KeywordSuggester
from app.core.text import fold_accents, normalize_text, starts_a_word

SAMPLE_WORDS = [
    "điện thoại samsung",
    "điện thoại samsung chính hãng",
    "điện thoại samsung giá rẻ",
    "điện thoại samsung cũ",
    "điện thoại apple",
    "điện thoại xiaomi",
    "điện thoại oppo",
    "tai nghe bluetooth",
    "tai nghe bluetooth chống nước",
    "tai nghe có dây",
    "tai nghe không dây",
    "áo thun akko",
    "áo thun akko cũ",
    "bàn phím cơ",
    "bàn phím cơ gaming",
    "laptop dell",
    "laptop dell cũ",
    "laptop asus",
]


def naive_top(dictionary: KeywordDictionary, query: str, limit: int):
    normalized = normalize_text(query)
    folded_query = fold_accents(normalized)
    scored = sorted(
        (
            prefix_levenshtein_distance(folded_query, fold_accents(keyword)),
            not starts_a_word(folded_query, fold_accents(keyword)),
            prefix_levenshtein_distance(normalized, keyword),
            levenshtein_distance(normalized, keyword),
            keyword,
        )
        for keyword in dictionary.keywords
    )
    return [(item[0], item[-1]) for item in scored[:limit]]


@pytest.fixture()
def suggester() -> KeywordSuggester:
    return KeywordSuggester(KeywordDictionary(SAMPLE_WORDS), cache_size=8)


def test_basic_suggestion(suggester: KeywordSuggester) -> None:
    result = suggester.suggest("điện thoại samsng", limit=5)

    assert result.normalized_query == "điện thoại samsng"
    assert result.suggestions[0].keyword == "điện thoại samsung"
    assert result.suggestions[0].distance == 1
    assert len(result.suggestions) == 5
    assert result.cached is False


def test_matches_naive_ranking(suggester: KeywordSuggester) -> None:
    for query in [
        "điện thoại samsng",
        "tai nghe blutooth",
        "áo thun akko",
        "laptop dell i5",
        "bàn phím cơ",
        "điện thoại",
    ]:
        expected = naive_top(suggester.dictionary, query, 5)
        actual = [(item.distance, item.keyword) for item in suggester.suggest(query).suggestions]
        assert actual == expected, query


def test_tie_break_is_lexicographic() -> None:
    dictionary = KeywordDictionary(["ac", "ab", "bb", "bc"])
    suggester = KeywordSuggester(dictionary, cache_size=0)

    result = suggester.suggest("aa", limit=3)

    assert [(item.distance, item.keyword) for item in result.suggestions] == [
        (1, "ab"),
        (1, "ac"),
        (2, "bb"),
    ]


def test_accent_insensitive_query() -> None:
    dictionary = KeywordDictionary(["balo cũ", "bàn phím cơ", "điện thoại samsung"])
    suggester = KeywordSuggester(dictionary, cache_size=0)

    assert suggester.suggest("ban", limit=1).suggestions[0].keyword == "bàn phím cơ"
    top = suggester.suggest("dien thoai samsng", limit=1).suggestions[0]
    assert (top.keyword, top.distance) == ("điện thoại samsung", 1)


def test_partial_query_matches_prefix(suggester: KeywordSuggester) -> None:
    """Gõ dở vẫn gợi ý theo tiền tố, không bị từ khóa ngắn lấn át."""
    result = suggester.suggest("tai nghe blu", limit=3)
    assert result.suggestions[0].keyword == "tai nghe bluetooth"
    assert result.suggestions[0].distance == 0

    dictionary = KeywordDictionary(["usb cũ", "điện thoại samsung văn phòng"])
    one_letter = KeywordSuggester(dictionary, cache_size=0).suggest("v", limit=1)
    assert one_letter.suggestions[0].keyword == "điện thoại samsung văn phòng"


def test_limit_and_empty_cases(suggester: KeywordSuggester) -> None:
    assert suggester.suggest("điện thoại", limit=0).suggestions == ()
    assert len(suggester.suggest("điện thoại", limit=2).suggestions) == 2
    assert suggester.suggest("!!!").suggestions == ()
    assert suggester.suggest("điện thoại", limit=100).suggestions  # không vượt quá từ điển


def test_max_distance_filters_results(suggester: KeywordSuggester) -> None:
    result = suggester.suggest("điện thoại samsng", limit=5, max_distance=1)
    assert all(item.distance <= 1 for item in result.suggestions)
    assert result.suggestions[0].keyword == "điện thoại samsung"
    assert len(result.suggestions) == 4  # mọi "điện thoại samsung ..." đều cách 1 phép

    none_found = suggester.suggest("xyzxyzxyz", limit=5, max_distance=0)
    assert none_found.suggestions == ()


def test_cache_hit(suggester: KeywordSuggester) -> None:
    first = suggester.suggest("tai nghe blutooth")
    second = suggester.suggest("tai nghe blutooth")

    assert first.cached is False
    assert second.cached is True
    assert second.suggestions == first.suggestions
    assert suggester.cache_stats()["hits"] == 1


def test_cache_key_includes_limit(suggester: KeywordSuggester) -> None:
    suggester.suggest("tai nghe", limit=3)
    other = suggester.suggest("tai nghe", limit=5)
    assert other.cached is False


def test_filters_out_most_candidates(real_dictionary_path) -> None:
    """Truy vấn sai một ký tự chỉ nên chạm tới một phần rất nhỏ từ điển."""
    dictionary = KeywordDictionary.from_file(real_dictionary_path)
    suggester = KeywordSuggester(dictionary, cache_size=0)

    result = suggester.suggest("điện thoại samsng", limit=5)

    assert result.suggestions[0].keyword == "điện thoại samsung"
    assert result.suggestions[0].distance == 1
    assert result.evaluated < 2000  # trong khi từ điển có 23.850 từ khóa


def test_random_dictionary_matches_brute_force() -> None:
    rng = random.Random(12345)
    alphabet = "abcđe"
    words = set()
    while len(words) < 120:
        word = "".join(rng.choice(alphabet) for _ in range(rng.randint(2, 9)))
        words.add(word)
    dictionary = KeywordDictionary(sorted(words))
    suggester = KeywordSuggester(dictionary, cache_size=0)

    for _ in range(40):
        query = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 10)))
        for limit in (1, 3, 5):
            expected = naive_top(dictionary, query, limit)
            actual = [
                (item.distance, item.keyword)
                for item in suggester.suggest(query, limit=limit).suggestions
            ]
            assert actual == expected, (query, limit)

        cap = rng.choice([0, 1, 2, 3])
        expected = [
            (distance, keyword)
            for distance, keyword in naive_top(dictionary, query, 5)
            if distance <= cap
        ]
        actual = [
            (item.distance, item.keyword)
            for item in suggester.suggest(query, limit=5, max_distance=cap).suggestions
        ]
        assert actual == expected, (query, cap)


def test_normalizes_query_before_matching(suggester: KeywordSuggester) -> None:
    result = suggester.suggest("  ĐIỆN THOẠI, SAMSUNG! ")
    assert result.suggestions[0].keyword == "điện thoại samsung"
    assert result.suggestions[0].distance == 0


def test_cache_evicts_old_entries() -> None:
    dictionary = KeywordDictionary(["điện thoại samsung", "tai nghe bluetooth", "chuột gaming"])
    suggester = KeywordSuggester(dictionary, cache_size=1)

    suggester.suggest("điện thoại", limit=3)
    suggester.suggest("tai nghe", limit=3)
    stats = suggester.cache_stats()

    assert stats["size"] == 1
    assert stats["evictions"] == 1


def test_clear_cache() -> None:
    dictionary = KeywordDictionary(["điện thoại samsung"])
    suggester = KeywordSuggester(dictionary, cache_size=4)

    suggester.suggest("điện thoại")
    suggester.clear_cache()

    assert suggester.cache_stats()["size"] == 0


def test_cache_disabled() -> None:
    dictionary = KeywordDictionary(["điện thoại samsung"])
    suggester = KeywordSuggester(dictionary, cache_size=0)

    assert suggester.suggest("điện thoại").cached is False
    assert suggester.suggest("điện thoại").cached is False
    assert suggester.cache_stats()["size"] == 0
