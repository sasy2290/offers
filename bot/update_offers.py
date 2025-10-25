import os
import requests
import feedparser
from datetime import datetime
import time

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise ValueError("Mancano TELEGRAM_TOKEN o CHAT_ID nei Secrets GitHub.")

# Feed RSS di offerte Amazon da siti affiliati
FEEDS = [
    "https://www.offerteshock.it/feed/",
    "https://www.kechiusa.it/offerte-amazon/feed/",
    "https://www.prezzi.tech/feed/"
]

def get_rss_offers(limit=5):
    """Legge i feed RSS e restituisce le ultime offerte trovate."""
    offers = []
    for feed_url in FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:limit]:
                offers.append({
                    "title": entry.title,
                    "link": entry.link
                })
        except Exception as e:
            print(f"Errore lettura feed {feed_url}: {e}")
        time.sleep(1)
    return offers[:limit]


def send_telegram_message(text: str):
    """Invia messaggio Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False}
    r = requests.post(url, data=payload)
    if r.status_code != 200:
        raise RuntimeError(f"Errore Telegram: {r.text}")


def main():
    try:
        offers = get_rss_offers(limit=5)
        if not offers:
            send_telegram_message("⚠️ Nessuna offerta trovata nei feed RSS.")
            return

        msg = f"<b>🔥 Ultime offerte Amazon dai feed</b>\nAggiornato: {datetime.now().strftime('%H:%M %d/%m/%Y')}\n\n"
        for o in offers:
            msg += f"🛒 <a href='{o['link']}'>{o['title']}</a>\n\n"

        send_telegram_message(msg)

    except Exception as e:
        send_telegram_message(f"⚠️ Errore durante l'aggiornamento: {e}")


if __name__ == "__main__":
    main()
