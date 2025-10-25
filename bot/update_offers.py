import os
import requests
import feedparser
from datetime import datetime
import time
import json
from ftplib import FTP

# === Config ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH")  # esempio: /public_html/index.html o /index.html

if not all([TELEGRAM_TOKEN, CHAT_ID, FTP_HOST, FTP_USER, FTP_PASS, FTP_PATH]):
    raise ValueError("Mancano uno o più secrets richiesti (TELEGRAM, FTP).")

# === Fonti offerte Amazon ===
FEEDS = [
    "https://www.offerteshock.it/feed/",
    "https://www.kechiusa.it/offerte-amazon/feed/",
    "https://www.prezzi.tech/feed/",
    "https://www.prezzipazzi.com/feed/",
    "https://www.offertepertutti.it/feed/",
    "https://www.scontodelgiorno.it/feed/"
]

CACHE_FILE = "bot/last_offers.json"


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return []
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_rss_offers(limit=10):
    offers = []
    for feed_url in FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                link = entry.link.strip()
                if "amazon.it" in link.lower():
                    offers.append({
                        "title": entry.title.strip(),
                        "link": link
                    })
                if len(offers) >= limit:
                    break
        except Exception as e:
            print(f"Errore feed {feed_url}: {e}")
        time.sleep(1)
        if len(offers) >= limit:
            break
    return offers[:limit]


def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    r = requests.post(url, data=payload)
    if r.status_code != 200:
        print("Errore Telegram:", r.text)


def fetch_homepage():
    """Scarica la homepage esistente da Aruba."""
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    lines = []
    ftp.retrlines(f"RETR {FTP_PATH}", lines.append)
    ftp.quit()
    return "\n".join(lines)


def upload_homepage(content):
    """Ricarica la homepage modificata su Aruba."""
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.storbinary(f"STOR {FTP_PATH}", content.encode("utf-8"))
    ftp.quit()


def inject_offers_into_html(original_html, offers):
    """Sostituisce il blocco tra <!-- OFFERTE_START --> e <!-- OFFERTE_END -->"""
    start_tag = "<!-- OFFERTE_START -->"
    end_tag = "<!-- OFFERTE_END -->"
    start = original_html.find(start_tag)
    end = original_html.find(end_tag)

    if start == -1 or end == -1:
        raise ValueError("Tag OFFERTE_START o OFFERTE_END mancanti nella homepage.")

    offers_html = f"\n<h2>🔥 Offerte Amazon (aggiornate {datetime.now().strftime('%H:%M %d/%m/%Y')})</h2>\n"
    for o in offers:
        offers_html += f"<div><a href='{o['link']}' target='_blank'>{o['title']}</a></div>\n"

    return original_html[:start + len(start_tag)] + offers_html + original_html[end:]


def main():
    offers = get_rss_offers(limit=10)
    if not offers:
        send_telegram_message("⚠️ Nessuna offerta trovata nei feed RSS.")
        return

    try:
    html = fetch_homepage()
    updated_html = inject_offers_into_html(html, new_offers)
    upload_homepage(updated_html)

    # 🔽 Messaggio Telegram con bottoni
    url_sito = "https://www.techandmore.eu"
    url_canale = "https://t.me/amazontechandmore"  # <-- metti qui il link reale del tuo canale

    testo = "<b>🔥 Homepage aggiornata con le ultime offerte Amazon!</b>\n\n📢 Controlla le novità anche sul sito o unisciti al canale."

    payload = {
        "chat_id": CHAT_ID,
        "text": testo,
        "parse_mode": "HTML",
        "reply_markup": json.dumps({
            "inline_keyboard": [
                [
                    {"text": "🌐 Vai al sito TechAndMore.eu", "url": url_sito}
                ],
                [
                    {"text": "🔔 Iscriviti al canale Telegram", "url": url_canale}
                ]
            ]
        })
    }

    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data=payload)

except Exception as e:
    send_telegram_message(f"❌ Errore aggiornamento homepage: {e}")


if __name__ == "__main__":
    main()
