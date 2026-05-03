from __future__ import annotations

import requests

from config import settings


class TelegramNotConfigured(RuntimeError):
    pass


def send_telegram_message(text: str) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise TelegramNotConfigured("TG_BOT_TOKEN or TG_CHAT_ID is missing. Please set GitHub Secrets first.")

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": text[:3900],
        "disable_web_page_preview": True,
    }
    response = requests.post(url, json=payload, timeout=settings.request_timeout)
    response.raise_for_status()
