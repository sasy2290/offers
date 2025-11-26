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
# CONFIG TELEGRAM
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
FB_FEED_URL = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/feed"
FB_PHOTOS_URL = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"

# ========================
# CONFIG FTP / SITO
# ========================

FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = (os.getenv("FTP_PATH") or "").strip("/")
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://techandmore.eu")  # adatta se serve

# ========================
# UTILS TESTO / OFFERTE
# ========================

def normalize(text: str) -> str:
    text = re.sub(r"\s+", " ", text.lower().strip())
    text = re.sub(r"http\\S+", "", text)
    return text


def replace_tag(url: str) -> str:
    if "amazon." not in url:
        return url
    if "tag=" in url:
        return re.sub(r'tag=[^&]+', f'tag={AFFILIATE_TAG}', url)
    sep = "&" if "?" in url else "?"
    return url + sep + f"tag={AFFILIATE_TAG}"


def extract_offer(text: str) -> dict:
    urls = re.findall(r'https?://[^\\s)]+', text)
    amazon = next((replace_tag(u) for u in urls if "amazon." in u), None)

    price_match = re.search(r"(\\d+[,.]?\\d*)\\s?€", text)
    price = price_match.group(1).replace(",", ".") + " €" if price_match else ""

    title_raw = re.sub(r'https?://[^\\s)]+', "", text).strip()
    title = title_raw.split("\\n")[0][:120] if title_raw else "Offerta Amazon"

    # immagine di default, se non riusciamo a scaricare quella Telegram
    return {
        "title": title,
        "url": amazon or "https://www.amazon.it/",
        "price": price,
        "image": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
    }

# ========================
# SCARICA FOTO DA TELEGRAM
# ========================

async def download_telegram_photo(client: TelegramClient, msg, save_path: str):
    if not msg.photo:
        return None
    try:
        await client.download_media(msg, file=save_path)
        return save_path
    except Exception as e:
        print(f"⚠️ Errore download immagine Telegram: {e}")
        return None

# ========================
# UPLOAD IMMAGINI SU /img
# ========================

def upload_image_to_ftp(local_path: str, remote_filename: str):
    """
    Carica una singola immagine in /img sul server
    e ritorna la URL assoluta (https://.../img/xxx.jpg)
    """
    try:
        ftps = FTP_TLS(FTP_HOST)
        ftps.login(FTP_USER, FTP_PASS)
        ftps.prot_p()

        # esempio: /www.techandmore.eu/img
        base = f"/{FTP_PATH}".rstrip("/")
        remote_dir = (base + "/img").rstrip("/") if base else "/img"

        # crea /img se non esiste
        try:
            ftps.cwd(remote_dir)
        except Exception:
            # prova a creare step by step
            parts = remote_dir.strip("/").split("/")
            current = ""
            for p in parts:
                current += "/" + p
                try:
                    ftps.mkd(current)
                except Exception:
                    pass
            ftps.cwd(remote_dir)

        with open(local_path, "rb") as f:
            ftps.storbinary(f"STOR {remote_filename}", f)

        ftps.quit()
        print(f"📸 Immagine caricata in {remote_dir}/{remote_filename}")
        # URL pubblica
        return f"{SITE_BASE_URL.rstrip('/')}/img/{remote_filename}"

    except Exception as e:
        print(f"❌ Errore FTP immagine: {e}")
        return None

# ========================
# FACEBOOK – POST UNICO CON IMMAGINE
# ========================

def publish_facebook_multi(offers: list):
    """
    Pubblica UN SOLO post su Facebook:
    - Se è disponibile almeno una foto Telegram (image_file), usa /photos con caption
    - Altrimenti usa /feed solo testuale
    Il testo contiene fino a 10 offerte.
    """
    if not offers:
        print("ℹ️ Nessuna offerta da pubblicare su Facebook")
        return

    text = "🔥 Ultime offerte Amazon\\n\\n"
    for o in offers[:10]:
        text += f"• {o['title']} – {o['price']}\\n{o['url']}\\n\\n"

    # Offerta con file immagine locale
    image_offer = next((o for o in offers if o.get("image_file")), None)

    if not image_offer:
        print("⚠️ Nessuna immagine trovata, pubblico post Facebook SENZA foto...")
        r = requests.post(
            FB_FEED_URL,
            data={"message": text, "access_token": FB_PAGE_TOKEN},
            timeout=30,
        )
        try:
            print("Facebook:", r.json())
        except Exception:
            print("Facebook:", r.text)
        return

    print("📘 Pubblico post Facebook CON immagine Telegram...")

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
        print("Facebook:", r.json())
    except Exception:
        print("Facebook:", r.text)

# ========================
# SCRAPER TELEGRAM
# ========================

async def run_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()

    # carica cache
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

                # testo per canale target (tag affiliato)
                processed = re.sub(
                    r'https?://[^\\s)]+',
                    lambda m: replace_tag(m.group(0)),
                    msg.message,
                )
                await client.send_message(TARGET_CHANNEL, processed)

                # estrai dati offerta
                offer = extract_offer(msg.message)

                # scarica immagine Telegram e carica su /img
                photo_path = f"bot/tmp_photo_{msg.id}.jpg"
                local_img = await download_telegram_photo(client, msg, photo_path)

                if local_img:
                    remote_name = f"offer_{msg.id}.jpg"
                    img_url = upload_image_to_ftp(local_img, remote_name)
                    if img_url:
                        offer["image"] = img_url  # sovrascrive l'immagine di default

                # salva anche il path locale per Facebook
                offer["image_file"] = local_img

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

    # salva JSON offerte
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
# UPLOAD SOLO JSON VIA FTPS
# ========================

def upload_site():
    """
    Carica SOLO latest_offers.json nella root del sito:
    /FTP_PATH/latest_offers.json
    NON tocca index.html.
    """
    print("🌐 Upload JSON via FTPS...")

    ftps = FTP_TLS(FTP_HOST)
    ftps.login(FTP_USER, FTP_PASS)
    ftps.prot_p()

    remote_base = f"/{FTP_PATH}".rstrip("/")
    if remote_base:
        ftps.cwd(remote_base)

    if os.path.exists(LATEST_JSON):
        with open(LATEST_JSON, "rb") as f:
            ftps.storbinary("STOR latest_offers.json", f)
        print("⬆️ Caricato: latest_offers.json")
    else:
        print("⚠️ latest_offers.json non trovato")

    ftps.quit()
    print("✅ Upload completato")

# ========================
# MAIN
# ========================

async def main():
    try:
        offers, count = await run_scraper()
        print(f"📊 Nuove offerte trovate: {count}")

        try:
            publish_facebook_multi(offers)
        except Exception as e:
            print(f"⚠️ Errore pubblicazione Facebook: {e}")

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
