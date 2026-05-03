from __future__ import annotations

from datetime import datetime

from brain import format_candidates, score_candidates
from config import ensure_dirs, settings
from data_sources import load_market_snapshot, twse_events
from indicators import add_price_indicators, latest_rows
from storage import append_daily_snapshot, save_report
from telegram_notify import TelegramNotConfigured, send_telegram_message


def build_report(mode: str) -> str:
    snapshot = load_market_snapshot()
    history = append_daily_snapshot(snapshot)
    enriched = add_price_indicators(history)
    latest = latest_rows(enriched)
    events = twse_events()
    candidates = score_candidates(latest, events)

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M")
    if mode == "morning":
        title = f"台股 AI 選股早報｜{now_text}"
    elif mode == "evening":
        title = f"台股 AI 選股晚報｜{now_text}"
    elif mode == "intraday":
        title = f"台股 AI 盤中飆股候選提醒｜{now_text}"
    else:
        title = f"台股 AI 選股報告｜{now_text}"

    return format_candidates(candidates, title, settings.top_n)


def main() -> None:
    ensure_dirs()
    report = build_report(settings.mode)
    filename = f"{settings.mode}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    path = save_report(filename, report)
    print(report)
    print(f"Report saved to {path}")

    try:
        send_telegram_message(report)
        print("Telegram message sent.")
    except TelegramNotConfigured as exc:
        print(f"Telegram skipped: {exc}")


if __name__ == "__main__":
    main()
