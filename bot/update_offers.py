import os
import requests
import feedparser
from datetime import datetime
import time
import json

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise ValueError("Mancano TELEGRAM_TOKEN o CHAT_ID nei Secrets GitHub.")

# === Lista ampliata di feed con offerte Amazon ===
FEEDS = [
    "https://www.offerteshock.it/feed/",
    "https://www.kechiusa.it/offerte-amazon/feed/",
    "https://www.prezzi.tech/feed/",
    "https://www.prezzipazzi.com/feed/",
    "https://www.offertepertutti.it/feed/",
    "https://www.scontodelgiorno.it/feed/"
]

# === File per la cache dei link già inviati ===
CACHE_FILE = "bot/last_offers.json"


def load_cache():
    """Carica la lista delle offerte già pubblicate."""
    if not os.path.exists(CACHE_FILE):
        return []
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_cache(cache):
    """Salva la lista aggiornata delle offerte pubblicate."""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def get_rss_offers(limit=10):
    """Legge i feed RSS, filtra solo link Amazon e restituisce nuove offerte."""
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
            print(f"Errore lettura feed {feed_url}: {e}")
        time.sleep(1)
        if len(offers) >= limit:
            break
    return offers[:limit]


def send_telegram_message(text: str):
    """Invia un messaggio Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    r = requests.post(url, data=payload)
    if r.status_code != 200:
        raise RuntimeError(f"Errore Telegram: {r.text}")


def main():
    cache = load_cache()
    new_offers = []
    offers = get_rss_offers(limit=10)

    for o in offers:
        if o["link"] not in cache:
            new_offers.append(o)
            cache.append(o["link"])

    # Mantieni la cache con massimo 100 link
    cache = cache[-100:]
    save_cache(cache)

    if not new_offers:
        send_telegram_message("⏳ Nessuna nuova offerta Amazon trovata nei feed RSS.")
        return

    msg = f"<b>🔥 Nuove offerte Amazon</b>\nAggiornato: {datetime.now().strftime('%H:%M %d/%m/%Y')}\n\n"
    for o in new_offers:
        msg += f"🛒 <a href='{o['link']}'>{o['title']}</a>\n\n"

    send_telegram_message(msg)


if __name__ == "__main__":
    main()
