import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
from ftplib import FTP

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH")

CACHE_FILE = "bot/last_offers.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
}


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


def scrape_amazon_offers(limit=10):
    """Estrae offerte reali da Amazon.it/offerte."""
    url = "https://www.amazon.it/gp/goldbox"
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    offers = []
    for div in soup.select("div.a-section.a-spacing-none.gbh1-row"):
        title_el = div.select_one("span.a-size-base.a-color-base")
        link_el = div.select_one("a.a-link-normal")
        if not title_el or not link_el:
            continue
        title = title_el.text.strip()
        link = "https://www.amazon.it" + link_el.get("href")
        offers.append({"title": title, "link": link})
        if len(offers) >= limit:
            break
    return offers


def send_telegram_message(text, buttons=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    if buttons:
        payload["reply_markup"] = json.dumps({"inline_keyboard": buttons})
    requests.post(url, data=payload)


def fetch_homepage():
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    lines = []
    ftp.retrlines(f"RETR {FTP_PATH}", lines.append)
    ftp.quit()
    return "\n".join(lines)


def upload_homepage(content):
    ftp = FTP(FTP_HOST)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.storbinary(f"STOR {FTP_PATH}", content.encode("utf-8"))
    ftp.quit()


def inject_offers_into_html(original_html, offers):
    start_tag = "<!-- OFFERTE_START -->"
    end_tag = "<!-- OFFERTE_END -->"
    start = original_html.find(start_tag)
    end = original_html.find(end_tag)

    if start == -1 or end == -1:
        raise ValueError("Tag OFFERTE_START o OFFERTE_END mancanti nella homepage.")

    offers_html = f"\n<h2>🔥 Offerte Amazon (aggiornate {datetime.now().strftime('%H:%M %d/%m/%Y')})</h2>\n"
    for o in offers:
        offers_html += f"<div class='offer'><a href='{o['link']}' target='_blank'>{o['title']}</a></div>\n"

    return original_html[:start + len(start_tag)] + offers_html + original_html[end:]


def main():
    offers = scrape_amazon_offers(limit=10)
    if not offers:
        send_telegram_message("⚠️ Nessuna offerta trovata su Amazon.")
        return

    cache = load_cache()
    new_offers = [o for o in offers if o["link"] not in cache]
    cache.extend([o["link"] for o in new_offers])
    cache = cache[-100:]
    save_cache(cache)

    try:
        html = fetch_homepage()
        updated_html = inject_offers_into_html(html, offers)
        upload_homepage(updated_html)

        buttons = [
            [{"text": "🌐 Vai al sito TechAndMore.eu", "url": "https://www.techandmore.eu"}],
            [{"text": "🔔 Iscriviti al canale Telegram", "url": "https://t.me/techandmore"}],
        ]
        msg = "<b>🔥 Homepage aggiornata con offerte reali Amazon!</b>"
        send_telegram_message(msg, buttons)

    except Exception as e:
        send_telegram_message(f"❌ Errore aggiornamento homepage: {e}")


if __name__ == "__main__":
    main()
