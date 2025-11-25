import os
import re
import json
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import AuthKeyDuplicatedError, SessionRevokedError
import requests
from datetime import datetime
from ftplib import FTP_TLS

# ========================
# CONFIGURAZIONE TELEGRAM
# ========================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("TELETHON_SESSION")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "techandmor03f-21")

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

TARGET_CHANNEL = "@amazontechandmore"

CACHE_FILE = "bot/posted_cache.json"
LATEST_JSON = "bot/latest_offers.json"

# ========================
# CONFIG FACEBOOK
# ========================
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN")

FB_URL = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/feed"


# ========================
# CALCOLO & NORMALIZZAZIONE
# ========================
def normalize(text):
    text = re.sub(r"\s+", " ", text.lower().strip())
    text = re.sub(r"http\S+", "", text)
    return text


def replace_tag(url):
    if "amazon." not in url:
        return url
    if "tag=" in url:
        return re.sub(r'tag=[^&]+', f'tag={AFFILIATE_TAG}', url)
    sep = "&" if "?" in url else "?"
    return url + sep + "tag=" + AFFILIATE_TAG


def extract_offer(text):
    urls = re.findall(r'https?://[^\s)]+', text)
    amazon = next((replace_tag(u) for u in urls if "amazon." in u), None)

    price_match = re.search(r"(\d+[,.]?\d*)\s?€", text)
    price = price_match.group(1).replace(",", ".") + " €" if price_match else ""

    title_raw = re.sub(r'https?://[^\s)]+', "", text).strip()
    title = title_raw.split("\n")[0][:120]

    return {
        "title": title or "Offerta Amazon",
        "url": amazon or "https://www.amazon.it/",
        "price": price or "",
        "image": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg"
    }


# ========================
# PUBBLICA UNICO POST FB
# ========================
def publish_facebook_multi(offers):
    if not offers:
        print("ℹ️ Nessuna offerta da pubblicare su Facebook")
        return

    text = "🔥 Ultime offerte Amazon\n\n"
    for o in offers[:10]:  # max 10 offerte per evitare limite caratteri
        text += f"• {o['title']} – {o['price']}\n{o['url']}\n\n"

    data = {
        "message": text,
        "access_token": FB_PAGE_TOKEN
    }

    print("📘 Pubblico unico post Facebook...")

    r = requests.post(FB_URL, data=data)
    try:
        res = r.json()
    except:
        res = r.text

    print("Facebook:", res)


# ========================
# SCRAPER TELEGRAM
# ========================
async def run_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()

    cache = {"ids": [], "texts": []}
    if os.path.exists(CACHE_FILE):
        cache = json.load(open(CACHE_FILE, "r", encoding="utf-8"))

    offers = []
    new_posts = 0

    for ch in SOURCE_CHANNELS:
        try:
            entity = await client.get_entity(ch)
            messages = await client.get_messages(entity, limit=8)

            for msg in messages:
                if not msg.message or "amazon." not in msg.message.lower():
                    continue

                norm = normalize(msg.message)

                if msg.id in cache["ids"] or norm in cache["texts"]:
                    continue

                # PUBBLICA SU TELEGRAM
                processed = re.sub(
                    r'https?://[^\s)]+',
                    lambda m: replace_tag(m.group(0)),
                    msg.message
                )

                await client.send_message(TARGET_CHANNEL, processed)

                # AGGIUNGI OFFERTA ALLA LISTA
                offers.append(extract_offer(msg.message))

                # AGGIORNA CACHE
                cache["ids"].append(msg.id)
                cache["texts"].append(norm)
                new_posts += 1

        except Exception as e:
            print(f"⚠️ Errore canale {ch}: {e}")

    # salva cache
    json.dump(cache, open(CACHE_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    # salva json offerte
    if offers:
        json.dump(offers, open(LATEST_JSON, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    await client.disconnect()

    return offers, new_posts


# ========================
# U P L O A D   F T P S
# ========================
def upload_site():
    HOST = os.getenv("FTP_HOST")
    USER = os.getenv("FTP_USER")
    PASS = os.getenv("FTP_PASS")
    PATH = os.getenv("FTP_PATH").strip("/")

    ftps = FTP_TLS(HOST)
    ftps.login(USER, PASS)
    ftps.prot_p()
    ftps.cwd("/" + PATH)

    # carica index.html
    if os.path.exists("index.html"):
        with open("index.html", "rb") as f:
            ftps.storbinary("STOR index.html", f)

    # carica JSON
    with open(LATEST_JSON, "rb") as f:
        ftps.storbinary("STOR latest_offers.json", f)

    ftps.quit()
    print("🌐 Sito aggiornato!")


# ========================
# MAIN
# ========================
async def main():
    try:
        offers, count = await run_scraper()
        print(f"📊 Nuove offerte trovate: {count}")

        # unico post Facebook
        publish_facebook_multi(offers)

        upload_site()

        print("✅ FULL AUTOMATION COMPLETATA")

    except Exception as e:
        print(f"❌ Errore: {e}")


if __name__ == "__main__":
    asyncio.run(main())
