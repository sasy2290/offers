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

# Feed RSS di siti che pubblicano offerte Amazon
FEEDS = [
    "https://www.offerteshock.it/feed/",
    "https://www.kechiusa.it/offerte-amazon/feed/",
    "https://www.prezzi.tech/feed/",
    "https://www.prezzipazzi.com/feed/",
    "https://www.offertepertutti.it/feed/",
    "https://www.scontodelgiorno.it/feed/"
]

CACHE_FILE = "bot/last_offers.json"
HTML_FILE = "bot/offerte.html"


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
            print(f"Errore lettura feed {feed_url}: {e}")
        time.sleep(1)
        if len(offers) >= limit:
            break
    return offers[:limit]


def send_telegram_message(text: str):
    """Invia un messaggio Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False}
    r = requests.post(url, data=payload)
    if r.status_code != 200:
        raise RuntimeError(f"Errore Telegram: {r.text}")


def generate_html(offers):
    """Genera il file offerte.html con le ultime offerte Amazon."""
    html = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Offerte Amazon - TechAndMore</title>
<style>
body {font-family: Arial, sans-serif; background:#fafafa; color:#111; margin:40px;}
a {color:#0073bb; text-decoration:none;}
.offer {background:white; padding:15px; margin:10px 0; border-radius:10px; box-shadow:0 1px 3px rgba(0,0,0,0.1);}
h2 {color:#222;}
</style>
</head>
<body>
<h2>🔥 Ultime offerte Amazon (aggiornate {time})</h2>
""".format(time=datetime.now().strftime("%H:%M %d/%m/%Y"))

    for o in offers:
        html += f"<div class='offer'><a href='{o['link']}' target='_blank'>{o['title']}</a></div>\n"

    html += "</body></html>"
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    cache = load_cache()
    new_offers = []
    offers = get_rss_offers(limit=10)

    for o in offers:
        if o["link"] not in cache:
            new_offers.append(o)
            cache.append(o["link"])

    cache = cache[-100:]
    save_cache(cache)

    if not new_offers:
        send_telegram_message("⏳ Nessuna nuova offerta Amazon trovata.")
        return

    msg = f"<b>🔥 Nuove offerte Amazon</b>\nAggiornato: {datetime.now().strftime('%H:%M %d/%m/%Y')}\n\n"
    for o in new_offers:
        msg += f"🛒 <a href='{o['link']}'>{o['title']}</a>\n\n"

    send_telegram_message(msg)
    generate_html(new_offers)


if __name__ == "__main__":
    main()
