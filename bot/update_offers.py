import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise ValueError("Mancano TELEGRAM_TOKEN o CHAT_ID nei Secrets del repository GitHub.")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9",
}

def get_amazon_offers(limit: int = 5):
    """Estrae le offerte attuali da amazon.it/gp/goldbox"""
    url = "https://www.amazon.it/gp/goldbox"
    res = requests.get(url, headers=HEADERS, timeout=15)
    if res.status_code != 200:
        raise RuntimeError(f"Errore HTTP {res.status_code} su {url}")

    soup = BeautifulSoup(res.text, "html.parser")
    offers = []

    # Selettori aggiornati per le offerte
    blocks = soup.select("div[data-asin][data-component-type='s-search-result']")

    for i, b in enumerate(blocks, start=1):
        title = b.select_one("h2 a span")
        link = b.select_one("h2 a")
        price = b.select_one("span.a-price span.a-offscreen")
        old_price = b.select_one("span.a-text-price span.a-offscreen")

        if not title or not link:
            continue

        offers.append({
            "rank": i,
            "title": title.get_text(strip=True),
            "url": "https://www.amazon.it" + link["href"].split("?")[0],
            "price": price.get_text(strip=True) if price else "N/D",
            "old_price": old_price.get_text(strip=True) if old_price else None
        })

        if i >= limit:
            break

    return offers


def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    r = requests.post(url, data=payload)
    if r.status_code != 200:
        raise RuntimeError(f"Errore Telegram: {r.text}")


def main():
    try:
        offers = get_amazon_offers(limit=5)
        msg = f"<b>🔥 Offerte Amazon del Giorno</b>\nAggiornato: {datetime.now().strftime('%H:%M %d/%m/%Y')}\n\n"

        for o in offers:
            line = f"🛒 <a href='{o['url']}'>{o['title']}</a>\n💰 {o['price']}"
            if o["old_price"]:
                line += f"  <s>{o['old_price']}</s>"
            msg += line + "\n\n"

        send_telegram_message(msg)
    except Exception as e:
        send_telegram_message(f"⚠️ Errore durante l'aggiornamento: {e}")


if __name__ == "__main__":
    main()
