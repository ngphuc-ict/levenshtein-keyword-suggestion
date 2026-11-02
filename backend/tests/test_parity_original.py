"""Đối chiếu backend với bản thuật toán gốc trong repo (algorithm.py).

Mục tiêu: bảo đảm phần tối ưu (chỉ mục trigram, quy hoạch động có chặn)
không làm thay đổi kết quả so với cách làm ban đầu của nhóm.
"""

from __future__ import annotations

import importlib.util
import random
import unicodedata
from pathlib import Path
from types import ModuleType

import pytest

from app.core.dictionary import KeywordDictionary
from app.core.levenshtein import bounded_levenshtein_distance, levenshtein_distance
from app.core.suggester import KeywordSuggester
from app.core.text import normalize_text

REPO_ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_ALGORITHM = REPO_ROOT / "algorithm.py"
ORIGINAL_PROCESSOR = REPO_ROOT / "data_processor.py"

ALPHABET = "abcđeêghiklmnôơpqrstuưvxyáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọ "


def _load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def original() -> ModuleType:
    if not ORIGINAL_ALGORITHM.is_file():
        pytest.skip("Không tìm thấy algorithm.py gốc")
    return _load_module(ORIGINAL_ALGORITHM, "original_algorithm")


def test_distance_matches_original(original: ModuleType) -> None:
    rng = random.Random(2025)
    reference = original.LevenshteinSuggester()
    for _ in range(300):
        left = "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 18)))
        right = "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 18)))
        assert levenshtein_distance(left, right) == reference.levenshtein_distance(left, right)


def test_normalization_matches_original(original: ModuleType, real_dictionary_path: Path) -> None:
    processor = (
        _load_module(ORIGINAL_PROCESSOR, "original_data_processor").DictionaryProcessor(
            real_dictionary_path
        )
        if ORIGINAL_PROCESSOR.is_file()
        else None
    )
    samples = [
        "Điện Thoại, Samsung!",
        "  tai   nghe  ",
        "ÁO-THUN (AKKO)",
        "Iphone_15 Pro",
        unicodedata.normalize("NFD", "điện thoại samsung"),
        "...",
    ]
    for sample in samples:
        assert normalize_text(sample) == original.LevenshteinSuggester.normalize(sample)
        if processor is not None:
            assert normalize_text(sample) == processor.normalize_text(sample)


def test_bounded_never_underestimates(original: ModuleType) -> None:
    rng = random.Random(7)
    reference = original.LevenshteinSuggester()
    for _ in range(200):
        left = "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 14)))
        right = "".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 14)))
        exact = reference.levenshtein_distance(left, right)
        limit = rng.randint(0, 6)
        bounded = bounded_levenshtein_distance(left, right, limit)
        if exact <= limit:
            assert bounded == exact
        else:
            assert bounded == limit + 1


def test_ranking_matches_original_on_subset(
    original: ModuleType, real_dictionary_path: Path
) -> None:
    dictionary = KeywordDictionary.from_file(real_dictionary_path)
    subset = list(dictionary.keywords)[::16]  # ~1.500 từ khóa, đủ đa dạng
    backend = KeywordSuggester(KeywordDictionary(subset), cache_size=0)
    reference = original.LevenshteinSuggester()

    rng = random.Random(11)

    def mutate(word: str) -> str:
        characters = list(word)
        for _ in range(rng.randint(1, 3)):
            operation = rng.choice("ids")
            if not characters:
                break
            index = rng.randrange(len(characters))
            if operation == "i":
                characters.insert(index, rng.choice(ALPHABET))
            elif operation == "d":
                characters.pop(index)
            else:
                characters[index] = rng.choice(ALPHABET)
        return "".join(characters)

    for _ in range(15):
        query = mutate(rng.choice(subset))
        expected = [
            (item.keyword, item.distance)
            for item in reference.rank_suggestions(query, subset, limit=5)
        ]
        actual = [
            (item.keyword, item.distance) for item in backend.suggest(query, limit=5).suggestions
        ]
        assert actual == expected, query


def test_ranking_matches_original_on_full_dictionary(original: ModuleType) -> None:
    """Hai truy vấn mẫu trong README, chạy trên toàn bộ 23.850 từ khóa."""
    dictionary = KeywordDictionary.from_file(REPO_ROOT / "dictionary.txt")
    backend = KeywordSuggester(dictionary, cache_size=0)
    reference = original.LevenshteinSuggester()
    all_keywords = list(dictionary.keywords)

    for query in ("điện thoại samsng", "tai nghe blutooth"):
        expected = [
            (item.keyword, item.distance)
            for item in reference.rank_suggestions(query, all_keywords, limit=5)
        ]
        actual = [
            (item.keyword, item.distance) for item in backend.suggest(query, limit=5).suggestions
        ]
        assert actual == expected, query
