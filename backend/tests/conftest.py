"""Fixture dùng chung cho bộ test."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_DICTIONARY = REPO_ROOT / "dictionary.txt"

# Từ điển nhỏ, cố định để test API ổn định và chạy nhanh.
SAMPLE_WORDS = [
    "điện thoại samsung",
    "điện thoại samsung chính hãng",
    "điện thoại samsung giá rẻ",
    "điện thoại samsung cũ",
    "điện thoại samsung 128gb",
    "điện thoại apple",
    "điện thoại xiaomi",
    "điện thoại oppo",
    "điện thoại gaming",
    "tai nghe bluetooth",
    "tai nghe bluetooth chống nước",
    "tai nghe bluetooth giá rẻ",
    "tai nghe có dây",
    "tai nghe không dây",
    "tai nghe gaming",
    "áo thun akko",
    "áo thun akko cũ",
    "áo thun nam",
    "bàn phím cơ",
    "bàn phím cơ gaming",
    "bàn phím không dây",
    "chuột không dây",
    "chuột gaming",
    "laptop dell",
    "laptop dell cũ",
    "laptop asus",
    "laptop hp",
    "nồi cơm điện",
    "quạt điện mini",
    "quạt điện cũ",
]


@pytest.fixture()
def sample_dictionary(tmp_path: Path) -> Path:
    path = tmp_path / "dictionary.txt"
    path.write_text("\n".join(SAMPLE_WORDS) + "\n", encoding="utf-8")
    return path


@pytest.fixture()
def settings(sample_dictionary: Path) -> Settings:
    return Settings(dictionary_path=sample_dictionary, cache_size=32, log_level="WARNING")


@pytest.fixture()
def client(settings: Settings):
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def real_dictionary_path() -> Path:
    if not REAL_DICTIONARY.is_file():
        pytest.skip(f"Không có từ điển thật tại {REAL_DICTIONARY}")
    return REAL_DICTIONARY
