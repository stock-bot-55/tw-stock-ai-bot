from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from config import settings


@dataclass(frozen=True)
class BrainWeights:
    momentum: float = 0.30
    volume: float = 0.20
    chip: float = 0.20
    fundamental: float = 0.15
    event: float = 0.10
    risk: float = 0.05


WEIGHTS = BrainWeights()


def _clip_score(value: float) -> float:
    if pd.isna(value):
        return 0.0
    return float(np.clip(value, 0, 100))


def score_candidates(latest: pd.DataFrame, events: pd.DataFrame | None = None) -> pd.DataFrame:
    if latest.empty:
        return latest

    df = latest.copy()
    df["momentum_score"] = df.apply(_momentum_score, axis=1)
    df["volume_score"] = df.apply(_volume_score, axis=1)
    df["chip_score"] = df.apply(_chip_score, axis=1)
    df["fundamental_score"] = df.apply(_fundamental_score, axis=1)
    df["event_score"] = _event_scores(df, events)
    df["risk_score"] = df.apply(_risk_score, axis=1)

    df["total_score"] = (
        df["momentum_score"] * WEIGHTS.momentum
        + df["volume_score"] * WEIGHTS.volume
        + df["chip_score"] * WEIGHTS.chip
        + df["fundamental_score"] * WEIGHTS.fundamental
        + df["event_score"] * WEIGHTS.event
        + df["risk_score"] * WEIGHTS.risk
    )

    df["reasons"] = df.apply(explain_row, axis=1)
    df = apply_hard_filters(df)
    return df.sort_values("total_score", ascending=False)


def apply_hard_filters(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()
    if "turnover" in filtered.columns:
        filtered = filtered[filtered["turnover"].fillna(0) >= settings.min_turnover_ntd]
    if "close" in filtered.columns:
        filtered = filtered[filtered["close"].fillna(0) >= 10]
    return filtered


def _momentum_score(row: pd.Series) -> float:
    score = 0.0
    ret_5d = row.get("ret_5d")
    ret_20d = row.get("ret_20d")
    close = row.get("close")
    ma20 = row.get("ma20")
    ma60 = row.get("ma60")

    if pd.notna(ret_5d):
        score += np.clip(ret_5d * 500, -20, 35)
    if pd.notna(ret_20d):
        score += np.clip(ret_20d * 250, -20, 30)
    if pd.notna(close) and pd.notna(ma20) and close > ma20:
        score += 20
    if pd.notna(close) and pd.notna(ma60) and close > ma60:
        score += 15
    if bool(row.get("break_ma20", False)):
        score += 20
    return _clip_score(score)


def _volume_score(row: pd.Series) -> float:
    ratio = row.get("volume_ratio_20")
    if pd.isna(ratio):
        return 30.0
    if ratio < 0.8:
        return 20.0
    if ratio < 1.2:
        return 45.0
    if ratio < 2.0:
        return 70.0
    if ratio < 4.0:
        return 90.0
    return 75.0


def _chip_score(row: pd.Series) -> float:
    # 初版先給中性分數。後續接入法人買賣超、融資融券變化與券資比後，可在此擴充。
    return 50.0


def _fundamental_score(row: pd.Series) -> float:
    score = 50.0
    pe = row.get("pe")
    pb = row.get("pb")
    dividend_yield = row.get("dividend_yield")

    if pd.notna(pe):
        if 8 <= pe <= 25:
            score += 20
        elif pe > 60 or pe <= 0:
            score -= 20
    if pd.notna(pb):
        if 0.8 <= pb <= 4:
            score += 10
        elif pb > 8:
            score -= 10
    if pd.notna(dividend_yield) and dividend_yield >= 2:
        score += 10
    return _clip_score(score)


def _event_scores(df: pd.DataFrame, events: pd.DataFrame | None) -> pd.Series:
    if events is None or events.empty or "stock_id" not in events.columns:
        return pd.Series([40.0] * len(df), index=df.index)

    positive_words = "營收 成長 接單 法說 擴產 得標 新產品 AI 半導體 合作".split()
    negative_words = "處分 訴訟 停工 裁罰 虧損 下修 減資 違約".split()
    event_map: dict[str, float] = {}
    for stock_id, group in events.groupby("stock_id"):
        text = " ".join(group.astype(str).agg(" ".join, axis=1).tolist())
        score = 40.0
        score += sum(8 for word in positive_words if word in text)
        score -= sum(12 for word in negative_words if word in text)
        event_map[str(stock_id)] = _clip_score(score)
    return df["stock_id"].astype(str).map(event_map).fillna(40.0)


def _risk_score(row: pd.Series) -> float:
    score = 70.0
    close = row.get("close")
    turnover = row.get("turnover")
    rsi = row.get("rsi14")
    volume_ratio = row.get("volume_ratio_20")

    if pd.notna(close) and close < 10:
        score -= 40
    if pd.notna(turnover) and turnover < settings.min_turnover_ntd:
        score -= 30
    if pd.notna(rsi) and rsi > 85:
        score -= 20
    if pd.notna(volume_ratio) and volume_ratio > 5:
        score -= 15
    return _clip_score(score)


def explain_row(row: pd.Series) -> str:
    reasons: list[str] = []
    if bool(row.get("break_ma20", False)):
        reasons.append("突破 20 日均線")
    if pd.notna(row.get("volume_ratio_20")) and row.get("volume_ratio_20") >= 2:
        reasons.append(f"量能約為 20 日均量 {row.get('volume_ratio_20'):.1f} 倍")
    if pd.notna(row.get("ret_5d")) and row.get("ret_5d") > 0.05:
        reasons.append(f"5 日漲幅 {row.get('ret_5d'):.1%}")
    if pd.notna(row.get("pe")) and 8 <= row.get("pe") <= 25:
        reasons.append("本益比位於合理區間")
    if not reasons:
        reasons.append("綜合分數達標，但尚無單一強烈訊號")
    return "；".join(reasons)


def format_candidates(candidates: pd.DataFrame, title: str, top_n: int | None = None) -> str:
    top_n = top_n or settings.top_n
    if candidates.empty:
        return f"{title}\n\n目前沒有符合條件的候選股。"

    lines = [title, "", "以下為系統依技術、量能、籌碼、基本面與事件面計算的候選名單：", ""]
    for _, row in candidates.head(top_n).iterrows():
        lines.append(
            f"{row.get('stock_id')} {row.get('stock_name', '')}｜總分 {row.get('total_score', 0):.1f}｜"
            f"收盤 {row.get('close', 0):.2f}｜量能分 {row.get('volume_score', 0):.0f}｜"
            f"理由：{row.get('reasons', '')}"
        )
    lines.append("\n提醒：本訊息僅為量化研究與選股提醒，不是投資建議。")
    return "\n".join(lines)
