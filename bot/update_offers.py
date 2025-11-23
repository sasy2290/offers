import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
from ftplib import FTP

# === CONFIG ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH")

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")   # Facebook
PAGE_ID = os.getenv("PAGE_ID")                       # Facebook

CACHE_FILE = "bot/last_offers.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


# ============================================================
#                       FACEBOOK API
# ============================================================

def publish_to_facebook(message, image_url=None):
    if not PAGE_ID or not PAGE_ACCESS_TOKEN:
        print("❌ Facebook non configurato")
        return

    if image_url:
        url = f"https://graph.facebook.com/{PAGE_ID}/photos"
        payload = {
            "caption": message,
            "url": image_url,
            "access_token": PAGE_ACCESS_TOKEN
        }
    else:
        url = f"https://graph.facebook.com/{PAGE_ID}/feed"
        payload = {
            "message": message,
            "access_token": PAGE_ACCESS_TOKEN
        }

    r = requests.post(url, data=payload)
    try:
        print("📘 Facebook:", r.json())
    except:
        print("📘 Facebook: inviato")


# ============================================================
#                     CACHE OFFERTE
# ============================================================

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


# ============================================================
#                    SCRAPER AMAZON
# ============================================================

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

        if not title_el or not link_el:
            continue

        title = title_el.text.strip()
        link = "https://www.amazon.it" + link_el.get("href").split("?")[0]
        price = price_el.text.strip() + " €" if price_el else "—"
        img = img_el["src"] if img_el else ""

        offers.append({
            "title": title,
            "link": link,
            "price": price,
            "img": img
        })

        if len(offers) >= limit:
            break

    return offers


# ============================================================
#                TELEGRAM API
# ============================================================

def send_telegram_message(text, buttons=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }

    if buttons:
        payload["reply_markup"] = json.dumps({"inline_keyboard": buttons})

    requests.post(url, data=payload)


# ============================================================
#                    FTP WEBSITE UPDATE
# ============================================================

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
        raise ValueError("Homepage senza tag OFFERTE_START / OFFERTE_END")

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


# ============================================================
#                        MAIN
# ============================================================

def main():
    offers = scrape_amazon_offers(limit=10)

    if not offers:
        send_telegram_message("⚠️ Nessuna offerta trovata su Amazon.")
        return

    # CACHE
    cache = load_cache()
    new_offers = [o for o in offers if o["link"] not in cache]
    cache.extend([o["link"] for o in new_offers])
    cache = cache[-100:]
    save_cache(cache)

    # UPDATE WEBSITE
    try:
        html = fetch_homepage()
        updated_html = inject_offers_into_html(html, offers)
        upload_homepage(updated_html)
    except Exception as e:
        send_telegram_message(f"❌ Errore aggiornamento homepage: {e}")

    # MESSAGE FOR TELEGRAM
    msg = "<b>🔥 Nuove offerte Amazon!</b>\n\n"
    for o in offers[:3]:
        msg += f"🛒 <a href='{o['link']}'>{o['title']}</a>\n💰 {o['price']}\n\n"
    msg += "🌐 <b>Scopri tutte le offerte su TechAndMore.eu</b>"

    buttons = [
        [{"text": "🌐 Vai al sito TechAndMore.eu", "url": "https://www.techandmore.eu"}],
        [{"text": "🔔 Iscriviti al canale Telegram", "url": "https://t.me/techandmore"}]
    ]

    send_telegram_message(msg, buttons)

    # === FACEBOOK POST ===
    try:
        fb_text = "🔥 NUOVE OFFERTE AMAZON!\n\n"
        for o in offers[:3]:
            fb_text += f"{o['title']}\n{o['price']}\n{o['link']}\n\n"

        publish_to_facebook(fb_text, offers[0]['img'])

    except Exception as e:
        print("❌ Errore pubblicazione Facebook:", e)


if __name__ == "__main__":
    main()
