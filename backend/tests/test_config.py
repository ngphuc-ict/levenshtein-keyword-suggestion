"""Kiểm tra đọc cấu hình từ biến môi trường."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.config import DEFAULT_DICTIONARY_PATH, Settings


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("DICTIONARY_PATH", "SUGGEST_CACHE_SIZE", "CORS_ORIGINS", "LOG_LEVEL"):
        monkeypatch.delenv(name, raising=False)

    settings = Settings.from_env()

    assert settings.dictionary_path == DEFAULT_DICTIONARY_PATH
    assert settings.cache_size == 1024
    assert settings.cors_origins == ("*",)
    assert settings.log_level == "INFO"
    assert settings.version == "1.0.0"


def test_relative_dictionary_path_is_resolved(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DICTIONARY_PATH", "data/dictionary.txt")

    settings = Settings.from_env()

    assert settings.dictionary_path == (tmp_path / "data" / "dictionary.txt").resolve()


def test_cors_origins_are_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173, https://example.com")

    assert Settings.from_env().cors_origins == (
        "http://localhost:5173",
        "https://example.com",
    )


def test_blank_cors_falls_back_to_wildcard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", " , ")

    assert Settings.from_env().cors_origins == ("*",)


def test_cache_size_is_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUGGEST_CACHE_SIZE", "64")

    assert Settings.from_env().cache_size == 64


@pytest.mark.parametrize("value", ["abc", "-1", "3.5"])
def test_invalid_cache_size(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("SUGGEST_CACHE_SIZE", value)

    with pytest.raises(ValueError, match="SUGGEST_CACHE_SIZE"):
        Settings.from_env()


def test_log_level_is_uppercased(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "debug")

    assert Settings.from_env().log_level == "DEBUG"
