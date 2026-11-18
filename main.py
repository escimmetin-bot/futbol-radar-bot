"""
FutbolRadar | Ana Çalıştırıcı Motor
Kullanım:
  python main.py          (Normal döngü)
  python main.py --dry    (Simülasyon / Test modu)
"""
import os
import sys
import time

if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from football_news import fetch_football_articles
from football_card import generate_football_card
from football_poster import can_post_now, format_football_tweet, post_to_x, load_history, save_history
from football_telegram import format_telegram_caption, send_football_post_to_telegram


def run_cycle(dry_run: bool = False):
    print("=" * 60)
    print("⚽ FUTBOLRADAR | OTONOM FUTBOL & TRANSFER MOTORU")
    print("=" * 60)

    # 1. Zaman Kilidi Kontrolü
    if not dry_run:
        allowed, reason = can_post_now()
        if not allowed:
            print(f"⏳ [Zaman Kilidi] {reason}")
            return

    # 2. Futbol Haber Havuzu
    print("📡 Futbol & transfer akışları taranıyor...")
    articles = fetch_football_articles(config.FOOTBALL_RSS_FEEDS)
    print(f"  • {len(articles)} adet sıcak spor gelişmesi tespit edildi.")

    if not articles:
        print("ℹ️ Şu an paylaşılacak yeni içerik bulunamadı.")
        return

    history = load_history()
    posted_slugs = {h.get("slug") for h in history if isinstance(h, dict)}

    candidate = None
    for art in articles:
        if art["slug"] not in posted_slugs:
            candidate = art
            break

    if not candidate:
        print("ℹ️ Havuzdaki tüm haberler daha önce paylaşılmış.")
        return

    club_info = candidate["club"]
    print(f"🎯 [Seçilen Haber - {candidate['virality_score']} Puan]: {club_info['emoji']} {club_info['name']} - {candidate['title']}")

    # 3. Editoryal Lüks Kart Tasarımı
    out_dir = os.path.join(config.BASE_DIR, "output")
    os.makedirs(out_dir, exist_ok=True)
    card_path = os.path.join(out_dir, f"futbol_{candidate['slug'][:25]}.jpg")

    generate_football_card(
        title=candidate["title"],
        output_path=card_path,
        club_info=club_info,
        image_url=candidate.get("image_url"),
        brand_name=config.BRAND_NAME,
        handle=config.X_HANDLE
    )
    print(f"🎨 Editoryal Futbol Kartı Oluşturuldu: {card_path}")

    # 4. Tweet & Telegram Formatlama
    tweet_text = format_football_tweet(candidate["title"], candidate.get("summary", ""), club_info)
    tg_caption = format_telegram_caption(candidate["title"], candidate.get("summary", ""), club_info, channel_handle=config.TELEGRAM_TARGET_CHAT)
    print("-" * 40)
    print(tweet_text)
    print("-" * 40)

    # 5. Telegram Yayını
    print("✈️ Telegram yayını yapılıyor...")
    tg_ok = send_football_post_to_telegram(card_path, tg_caption)
    if tg_ok:
        print("✅ [Telegram] Futbol bülteni başarıyla gönderildi!")
    else:
        print("⚠️ [Telegram] Gönderim başarısız oldu.")

    # 6. X (Twitter) Yayını
    if not dry_run:
        print("🚀 X'e gönderiliyor...")
        x_res = post_to_x(tweet_text, card_path)
        if x_res.get("status") == "success":
            print("🎉 [FutbolRadar] X'e başarıyla paylaşıldı!")
            history.append({
                "slug": candidate["slug"],
                "title": candidate["title"],
                "club": club_info["name"],
                "status": "posted",
                "ts": time.time()
            })
            save_history(history)
        else:
            print(f"⚠️ [X Hatası] {x_res.get('message')}")
            if tg_ok:
                history.append({
                    "slug": candidate["slug"],
                    "title": candidate["title"],
                    "club": club_info["name"],
                    "status": "posted_telegram",
                    "ts": time.time()
                })
                save_history(history)
    else:
        print("🧪 [DRY RUN] Tweet atılmadı, simülasyon tamamlandı.")


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    run_cycle(dry_run=dry)
