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
SCRAPER_KEY = os.getenv("SCRAPER_KEY")

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
    try:
        api_url = (
            f"https://api.scraperapi.com/?api_key={SCRAPER_KEY}"
            f"&url={url}&autoparse=true"
        )
        data = requests.get(api_url, timeout=15).json()
        if "primaryImage" in data:
            return data["primaryImage"]
        if "images" in data and len(data["images"]) > 0:
            return data["images"][0]
    except:
        pass
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
    except:
        return None


# ========================
# FACEBOOK POST (1 sola immagine)
# ========================

def publish_facebook_multi(offers):
    if not offers:
        return

    text = "🔥 Ultime offerte Amazon\n\n"
    for o in offers[:10]:
        text += f"• {o['title']} – {o['price']}\n{o['url']}\n\n"

    first_with_image = next((o for o in offers if o.get("image_file")), None)

    # niente immagine → solo testo
    if not first_with_image:
        requests.post(FB_FEED_URL, data={
            "message": text,
            "access_token": FB_PAGE_TOKEN,
        })
        return

    # immagine singola
    files = {"source": open(first_with_image["image_file"], "rb")}
    data = {"caption": text, "access_token": FB_PAGE_TOKEN}

    requests.post(FB_PHOTOS_URL, data=data, files=files)


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
            pass

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

                # 1. Telegram photo
                local = await download_telegram_photo(client, msg, f"bot/tmp_{msg.id}.jpg")

                # 2. Fallback Amazon image
                if not local:
                    amazon_img = get_amazon_image(offer["url"])
                    if amazon_img:
                        try:
                            img = requests.get(amazon_img).content
                            open(f"bot/tmp_{msg.id}.jpg", "wb").write(img)
                            local = f"bot/tmp_{msg.id}.jpg"
                        except:
                            pass

                # 3. upload FTP
                if local:
                    remote = upload_image_to_ftp(local, f"offer_{msg.id}.jpg")
                    if remote:
                        offer["image"] = remote
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
            print("Errore su canale:", e)

    json.dump(cache, open(CACHE_FILE, "w"), indent=2)
    json.dump(offers, open(LATEST_JSON, "w"), indent=2)

    await client.disconnect()
    return offers, new_posts


# ========================
# UPLOAD JSON SITO
# ========================

def upload_site():
    try:
        ftps = FTP_TLS(FTP_HOST)
        ftps.login(FTP_USER, FTP_PASS)
        ftps.prot_p()
        ftps.cwd(f"/{FTP_PATH}")

        with open(LATEST_JSON, "rb") as f:
            ftps.storbinary("STOR latest_offers.json", f)

        ftps.quit()
    except Exception as e:
        print("Errore upload sito:", e)


# ========================
# MAIN
# ========================

async def main():
    offers, count = await run_scraper()
    publish_facebook_multi(offers)
    upload_site()
    print("✅ FULL AUTOMATION COMPLETATA")


if __name__ == "__main__":
    asyncio.run(main())
