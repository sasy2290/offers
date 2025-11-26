import os
import re
import json
import asyncio
from ftplib import FTP_TLS

import requests
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import AuthKeyDuplicatedError, SessionRevokedError

# ========================
# CONFIG
# ========================

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("TELETHON_SESSION")
SCRAPER_KEY = os.getenv("SCRAPER_KEY")  # API per immagine Amazon

AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "techandmor03f-21")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = (os.getenv("FTP_PATH") or "").strip("/")
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://techandmore.eu")

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN")

FB_FEED_URL = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/feed"
FB_PHOTOS_URL = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"

CACHE_FILE = "bot/posted_cache.json"
LATEST_JSON = "bot/latest_offers.json"

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


# ========================
# UTILS
# ========================

def normalize(text: str) -> str:
    text = re.sub(r"\s+", " ", text.lower().strip())
    text = re.sub(r"http\S+", "", text)
    return text


def replace_tag(url: str) -> str:
    if "amazon." not in url:
        return url
    if "tag=" in url:
        return re.sub(r"tag=[^&]+", f"tag={AFFILIATE_TAG}", url)
    return url + ("&" if "?" in url else "?") + f"tag={AFFILIATE_TAG}"


def extract_offer(text: str) -> dict:
    urls = re.findall(r"https?://[^\s)]+", text)
    amazon = next((replace_tag(u) for u in urls if "amazon." in u), None)

    price_match = re.search(r"(\d+[,.]?\d*)\s?€", text)
    price = price_match.group(1).replace(",", ".") + " €" if price_match else ""

    title_raw = re.sub(r"https?://[^\s)]+", "", text).strip()
    title = title_raw.split("\n")[0][:120] if title_raw else "Offerta Amazon"

    return {
        "title": title,
        "url": amazon or "https://www.amazon.it/",
        "price": price,
        "image": None,
    }


# ========================
# IMMAGINE AMAZON (fallback)
# ========================

def get_amazon_image(url: str):
    if not url or not SCRAPER_KEY:
        return None

    api_url = (
        f"https://api.scraperapi.com/"
        f"?api_key={SCRAPER_KEY}"
        f"&url={url}"
        f"&autoparse=true"
    )

    try:
        r = requests.get(api_url, timeout=20)
        data = r.json()

        if "primaryImage" in data:
            return data["primaryImage"]

        if "images" in data and len(data["images"]) > 0:
            return data["images"][0]

    except Exception as e:
        print("⚠️ Errore immagine Amazon:", e)

    return None


# ========================
# SCARICA FOTO TELEGRAM
# ========================

async def download_telegram_photo(client, msg, save_path):
    if not msg.photo:
        return None
    try:
        await client.download_media(msg, file=save_path)
        return save_path
    except:
        return None


# ========================
# UPLOAD IMG SU FTP
# ========================

def upload_image_to_ftp(local_path, remote_filename):
    if not local_path:
        return None
    try:
        ftps = FTP_TLS(FTP_HOST)
        ftps.login(FTP_USER, FTP_PASS)
        ftps.prot_p()

        target = f"/{FTP_PATH}/img".rstrip("/")

        # crea /img se non esiste
        try:
            ftps.cwd(target)
        except:
            try:
                ftps.mkd(target)
            except:
                pass
            ftps.cwd(target)

        with open(local_path, "rb") as f:
            ftps.storbinary(f"STOR {remote_filename}", f)

        ftps.quit()
        return f"{SITE_BASE_URL}/img/{remote_filename}"

    except Exception as e:
        print("⚠️ Errore upload immagine FTP:", e)
        return None


# ========================
# FACEBOOK POST
# ========================

