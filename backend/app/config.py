"""Cấu hình dịch vụ, đọc từ biến môi trường."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import __version__

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_DICTIONARY_PATH = REPO_ROOT / "dictionary.txt"


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"Biến môi trường {name} phải là số nguyên, nhận được {raw!r}") from error
    if value < minimum:
        raise ValueError(f"Biến môi trường {name} phải >= {minimum}, nhận được {value}")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    """Toàn bộ cấu hình của ứng dụng."""

    dictionary_path: Path = DEFAULT_DICTIONARY_PATH
    cache_size: int = 1024
    cors_origins: tuple[str, ...] = ("*",)
    log_level: str = "INFO"
    version: str = __version__

    @classmethod
    def from_env(cls) -> Settings:
        raw_path = os.getenv("DICTIONARY_PATH", "").strip()
        dictionary_path = Path(raw_path).expanduser() if raw_path else DEFAULT_DICTIONARY_PATH
        if not dictionary_path.is_absolute():
            dictionary_path = (Path.cwd() / dictionary_path).resolve()

        raw_origins = os.getenv("CORS_ORIGINS", "*")
        cors_origins = tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())
        if not cors_origins:
            cors_origins = ("*",)

        return cls(
            dictionary_path=dictionary_path,
            cache_size=_env_int("SUGGEST_CACHE_SIZE", 1024, minimum=0),
            cors_origins=cors_origins,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
