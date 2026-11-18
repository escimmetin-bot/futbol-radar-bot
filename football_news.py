"""
FutbolRadar | Haber ve Transfer Akış Motoru
Fanatik, Fotomaç, Ajansspor, NTVSpor ve BBC Sport gibi kaynaklardan en sıcak futbol & transfer haberlerini çeker.
"""
import re
import html
import sys
import urllib.parse
import urllib.request
import json
import feedparser
import requests
from typing import List, Dict

if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def ensure_turkish(text: str) -> str:
    """Yabancı dildeki haberleri anında akıcı Türkçeye çevirir."""
    if not text:
        return ""
    tr_markers = [" ve ", " bir ", " için ", " ile ", " da ", " de ", "nin ", "nin\n", "nın ", "den ", "dan "]
    if any(c in text for c in "çğıöşüÇĞİÖŞÜ") or any(m in f" {text.lower()} " for m in tr_markers):
        return text

    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=tr&dt=t&q=" + urllib.parse.quote(text)
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5) as r:
            res = json.loads(r.read().decode("utf-8"))
            translated_parts = [p[0] for p in res[0] if p and p[0]]
            return "".join(translated_parts).strip()
    except Exception:
        return text


CLUBS = {
    "GALATASARAY": {
        "keywords": ["galatasaray", "cimbom", "aslan", "okan buruk", "icardi", "osimhen", "barış alper", "muslera", "torreira", "sara"],
        "emoji": "🟡🔴",
        "primary_color": "#FDB913",  # Sarı
        "secondary_color": "#C8102E"  # Kırmızı
    },
    "FENERBAHÇE": {
        "keywords": ["fenerbahçe", "kanarya", "mourinho", "dzeko", "tadic", "fred", "symanski", "en-nesyri", "livakovic", "ferdi"],
        "emoji": "🟡🔵",
        "primary_color": "#FFE500",  # Sarı
        "secondary_color": "#002D72"  # Lacivert
    },
    "BEŞİKTAŞ": {
        "keywords": ["beşiktaş", "kartal", "kara kartal", "bronckhorst", "rafa silva", "immobile", "gedson", "semih kılıçsoy", "muçi", "masuaku"],
        "emoji": "⚪⚫",
        "primary_color": "#FFFFFF",  # Beyaz
        "secondary_color": "#1E1E1E"  # Siyah
    },
    "TRABZONSPOR": {
        "keywords": ["trabzonspor", "fırtına", "şenol güneş", "uğurcan", "visca", "baniya", "cham", "savic", "nwakaeme"],
        "emoji": "🟣🔵",
        "primary_color": "#800020",  # Bordo
        "secondary_color": "#00A3E0"  # Mavi
    },
    "REAL MADRİD / ARDA GÜLER": {
        "keywords": ["arda güler", "real madrid", "ancelotti", "mbappe", "vinicius", "bellingham"],
        "emoji": "⚪👑",
        "primary_color": "#FEBE10",
        "secondary_color": "#111827"
    },
    "A MİLLİ TAKIM": {
        "keywords": ["milli takım", "montella", "türkiye", "ay-yıldız", "hakan çalhanoğlu", "kenan yıldız", "kerem aktürkoğlu"],
        "emoji": "🇹🇷",
        "primary_color": "#E30A17",
        "secondary_color": "#FFFFFF"
    }
}

TRANSFER_KEYWORDS = {
    "anlaştı": 50, "imza": 50, "transfer": 45, "bonservis": 45, "ayrılık": 40,
    "resmi açıklama": 50, "bomba transfer": 50, "here we go": 55, "masada": 40,
    "teklif": 40, "kiralık": 35, "sözleşme": 35, "yeni kulübü": 45, "vedalaştı": 40
}

MATCH_KEYWORDS = {
    "gol": 40, "derbi": 50, "penaltı": 35, "kırmızı kart": 35, "şampiyonluk": 45,
    "lider": 35, "tarihi zafer": 45, "maç sonucu": 40, "şampiyonlar ligi": 45
}

JUNK_KEYWORDS = [
    "kimdir", "nereli", "kaç yaşında", "burç", "astroloji", "indirim",
    "can yeleği", "dizi", "magazin", "sevgilisi", "eşinden"
]