def publish_facebook_multi(offers):
    if not offers:
        print("ℹ️ Nessuna offerta da pubblicare su Facebook (lista vuota).")
        return

    print(f"📡 Invio a Facebook {len(offers)} offerte (max 10 nel testo)...")

    text = "🔥 Ultime offerte Amazon\n\n"
    for o in offers[:10]:
        text += f"• {o['title']} – {o['price']}\n{o['url']}\n\n"

    image_offer = next((o for o in offers if o.get("image_file")), None)

    try:
        if not image_offer:
            print("ℹ️ Nessuna immagine locale, pubblico SOLO testo su Facebook...")
            r = requests.post(
                FB_FEED_URL,
                data={
                    "message": text,
                    "access_token": FB_PAGE_TOKEN,
                },
                timeout=30,
            )
        else:
            print(f"🖼 Pubblico su Facebook con immagine: {image_offer['image_file']}")
            files = {"source": open(image_offer["image_file"], "rb")}
            data = {
                "caption": text,
                "access_token": FB_PAGE_TOKEN,
            }
            r = requests.post(
                FB_PHOTOS_URL,
                data=data,
                files=files,
                timeout=60,
            )

        # Log risposta Facebook
        try:
            print("📨 Risposta Facebook:", r.status_code, r.text)
        except Exception as e:
            print("⚠️ Errore leggendo risposta Facebook:", e)

    except Exception as e:
        print("❌ Errore chiamata Facebook:", e)



# ========================
# SCRAPER TELEGRAM
# ========================

async def run_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()

    cache = {"ids": [], "texts": []}
    if os.path.exists(CACHE_FILE):
        try:
            cache = json.load(open(CACHE_FILE, "r"))
        except:
            cache = {"ids": [], "texts": []}

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

                processed = re.sub(
                    r"https?://[^\s)]+",
                    lambda m: replace_tag(m.group(0)),
                    msg.message,
                )

                await client.send_message(TARGET_CHANNEL, processed)

                offer = extract_offer(msg.message)

                # 1️⃣ scarica immagine Telegram
                local = await download_telegram_photo(
                    client,
                    msg,
                    f"bot/tmp_{msg.id}.jpg",
                )

                # 2️⃣ fallback immagine Amazon
                if not local:
                    amazon_img = get_amazon_image(offer["url"])
                    if amazon_img:
                        try:
                            img_data = requests.get(amazon_img).content
                            local = f"bot/tmp_{msg.id}.jpg"
                            open(local, "wb").write(img_data)
                        except:
                            pass

                # 3️⃣ upload via FTP
                if local:
                    remote_filename = f"offer_{msg.id}.jpg"
                    image_url = upload_image_to_ftp(local, remote_filename)
                    if image_url:
                        offer["image"] = image_url
                else:
                    offer["image"] = (
                        "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg"
                    )

                offer["image_file"] = local
                offers.append(offer)

                cache["ids"].append(msg.id)
                cache["texts"].append(norm)
                new_posts += 1

        except Exception as e:
            print("⚠️ Errore:", e)

    json.dump(cache, open(CACHE_FILE, "w"), indent=2)

    if offers:
        json.dump(offers, open(LATEST_JSON, "w"), indent=2)

    await client.disconnect()
    return offers, new_posts


# ========================
# UPLOAD JSON
# ========================

def upload_site():
    ftps = FTP_TLS(FTP_HOST)
    ftps.login(FTP_USER, FTP_PASS)
    ftps.prot_p()

    target = f"/{FTP_PATH}".rstrip("/")
    ftps.cwd(target)

    with open(LATEST_JSON, "rb") as f:
        ftps.storbinary("STOR latest_offers.json", f)

    ftps.quit()


# ========================
# MAIN
# ========================

async def main():
    offers, count = await run_scraper()
    print(f"📊 Nuove offerte trovate dallo scraper: {count}")
    print(f"📦 Offerte totali passate a Facebook: {len(offers)}")

    publish_facebook_multi(offers)
    upload_site()
    print("✅ FULL AUTOMATION COMPLETATA")



if __name__ == "__main__":
    asyncio.run(main())
