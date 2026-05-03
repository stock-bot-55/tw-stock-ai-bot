from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from config import CACHE_DIR, settings

TWSE_BASE = "https://openapi.twse.com.tw/v1"


class DataSourceError(RuntimeError):
    pass


def _cache_path(name: str) -> Path:
    safe = name.strip("/").replace("/", "__")
    return CACHE_DIR / f"{safe}.json"


def fetch_json(endpoint: str, cache_name: str | None = None, ttl_seconds: int = 300) -> list[dict[str, Any]]:
    """Fetch JSON with cache and conservative retry.

    The project deliberately uses low-frequency requests and cache files to reduce the
    chance of being blocked by free public sources.
    """
    cache_name = cache_name or endpoint
    path = _cache_path(cache_name)
    now = time.time()
    if path.exists() and now - path.stat().st_mtime <= ttl_seconds:
        return json.loads(path.read_text(encoding="utf-8"))

    url = endpoint if endpoint.startswith("http") else f"{TWSE_BASE}{endpoint}"
    headers = {
        "User-Agent": "tw-stock-ai-bot/0.1 (+personal research; low frequency)",
        "Accept": "application/json,text/plain,*/*",
    }

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=settings.request_timeout)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                raise DataSourceError(f"Unexpected JSON type from {url}: {type(data)!r}")
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return data
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(2 + attempt * 3)

    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    raise DataSourceError(f"Failed to fetch {url}: {last_error}")


def _to_number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).replace(",", "").replace("--", "").strip()
    if text in {"", "-", "X", "NaN"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def twse_daily_quotes() -> pd.DataFrame:
    rows = fetch_json("/exchangeReport/STOCK_DAY_ALL", ttl_seconds=240)
    df = pd.DataFrame(rows)
    rename = {
        "Code": "stock_id",
        "Name": "stock_name",
        "TradeVolume": "volume",
        "TradeValue": "turnover",
        "OpeningPrice": "open",
        "HighestPrice": "high",
        "LowestPrice": "low",
        "ClosingPrice": "close",
        "Change": "change",
        "Transaction": "transactions",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    for col in ["volume", "turnover", "open", "high", "low", "close", "change", "transactions"]:
        if col in df.columns:
            df[col] = df[col].map(_to_number)
    df["market"] = "TWSE"
    df["date"] = datetime.now(timezone.utc).astimezone().date().isoformat()
    return df


def twse_valuation() -> pd.DataFrame:
    rows = fetch_json("/exchangeReport/BWIBBU_ALL", ttl_seconds=3600)
    df = pd.DataFrame(rows)
    rename = {
        "Code": "stock_id",
        "Name": "stock_name",
        "PEratio": "pe",
        "DividendYield": "dividend_yield",
        "PBratio": "pb",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    for col in ["pe", "dividend_yield", "pb"]:
        if col in df.columns:
            df[col] = df[col].map(_to_number)
    return df


def twse_margin() -> pd.DataFrame:
    rows = fetch_json("/exchangeReport/MI_MARGN", ttl_seconds=3600)
    df = pd.DataFrame(rows)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def twse_company_info() -> pd.DataFrame:
    rows = fetch_json("/opendata/t187ap03_L", ttl_seconds=24 * 3600)
    df = pd.DataFrame(rows)
    rename = {
        "公司代號": "stock_id",
        "公司名稱": "company_name",
        "產業別": "industry",
        "營利事業統一編號": "tax_id",
        "上市日期": "listed_date",
    }
    return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})


def twse_events() -> pd.DataFrame:
    rows = fetch_json("/opendata/t187ap04_L", ttl_seconds=900)
    df = pd.DataFrame(rows)
    rename = {
        "公司代號": "stock_id",
        "公司名稱": "stock_name",
        "主旨": "title",
        "發言日期": "event_date",
        "發言時間": "event_time",
        "符合條款": "rule",
        "事實發生日": "fact_date",
    }
    return df.rename(columns={k: v for k, v in rename.items() if k in df.columns})


def load_market_snapshot() -> pd.DataFrame:
    quotes = twse_daily_quotes()
    valuation = twse_valuation()
    company = twse_company_info()

    df = quotes.merge(valuation, on=["stock_id", "stock_name"], how="left")
    if "stock_id" in company.columns:
        df = df.merge(company[[c for c in ["stock_id", "industry", "company_name"] if c in company.columns]], on="stock_id", how="left")
    return df