def detect_relevant_club(title: str, summary: str = "") -> dict:
    """Haber metninden ilgili takımı ve transfer durumunu tespit eder."""
    text = f"{title} {summary}".lower()

    # Kulüp Tespiti
    matched_club_name = None
    matched_data = None
    for club_name, info in CLUBS.items():
        if any(kw in text for kw in info["keywords"]):
            matched_club_name = club_name
            matched_data = info
            break

    if not matched_club_name:
        matched_club_name = "SÜPER LİG"
        matched_data = {
            "emoji": "⚽",
            "primary_color": "#10B981",
            "secondary_color": "#064E3B"
        }

    # Transfer Durumu
    is_transfer = any(tk in text for tk in TRANSFER_KEYWORDS.keys())

    return {
        "name": matched_club_name,
        "emoji": matched_data["emoji"],
        "primary_color": matched_data["primary_color"],
        "secondary_color": matched_data["secondary_color"],
        "is_transfer": is_transfer
    }


def calculate_football_virality(title: str, summary: str) -> int:
    score = 100
    text = f"{title} {summary}".lower()

    # Transfer puanı
    for kw, pt in TRANSFER_KEYWORDS.items():
        if re.search(rf"\b{re.escape(kw)}\b", text):
            score += pt

    # Maç / Derbi puanı
    for kw, pt in MATCH_KEYWORDS.items():
        if re.search(rf"\b{re.escape(kw)}\b", text):
            score += pt

    # Büyük kulüp bonusu
    for c_info in CLUBS.values():
        if any(kw in text for kw in c_info["keywords"]):
            score += 35
            break

    # Çöp filtre
    for jk in JUNK_KEYWORDS:
        if jk in text:
            score -= 150

    return score


def fetch_football_articles(feed_urls: List[str]) -> List[Dict]:
    articles = []
    seen_titles = set()

    for url in feed_urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:15]:
                title = entry.get("title", "").strip()
                if not title or title.lower() in seen_titles or len(title) < 18:
                    continue

                seen_titles.add(title.lower())
                summary = entry.get("summary", "") or entry.get("description", "")
                
                # HTML temizliği
                clean_summary = re.sub(r'<[^>]+>', '', summary).strip()
                clean_title = re.sub(r'<[^>]+>', '', title).strip()

                # Türkçe garantisi
                clean_title = ensure_turkish(clean_title)
                clean_summary = ensure_turkish(clean_summary)

                # Görsel bulma (Enclosures, media_content, veya HTML içi img)
                img_url = None
                if hasattr(entry, "enclosures") and entry.enclosures:
                    img_url = entry.enclosures[0].href
                elif hasattr(entry, "media_content") and entry.media_content:
                    img_url = entry.media_content[0].get("url")
                elif hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                    img_url = entry.media_thumbnail[0].get("url")

                if not img_url:
                    raw_html = summary or ""
                    found_imgs = re.findall(r'<img[^>]+src=[\'"]([^\'"]+)[\'"]', raw_html)
                    if found_imgs:
                        img_url = found_imgs[0]

                # Web sayfasından orijinal manşet fotoğrafı (og:image)
                article_link = entry.get("link", "")
                if not img_url and article_link:
                    try:
                        r_page = requests.get(article_link, headers=HEADERS, timeout=4)
                        if r_page.status_code == 200:
                            og_match = re.search(r'<meta[^>]+property=[\'"]og:image[\'"][^>]+content=[\'"]([^\'"]+)[\'"]', r_page.text, re.I)
                            if not og_match:
                                og_match = re.search(r'<meta[^>]+content=[\'"]([^\'"]+)[\'"][^>]+property=[\'"]og:image[\'"]', r_page.text, re.I)
                            if og_match:
                                img_url = og_match.group(1)
                    except Exception:
                        pass

                score = calculate_football_virality(clean_title, clean_summary)
                if score < 60:
                    continue

                slug = re.sub(r'[^a-zA-Z0-9]+', '-', clean_title.lower()).strip('-')[:50]
                club_info = detect_relevant_club(clean_title, clean_summary)

                articles.append({
                    "title": clean_title,
                    "summary": clean_summary,
                    "link": entry.get("link", ""),
                    "image_url": img_url,
                    "virality_score": score,
                    "slug": slug,
                    "club": club_info
                })
        except Exception as e:
            print(f"⚠️ RSS Okuma Hatası ({url}): {e}")
            continue

    # En yüksek virallik puanına göre sırala
    articles.sort(key=lambda x: x["virality_score"], reverse=True)
    return articles


if __name__ == "__main__":
    from config import FOOTBALL_RSS_FEEDS
    items = fetch_football_articles(FOOTBALL_RSS_FEEDS)
    print(f"Toplanan Futbol Haber Sayısı: {len(items)}")
    for it in items[:3]:
        print(f"[{it['virality_score']} Puan] {it['club']['emoji']} {it['club']['name']} - {it['title']}")
