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

def get_amazon_best_sellers(category_url: str, limit: int = 5):
    res = requests.get(category_url, headers=HEADERS, timeout=15)
    if res.status_code != 200:
        raise RuntimeError(f"Errore HTTP {res.status_code} su {category_url}")

    soup = BeautifulSoup(res.text, "html.parser")
    items = []

    for i, item in enumerate(soup.select("div.zg-grid-general-faceout"), start=1):
        title = item.select_one("div.p13n-sc-truncated, span.a-text-normal, div._cDEzb_p13n-sc-css-line-clamp-3_g3dy1")
        price = item.select_one("span.p13n-sc-price, span.a-color-price")
        title = title.get_text(strip=True) if title else "Titolo non trovato"
        price = price.get_text(strip=True) if price else "N/D"
        items.append({"rank": i, "title": title, "price": price})
        if i >= limit:
            break
    return items

def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    r = requests.post(url, data=payload)
    if r.status_code != 200:
        raise RuntimeError(f"Errore Telegram: {r.text}")

def main():
    categories = {
        "Elettronica": "https://www.amazon.it/gp/bestsellers/electronics",
        "Libri": "https://www.amazon.it/gp/bestsellers/books",
        "Casa": "https://www.amazon.it/gp/bestsellers/home",
    }

    for category, url in categories.items():
        try:
            items = get_amazon_best_sellers(url)
            msg = f"<b>📦 Best Seller Amazon - {category}</b>\nAggiornato: {datetime.now().strftime('%H:%M %d/%m/%Y')}\n\n"
            for i in items:
                msg += f"{i['rank']}. {i['title']} — {i['price']}\n"
            send_telegram_message(msg)
            time.sleep(2)
        except Exception as e:
            send_telegram_message(f"⚠️ Errore su {category}: {e}")

if __name__ == "__main__":
    main()
