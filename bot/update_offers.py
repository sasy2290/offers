# update_offers.py UPDATED WITH FACEBOOK SUPPORT
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

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PAGE_ID = os.getenv("PAGE_ID")

CACHE_FILE = "bot/last_offers.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def publish_to_facebook(message, image_url=None):
    if not PAGE_ACCESS_TOKEN or not PAGE_ID:
        print("Facebook non configurato.")
        return

    fb_url = f"https://graph.facebook.com/{PAGE_ID}/feed"
    payload = {
        "message": message,
        "access_token": PAGE_ACCESS_TOKEN
    }

    if image_url:
        fb_url = f"https://graph.facebook.com/{PAGE_ID}/photos"
        payload["url"] = image_url

    r = requests.post(fb_url, data=payload)
    try:
        print("Facebook response:", r.json())
    except:
        print("Facebook post inviato.")

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return []
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def scrape_amazon_offers(limit=10):
    url = "https://www.amazon.it/gp/goldbox"
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    offers = []
    for div in soup.select("div.DealCard-module__content__2mibk"):
        title_el = div.select_one("span.DealCard-module__truncateText__1GKy2")
        link_el = div.select_one("a.a-link-normal")
        price_el = div.select_one("span.a-price-whole")
        img_el = div.select_one("img")
        if not link_el or not title_el:
            continue
        title = title_el.text.strip()
        link = "https://www.amazon.it" + link_el.get("href").split("?")[0]
        price = price_el.text.strip() + " €" if price_el else "—"
        img = img_el["src"] if img_el else ""
        offers.append({"title": title, "link": link, "price": price, "img": img})
        if len(offers) >= limit:
            break
    return offers

def send_telegram_message(text, buttons=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
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
    offers_html = f"\n<h2>🔥 Offerte Amazon (aggiornate {datetime.now().strftime('%H:%M %d/%m/%Y')})</h2>\n"
    for o in offers:
        offers_html += f"""
        <div class='offer'>
            <a href='{o['link']}' target='_blank'>
                <img src='{o['img']}' alt='{o['title']}' style='max-width:150px; float:left; margin-right:15px; border-radius:8px;'>
                <strong>{o['title']}</strong><br>
                <span style='color:#00bfff; font-weight:bold;'>{o['price']}</span>
            </a>
            <div style='clear:both;'></div>
        </div>
        """
    return original_html[:start + len(start_tag)] + offers_html + original_html[end:]

def main():
    offers = scrape_amazon_offers(limit=10)
    cache = load_cache()
    new_offers = [o for o in offers if o["link"] not in cache]
    cache.extend([o["link"] for o in new_offers])
    cache = cache[-100:]
    save_cache(cache)
    html = fetch_homepage()
    updated_html = inject_offers_into_html(html, offers)
    upload_homepage(updated_html)

    msg = "<b>🔥 Nuove offerte Amazon!</b>\n\n"
    for o in offers[:3]:
        msg += f"🛒 <a href='{o['link']}'>{o['title']}</a>\n💰 {o['price']}\n\n"
    msg += "🌐 <b>Scopri tutte le offerte su TechAndMore.eu</b>"

    buttons = [
        [{"text": "🌐 Vai al sito", "url": "https://www.techandmore.eu"}],
        [{"text": "🔔 Telegram", "url": "https://t.me/amazontechandmore"}],
    ]
    send_telegram_message(msg, buttons)

    fb_message = "🔥 NUOVE OFFERTE AMAZON!\n\n"
    for o in offers[:3]:
        fb_message += f"{o['title']}\n{o['price']}\n{o['link']}\n\n"
    publish_to_facebook(fb_message)

if __name__ == "__main__":
    main()
