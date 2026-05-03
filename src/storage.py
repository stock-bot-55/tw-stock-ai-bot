from __future__ import annotations

from pathlib import Path

import pandas as pd

from config import DATA_DIR

HISTORY_PATH = DATA_DIR / "daily_history.csv"
ALERT_STATE_PATH = DATA_DIR / "alert_state.csv"


def load_history() -> pd.DataFrame:
    if not HISTORY_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(HISTORY_PATH)


def append_daily_snapshot(snapshot: pd.DataFrame) -> pd.DataFrame:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    current = snapshot.copy()
    keep_cols = [
        "date",
        "market",
        "stock_id",
        "stock_name",
        "open",
        "high",
        "low",
        "close",
        "change",
        "volume",
        "turnover",
        "pe",
        "pb",
        "dividend_yield",
        "industry",
    ]
    current = current[[c for c in keep_cols if c in current.columns]]
    old = load_history()
    combined = pd.concat([old, current], ignore_index=True)
    if {"date", "stock_id"}.issubset(combined.columns):
        combined = combined.drop_duplicates(["date", "stock_id"], keep="last")
        combined = combined.sort_values(["stock_id", "date"])
    combined.to_csv(HISTORY_PATH, index=False)
    return combined


def save_report(name: str, text: str) -> Path:
    report_dir = DATA_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / name
    path.write_text(text, encoding="utf-8")
    return path


def load_alert_state() -> pd.DataFrame:
    if not ALERT_STATE_PATH.exists():
        return pd.DataFrame(columns=["stock_id", "last_alert_at", "last_score"])
    return pd.read_csv(ALERT_STATE_PATH)


def save_alert_state(df: pd.DataFrame) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(ALERT_STATE_PATH, index=False)
