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
FTP_PATH = (os.getenv("FTP_PATH") or "").strip("/")

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


# ========================
# TELEGRAM MEDIA
# ========================

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
    base = f"/{FTP_PATH}".rstrip("/")
    if base:
        ftps.cwd(base)
    return ftps


def upload_site():
    print("🌐 Upload sito via FTPS...")

    # Pagine statiche HTML / file statici dalla root del repo
    static_files = [
        ("index.html", "index.html"),
        ("storico.html", "storico.html"),
        ("categorie.html", "categorie.html"),
        ("offerte-del-giorno.html", "offerte-del-giorno.html"),
        ("prodotto.html", "prodotto.html"),
        ("manifest.json", "manifest.json"),
        ("robots.txt", "robots.txt"),
    ]

    for local_path, remote_name in static_files:
        if os.path.exists(local_path):
            upload_file(local_path, remote_name)
        else:
            print(f"ℹ️ File statico non trovato (salto): {local_path}")

    # File generati dallo script (JSON, RSS, sitemap)
    data_files = [
        (LATEST_JSON, "latest_offers.json"),
        (HISTORY_JSON, "history.json"),
        (FEED_FILE, "feed.xml"),
        (SITEMAP_FILE, "sitemap.xml"),
    ]

    for local_path, remote_name in data_files:
        upload_file(local_path, remote_name)

    print("✅ Upload sito completato")



def download_history_from_ftp() -> list:
    """
    Scarica history.json dal server, se esiste.
    """
    try:
        ftps = open_ftps()
        buf = []

        def _collector(chunk):
            buf.append(chunk)

        try:
            ftps.retrbinary("RETR history.json", _collector)
            ftps.quit()
            raw = b"".join(buf).decode("utf-8")
            history = json.loads(raw)
            print(f"📥 Scaricato history.json dal server ({len(history)} offerte).")
            return history
        except error_perm as e:
            # 550 = file not found
            print(f"ℹ️ Nessun history.json remoto (o errore FTP): {e}")
            ftps.quit()
            return []
    except Exception as e:
        print(f"⚠️ Errore download history.json: {e}")
        return []


# ========================
# UPLOAD IMMAGINE SU FTP
# ========================

def upload_image_to_ftp(local_path, remote_filename):
    if not local_path:
        return None
    try:
        ftps = open_ftps()
        # crea /img se non esiste
        try:
            ftps.cwd("img")
        except Exception:
            try:
                ftps.mkd("img")
            except Exception:
                pass
            ftps.cwd("img")

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
        print("ℹ️ Nessuna offerta per Facebook.")
        return

    text = "🔥 Ultime offerte Amazon\n\n"
    for o in offers[:10]:
        text += f"• {o['title']} – {o['price']}\n{o['url']}\n\n"

    # prima offerta con immagine locale per /photos
    image_offer = next((o for o in offers if o.get("image_file")), None)

    if not image_offer:
        print("📌 FB_DEBUG: Nessuna immagine locale, pubblico post testuale.")
        r = requests.post(
            FB_FEED_URL,
            data={
                "message": text,
                "access_token": FB_PAGE_TOKEN,
            },
            timeout=40,
        )
    else:
        print("📌 FB_DEBUG: Pubblico post con immagine.")
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

    try:
        print("📌 FB_DEBUG: Risposta Facebook:", r.status_code, r.text)
    except Exception:
        pass


# ========================
# SCRAPER TELEGRAM
# ========================

async def run_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()

    # cache locale
    cache = {"ids": [], "texts": []}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {"ids": [], "texts": []}

    offers = []
    new_posts = 0

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

                # id univoco: chat_id + msg_id
                created_at = datetime.now(timezone.utc).isoformat()
                offer["id"] = f"{entity.id}_{msg.id}"
                offer["created_at"] = created_at

                # 1) immagine Telegram
                local = await download_telegram_photo(
                    client,
                    msg,
                    f"bot/tmp_{entity.id}_{msg.id}.jpg",
                )

                # 2) fallback immagine Amazon
                if not local:
                    amazon_img = get_amazon_image(offer["url"])
                    if amazon_img:
                        try:
                            img_data = requests.get(amazon_img, timeout=30).content
                            local = f"bot/tmp_{entity.id}_{msg.id}.jpg"
                            with open(local, "wb") as f:
                                f.write(img_data)
                        except Exception as e:
                            print("⚠️ Errore download immagine Amazon:", e)

                # 3) upload FTP
                if local:
                    remote_filename = f"offer_{entity.id}_{msg.id}.jpg"
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
            print(f"⚠️ Errore sul canale {ch}: {e}")

    # salva cache
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Errore salvataggio cache: {e}")

    # salva JSON offerte (solo ultime)
    if offers:
        try:
            with open(LATEST_JSON, "w", encoding="utf-8") as f:
                json.dump(offers, f, ensure_ascii=False, indent=2)
            print(f"💾 Salvate {len(offers)} offerte in {LATEST_JSON}")
        except Exception as e:
            print(f"⚠️ Errore salvataggio JSON offerte: {e}")
    else:
        print("ℹ️ Nessuna nuova offerta trovata.")

    await client.disconnect()
    return offers, new_posts


