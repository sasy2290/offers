import os
import re
import json
import asyncio
import ftplib
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import AuthKeyDuplicatedError, SessionRevokedError
import requests


# ======================================================
# CONFIG
# ======================================================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("TELETHON_SESSION", "")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "techandmor03f-21")

FACEBOOK_PAGE_ID = os.getenv("FB_PAGE_ID")
FACEBOOK_TOKEN = os.getenv("FB_PAGE_TOKEN")

FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH")

TARGET_CHANNEL = "@amazontechandmore"

LATEST_JSON = "latest_offers.json"
SITE_DIR = "site"


SOURCE_CHANNELS = [
    "SoloOfferteECodiciSconto",
    "offertebenesseretop",
    "offerte24hgruppo",
    "DottSconto",
    "offertepaz",
    "ilmondodelrisparmio",
    "LeoffertedelGiorno",
    "mondodiofferte",
    "giga_offertee",
    "codici_sconto_sconti",
    "modascontata",
    "super_promo_it",
    "prezzitech",
    "ScontiClubOfficial",
    "prezzoTagliatoModa",
    "offertesmartworld",
    "affarefattoamz",
    "offerteabbigliamento",
    "prezzaccitech",
    "Homezoneit",
    "offerteinformatiche",
    "ScontologyErrori",
]


# ======================================================
# UTILITY
# ======================================================

def replace_affiliate_tag(url):
    if "amazon." not in url:
        return url
    if "tag=" in url:
        return re.sub(r'tag=[^&]+', f'tag={AFFILIATE_TAG}', url)
    sep = "&" if "?" in url else "?"
    return url + f"{sep}tag={AFFILIATE_TAG}"


def extract_offer(text):
    urls = re.findall(r'https?://[^\s)]+', text)
    amazon = next((replace_affiliate_tag(u) for u in urls if "amazon." in u), None)

    price_match = re.search(r"(\d+[,.]?\d*)\s?€", text)
    price = price_match.group(1).replace(",", ".") + " €" if price_match else ""

    title_raw = re.sub(r'https?://[^\s)]+', '', text).strip()
    title = title_raw.split("\n")[0][:120] if title_raw else "Offerta Amazon"

    return {
        "title": title,
        "url": amazon or "",
        "price": price,
        "image": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg"
    }


# ======================================================
# FACEBOOK POSTER
# ======================================================

def post_to_facebook(message):
    url = f"https://graph.facebook.com/v19.0/{FACEBOOK_PAGE_ID}/feed"

    payload = {
        "message": message,
        "access_token": FACEBOOK_TOKEN
    }

    try:
        r = requests.post(url, data=payload)
        print("📘 Facebook:", r.status_code, r.text)
    except Exception as e:
        print("❌ Errore Facebook:", e)


# ======================================================
# HTML GENERATOR
# ======================================================

def generate_html(offers):
    os.makedirs(f"{SITE_DIR}/updates", exist_ok=True)

    cards = ""
    for o in offers:
        cards += f"""
        <div class='offer'>
            <h3>{o['title']}</h3>
            <p>{o['price']}</p>
            <a href="{o['url']}" target="_blank">Vai all'offerta</a>
        </div>
        """

    html = f"""
    <html><body>
    <h1>🔥 Ultime Offerte Amazon</h1>
    {cards}
    </body></html>
    """

    with open(f"{SITE_DIR}/index.html", "w", encoding="utf-8") as f:
        f.write(html)

    update_name = f"update_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    with open(f"{SITE_DIR}/updates/{update_name}", "w", encoding="utf-8") as f:
        f.write(html)

    return update_name


# ======================================================
# FTPS UPLOADER
# ======================================================

def upload_site(update_file):
    ftp = ftplib.FTP_TLS()
    ftp.connect(FTP_HOST, 21)
    ftp.login(FTP_USER, FTP_PASS)
    ftp.prot_p()

    ftp.cwd(FTP_PATH)
    print("📂 Connected to FTP")

    # Upload homepage
    with open(f"{SITE_DIR}/index.html", "rb") as f:
        ftp.storbinary("STOR index.html", f)

    # Upload update page
    with open(f"{SITE_DIR}/updates/{update_file}", "rb") as f:
        ftp.storbinary(f"STOR updates/{update_file}", f)

    ftp.quit()
    print("🚀 Sito aggiornato!")


# ======================================================
# TELEGRAM SCRAPER
# ======================================================

async def run_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()

    offers = []

    print("🔍 Cerco offerte...")

    for ch in SOURCE_CHANNELS:
        try:
            entity = await client.get_entity(ch)
            messages = await client.get_messages(entity, limit=10)

            for msg in messages:
                if not msg.message or "amazon." not in msg.message.lower():
                    continue

                data = extract_offer(msg.message)
                if not data["url"]:
                    continue

                offers.append(data)

                # Telegram publish
                await client.send_message(
                    TARGET_CHANNEL,
                    f"{data['title']}\n{data['price']}\n{data['url']}"
                )

                # Facebook publish
                post_to_facebook(
                    f"{data['title']}\n{data['price']}\n{data['url']}"
                )

        except Exception as e:
            print(f"⚠️ Errore su {ch}: {e}")

    await client.disconnect()

    with open(LATEST_JSON, "w", encoding="utf-8") as f:
        json.dump(offers[:20], f, ensure_ascii=False, indent=2)

    print("💾 Salvate ultime offerte.")

    return offers


# ======================================================
# MAIN (UNIFICA TUTTO)
# ======================================================

async def main():
    try:
        offers = await run_scraper()
        update_page = generate_html(offers)
        upload_site(update_page)
        print("🎉 COMPLETATO")

    except Exception as e:
        print("❌ ERRORE FATALE:", e)


if __name__ == "__main__":
    asyncio.run(main())
