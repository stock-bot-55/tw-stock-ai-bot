from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
REPORT_DIR = DATA_DIR / "reports"


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str = os.getenv("TG_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TG_CHAT_ID", "")
    mode: str = os.getenv("RUN_MODE", "morning")
    top_n: int = int(os.getenv("TOP_N", "10"))
    min_turnover_ntd: int = int(os.getenv("MIN_TURNOVER_NTD", "30000000"))
    cool_down_minutes: int = int(os.getenv("COOL_DOWN_MINUTES", "60"))
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "20"))


def ensure_dirs() -> None:
    for path in (DATA_DIR, CACHE_DIR, REPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)


settings = Settings()
