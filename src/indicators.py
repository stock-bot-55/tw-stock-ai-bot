from __future__ import annotations

import pandas as pd


def add_price_indicators(history: pd.DataFrame) -> pd.DataFrame:
    """Add rolling indicators to a long-format OHLCV dataframe.

    Required columns are stock_id, date, close and volume. Missing values are kept
    as NaN so the scoring engine can apply conservative defaults.
    """
    if history.empty:
        return history

    df = history.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["stock_id", "date"])

    grouped = df.groupby("stock_id", group_keys=False)
    for window in (5, 10, 20, 60):
        df[f"ma{window}"] = grouped["close"].rolling(window).mean().reset_index(level=0, drop=True)
        df[f"vol_ma{window}"] = grouped["volume"].rolling(window).mean().reset_index(level=0, drop=True)

    df["ret_1d"] = grouped["close"].pct_change(1)
    df["ret_5d"] = grouped["close"].pct_change(5)
    df["ret_20d"] = grouped["close"].pct_change(20)
    df["volume_ratio_20"] = df["volume"] / df["vol_ma20"]
    df["break_ma20"] = (df["close"] > df["ma20"]) & (grouped["close"].shift(1) <= grouped["ma20"].shift(1))
    df["rsi14"] = grouped.apply(_rsi14).reset_index(level=0, drop=True)
    return df


def _rsi14(group: pd.DataFrame) -> pd.Series:
    diff = group["close"].diff()
    gain = diff.clip(lower=0).rolling(14).mean()
    loss = (-diff.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def latest_rows(history_with_indicators: pd.DataFrame) -> pd.DataFrame:
    if history_with_indicators.empty:
        return history_with_indicators
    df = history_with_indicators.sort_values(["stock_id", "date"])
    return df.groupby("stock_id", as_index=False).tail(1)
