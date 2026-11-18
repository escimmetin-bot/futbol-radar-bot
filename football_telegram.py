"""
FutbolRadar | Telegram Yayın & Dağıtım Motoru
Futbol ve transfer haberlerini @Futbolradars kanalına fotoğraflı bülten olarak gönderir.
"""
import os
import requests
import html
import re

import config

TELEGRAM_BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
TELEGRAM_TARGET_CHAT = config.TELEGRAM_TARGET_CHAT


def format_telegram_caption(title: str, summary: str, club_info: dict, channel_handle: str = "@Futbolradars") -> str:
    """Telegram için şık, zengin ve emojili futbol haber metni."""
    c_title = html.unescape(title).strip()
    c_summary = html.unescape(summary)
    c_summary = re.sub(r'<[^>]+>', '', c_summary)
    c_summary = re.sub(r'https?://\S+', '', c_summary).strip()

    sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', c_summary) if len(s.strip()) > 20]
    body = " ".join(sents[:2]) if sents else c_title

    club_name = club_info.get("name", "SÜPER LİG")
    club_emoji = club_info.get("emoji", "⚽")
    is_transfer = club_info.get("is_transfer", False)

    header = "🔥 <b>TRANSFER BOMBASI!</b>" if is_transfer else "⚡ <b>FUTBOL SON DAKİKA!</b>"

    caption = (
        f"{header}\n\n"
        f"{club_emoji} <b>{club_name} | {c_title}</b>\n\n"
        f"{body}\n\n"
        f"⚽ <b>Futbol & Transfer Radarı</b> | {channel_handle}"
    )
    return caption[:1020]


def send_football_post_to_telegram(photo_path: str, caption: str, target_chat: str = None) -> bool:
    """Telegram kanalına fotoğraflı bülten gönderir."""
    chat_id = target_chat or TELEGRAM_TARGET_CHAT
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

    try:
        with open(photo_path, "rb") as f:
            resp = requests.post(
                url,
                data={
                    "chat_id": chat_id,
                    "caption": caption,
                    "parse_mode": "HTML"
                },
                files={"photo": f},
                timeout=25
            )
            data = resp.json()
            if data.get("ok"):
                return True
            else:
                print(f"⚠️ Telegram API Hatası: {data.get('description')}")
                return False
    except Exception as e:
        print(f"⚠️ Telegram Gönderim Hatası: {e}")
        return False
