import os
import re
import json
import asyncio
from datetime import datetime, timezone
from ftplib import FTP_TLS, error_perm

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

# QUI LA FIX FONDAMENTALE:
FTP_PATH = (os.getenv("FTP_PATH") or "/www.techandmore.eu").rstrip("/")

SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://techandmore.eu")

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN")

FB_FEED_URL = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/feed"
FB_PHOTOS_URL = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"

CACHE_FILE = "bot/posted_cache.json"
LATEST_JSON = "bot/latest_offers.json"
HISTORY_JSON = "bot/history.json"
FEED_FILE = "bot/feed.xml"
SITEMAP_FILE = "bot/sitemap.xml"

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
    title = title_raw.split("\n")[0][:160] if title_raw else "Offerta Amazon"

    return {
        "title": title,
        "url": amazon or "https://www.amazon.it/",
        "price": price,
        "image": None,
    }


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


async def download_telegram_photo(client, msg, save_path):
    if not msg.photo:
        return None
    try:
        await client.download_media(msg, file=save_path)
        return save_path
    except Exception as e:
        print(f"⚠️ Errore download immagine Telegram: {e}")
        return None


# ========================
# FTP HELPERS
# ========================

def open_ftps():
    ftps = FTP_TLS(FTP_HOST)
    ftps.login(FTP_USER, FTP_PASS)
    ftps.prot_p()

    if FTP_PATH:
        try:
            ftps.cwd(FTP_PATH)
        except:
            pass
    return ftps


def upload_file(local_path: str, remote_name: str):
    if not os.path.exists(local_path):
        print(f"⚠️ File non trovato per upload: {local_path}")
        return
    ftps = open_ftps()
    with open(local_path, "rb") as f:
        ftps.storbinary(f"STOR {remote_name}", f)
    ftps.quit()
    print(f"⬆️ Caricato: {remote_name}")


def download_history_from_ftp() -> list:
    try:
        ftps = open_ftps()
        buf = []

        def _collector(chunk):
            buf.append(chunk)

        try:
            ftps.retrbinary("RETR history.json", _collector)
        except error_perm:
            ftps.quit()
            print("ℹ️ Nessun history.json remoto.")
            return []

        ftps.quit()
        return json.loads(b"".join(buf).decode("utf-8"))
    except:
        return []


def upload_image_to_ftp(local_path, remote_filename):
    if not local_path:
        return None
    try:
        ftps = open_ftps()

        # entra in cartella img
        try:
            ftps.cwd("img")
        except:
            try:
                ftps.mkd("img")
                ftps.cwd("img")
            except:
                return None

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
        return

    text = "🔥 Ultime offerte Amazon\n\n"
    for o in offers[:10]:
        text += f"• {o['title']} – {o['price']}\n{o['url']}\n\n"

    img = next((o.get("image_file") for o in offers if o.get("image_file")), None)

    if img:
        files = {"source": open(img, "rb")}
        data = {"caption": text, "access_token": FB_PAGE_TOKEN}
        r = requests.post(FB_PHOTOS_URL, data=data, files=files)
    else:
        r = requests.post(FB_FEED_URL, data={"message": text, "access_token": FB_PAGE_TOKEN})

    print("📌 FB_DEBUG:", r.status_code, r.text)


# ========================
# SCRAPER TELEGRAM
# ========================

async def run_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()

    cache = {"ids": [], "texts": []}
    if os.path.exists(CACHE_FILE):
        try:
            cache = json.load(open(CACHE_FILE, "r", encoding="utf-8"))
        except:
            pass

    offers = []
    print("🔍 Avvio scraper Telegram...")

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

                created_at = datetime.now(timezone.utc).isoformat()
                offer["id"] = f"{entity.id}_{msg.id}"
                offer["created_at"] = created_at

                local = await download_telegram_photo(
                    client,
                    msg,
                    f"bot/tmp_{entity.id}_{msg.id}.jpg",
                )

                if not local:
                    amazon_img = get_amazon_image(offer["url"])
                    if amazon_img:
                        try:
                            img_data = requests.get(amazon_img, timeout=20).content
                            local = f"bot/tmp_{entity.id}_{msg.id}.jpg"
                            open(local, "wb").write(img_data)
                        except:
                            local = None

                if local:
                    remote_filename = f"offer_{entity.id}_{msg.id}.jpg"
                    image_url = upload_image_to_ftp(local, remote_filename)
                    offer["image"] = image_url or None
                else:
                    offer["image"] = None

                offer["image_file"] = local
                offers.append(offer)

                cache["ids"].append(msg.id)
                cache["texts"].append(norm)

        except Exception as e:
            print("⚠️ Errore su canale:", ch, e)

    json.dump(cache, open(CACHE_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    json.dump(offers, open(LATEST_JSON, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    await client.disconnect()
    return offers


# ========================
# STORICO / RSS / SITEMAP
# ========================

def update_history(new):
    history = download_history_from_ftp()

    ids = {o["id"] for o in history}
    added = 0

    for o in new:
        if o["id"] not in ids:
            history.insert(0, o)
            ids.add(o["id"])
            added += 1

    json.dump(history, open(HISTORY_JSON, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"📚 Storico aggiornato: {len(history)} offerte totali (+{added} nuove).")
    return history


def generate_rss(history):
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        "<title>TechAndMore - Ultime offerte Amazon</title>",
        f"<link>{SITE_BASE_URL}</link>",
    ]

    for o in history[:20]:
        parts.append("<item>")
        parts.append(f"<title>{o['title']}</title>")
        parts.append(f"<link>{o['url']}</link>")
        parts.append(f"<guid>{SITE_BASE_URL}/prodotto.html?id={o['id']}</guid>")
        parts.append(f"<pubDate>{o['created_at']}</pubDate>")
        parts.append("</item>")

    parts.append("</channel></rss>")

    open(FEED_FILE, "w", encoding="utf-8").write("\n".join(parts))


def generate_sitemap(history):
    urls = [
        f"{SITE_BASE_URL}/",
        f"{SITE_BASE_URL}/storico.html",
        f"{SITE_BASE_URL}/categorie.html",
        f"{SITE_BASE_URL}/offerte-del-giorno.html",
    ]

    for o in history:
        urls.append(f"{SITE_BASE_URL}/prodotto.html?id={o['id']}")

    today = datetime.now(timezone.utc).date().isoformat()

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for u in urls:
        parts.append("<url>")
        parts.append(f"<loc>{u}</loc>")
        parts.append(f"<lastmod>{today}</lastmod>")
        parts.append("<changefreq>hourly</changefreq>")
        parts.append("<priority>0.8</priority>")
        parts.append("</url>")

    parts.append("</urlset>")

    open(SITEMAP_FILE, "w", encoding="utf-8").write("\n".join(parts))


# ========================
# UPLOAD SITO
# ========================

def upload_site():
    print("🌐 Upload sito via FTPS...")

    upload_file("index.html", "index.html")
    upload_file(LATEST_JSON, "latest_offers.json")
    upload_file(HISTORY_JSON, "history.json")
    upload_file(FEED_FILE, "feed.xml")
    upload_file(SITEMAP_FILE, "sitemap.xml")

    print("🚀 Upload sito completato.")


# ========================
# MAIN
# ========================

async def main():
    try:
        offers = await run_scraper()
        history = update_history(offers)
        generate_rss(history)
        generate_sitemap(history)
        publish_facebook_multi(offers)
        upload_site()
        print("✅ FULL AUTOMATION COMPLETATA")

    except Exception as e:
        print("❌ Errore generale:", e)


if __name__ == "__main__":
    asyncio.run(main())