# ========================
# STORICO / RSS / SITEMAP
# ========================

def update_history(all_new_offers):
    # scarico storico esistente dal server
    history = download_history_from_ftp()

    if not isinstance(history, list):
        history = []

    existing_ids = {o.get("id") for o in history if isinstance(o, dict)}

    # inserisco nuove offerte in testa
    added = 0
    for off in all_new_offers:
        oid = off.get("id")
        if not oid or oid in existing_ids:
            continue
        history.insert(0, off)
        existing_ids.add(oid)
        added += 1

    # opzionale: limito storico a N elementi (es. 5000)
    MAX_ITEMS = 5000
    if len(history) > MAX_ITEMS:
        history = history[:MAX_ITEMS]

    with open(HISTORY_JSON, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    print(f"📚 Storico aggiornato: {len(history)} offerte totali (+{added} nuove).")
    return history


def _xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def generate_rss(history):
    # prendo le ultime 20 offerte
    items = history[:20]

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "<channel>",
        f"<title>{_xml_escape('TechAndMore - Ultime offerte Amazon')}</title>",
        f"<link>{SITE_BASE_URL}</link>",
        "<description>Feed RSS con le ultime offerte pubblicate su TechAndMore.</description>",
        "<language>it-it</language>",
    ]

    for o in items:
        title = _xml_escape(o.get("title", "Offerta Amazon"))
        link = o.get("url") or SITE_BASE_URL
        price = o.get("price", "")
        created = o.get("created_at")
        pubdate = created or datetime.now(timezone.utc).isoformat()
        guid = f"{SITE_BASE_URL}/prodotto.html?id={o.get('id', '')}"

        parts.append("<item>")
        parts.append(f"<title>{title}</title>")
        parts.append(f"<link>{_xml_escape(link)}</link>")
        parts.append(f"<guid>{_xml_escape(guid)}</guid>")
        parts.append(f"<description>{_xml_escape(price)}</description>")
        parts.append(f"<pubDate>{_xml_escape(pubdate)}</pubDate>")
        parts.append("</item>")

    parts.append("</channel>")
    parts.append("</rss>")

    with open(FEED_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))

    print("📰 RSS feed generato.")


def generate_sitemap(history):
    urls = [
        f"{SITE_BASE_URL}/",
        f"{SITE_BASE_URL}/storico.html",
        f"{SITE_BASE_URL}/categorie.html",
        f"{SITE_BASE_URL}/offerte-del-giorno.html",
    ]

    # tutte le schede prodotto
    for o in history:
        oid = o.get("id")
        if not oid:
            continue
        urls.append(f"{SITE_BASE_URL}/prodotto.html?id={oid}")

    now = datetime.now(timezone.utc).date().isoformat()

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for u in urls:
        parts.append("<url>")
        parts.append(f"<loc>{_xml_escape(u)}</loc>")
        parts.append(f"<lastmod>{now}</lastmod>")
        parts.append("<changefreq>hourly</changefreq>")
        parts.append("<priority>0.8</priority>")
        parts.append("</url>")

    parts.append("</urlset>")

    with open(SITEMAP_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))

    print("🗺️ Sitemap generata.")


# ========================
# UPLOAD SITO
# ========================

def upload_site():
    print("🌐 Upload sito via FTPS...")

    # index + latest_offers + history + feed + sitemap
    upload_file("index.html", "index.html")
    upload_file(LATEST_JSON, "latest_offers.json")
    upload_file(HISTORY_JSON, "history.json")
    upload_file(FEED_FILE, "feed.xml")
    upload_file(SITEMAP_FILE, "sitemap.xml")

    print("✅ Upload sito completato")


# ========================
# MAIN
# ========================

async def main():
    try:
        offers, count = await run_scraper()
        print(f"📊 Nuove offerte trovate: {count}")

        # aggiorno storico + RSS + sitemap
        history = update_history(offers if offers else [])
        generate_rss(history)
        generate_sitemap(history)

        # Facebook
        try:
            publish_facebook_multi(offers)
        except Exception as e:
            print(f"⚠️ Errore pubblicazione Facebook: {e}")

        # Upload sito
        try:
            upload_site()
        except Exception as e:
            print(f"⚠️ Errore upload sito: {e}")

        print("✅ FULL AUTOMATION COMPLETATA")

    except (AuthKeyDuplicatedError, SessionRevokedError):
        print("❌ Errore di sessione Telethon: rigenera TELETHON_SESSION")
    except Exception as e:
        print(f"❌ Errore generale: {e}")


if __name__ == "__main__":
    asyncio.run(main())
