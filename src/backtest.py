from __future__ import annotations

import pandas as pd

from brain import score_candidates
from indicators import add_price_indicators
from storage import load_history


def run_simple_backtest(holding_days: int = 5, top_n: int = 10) -> pd.DataFrame:
    history = load_history()
    if history.empty:
        return pd.DataFrame()

    df = add_price_indicators(history)
    df = df.sort_values(["date", "stock_id"])
    results = []
    dates = sorted(df["date"].dropna().unique())

    for date in dates:
        past = df[df["date"] <= date]
        latest = past.groupby("stock_id", as_index=False).tail(1)
        scored = score_candidates(latest).head(top_n)
        for _, row in scored.iterrows():
            stock_id = row["stock_id"]
            future = df[(df["stock_id"] == stock_id) & (df["date"] > date)].head(holding_days)
            if len(future) < holding_days:
                continue
            entry = row["close"]
            exit_price = future.iloc[-1]["close"]
            if pd.isna(entry) or entry == 0 or pd.isna(exit_price):
                continue
            results.append(
                {
                    "date": date,
                    "stock_id": stock_id,
                    "stock_name": row.get("stock_name", ""),
                    "score": row.get("total_score", 0),
                    "entry": entry,
                    "exit": exit_price,
                    "return": exit_price / entry - 1,
                }
            )
    return pd.DataFrame(results)


def summarize_backtest(result: pd.DataFrame) -> str:
    if result.empty:
        return "目前歷史資料不足，尚無法完成回測。請先讓系統累積一段時間資料，或匯入歷史 OHLCV。"

    win_rate = (result["return"] > 0).mean()
    avg_return = result["return"].mean()
    median_return = result["return"].median()
    best = result["return"].max()
    worst = result["return"].min()
    return (
        "回測摘要\n\n"
        f"交易樣本數：{len(result)}\n"
        f"勝率：{win_rate:.1%}\n"
        f"平均報酬：{avg_return:.2%}\n"
        f"報酬中位數：{median_return:.2%}\n"
        f"最佳單筆：{best:.2%}\n"
        f"最差單筆：{worst:.2%}\n\n"
        "提醒：此為簡化回測，尚未納入手續費、證交稅、滑價與停損停利。"
    )


if __name__ == "__main__":
    print(summarize_backtest(run_simple_backtest()))
