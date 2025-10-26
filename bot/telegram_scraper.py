import os
import re
import json
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import AuthKeyDuplicatedError, SessionRevokedError

# === CONFIG ===
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("TELETHON_SESSION", "")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "techandmore05-21")

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
]

TARGET_CHANNEL = "@amazontechandmore"
CACHE_FILE = "bot/posted_cache.json"


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {"ids": [], "texts": []}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"ids": [], "texts": []}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"ids": cache["ids"][-500:], "texts": cache["texts"][-500:]},
            f, ensure_ascii=False, indent=2
        )


def normalize_text(text):
    """Normalizza testo per confronti duplicati"""
    text = re.sub(r"\s+", " ", text.lower().strip())
    text = re.sub(r"http\S+", "", text)  # rimuove link
    return text


def replace_affiliate_tag(url):
    if "tag=" in url:
        return re.sub(r'tag=[^&]+', f'tag={AFFILIATE_TAG}', url)
    elif "amazon." in url:
        sep = "&" if "?" in url else "?"
        return url + f"{sep}tag={AFFILIATE_TAG}"
    return url


def process_message(text):
    urls = re.findall(r'https?://\S+', text)
    for url in urls:
        if "amazon." in url:
            text = text.replace(url, replace_affiliate_tag(url))
    return text


async def run_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()

    cache = load_cache()
    new_posts = 0

    print("🔍 Controllo nuovi messaggi Amazon...")

    for ch in SOURCE_CHANNELS:
        try:
            entity = await client.get_entity(ch)
            messages = await client.get_messages(entity, limit=10)

            for msg in messages:
                if not msg.message or "amazon." not in msg.message.lower():
                    continue

                text = msg.message.strip()
                normalized = normalize_text(text)

                # Evita duplicati per ID o testo
                if msg.id in cache["ids"] or normalized in cache["texts"]:
                    continue

                processed = process_message(text)
                await client.send_message(TARGET_CHANNEL, processed)
                cache["ids"].append(msg.id)
                cache["texts"].append(normalized)
                new_posts += 1

        except Exception as e:
            print(f"⚠️ Errore con {ch}: {e}")

    save_cache(cache)
    await client.disconnect()

    print(f"✅ Fine esecuzione. {new_posts} nuove offerte pubblicate.")
    return new_posts


import sys
import asyncio

async def main():
    try:
        # Timeout massimo di 1 minuto
        new_posts = await asyncio.wait_for(run_scraper(), timeout=120)
        print(f"📊 Totale offerte nuove trovate: {new_posts}")
    except asyncio.TimeoutError:
        print("⏱️ Timeout raggiunto, chiusura forzata.")
    except (AuthKeyDuplicatedError, SessionRevokedError):
        print("⚠️ Sessione Telethon invalidata o scaduta.")
        print("🔁 Rigenera la TELETHON_SESSION localmente con lo script generate_session.py")
    except Exception as e:
        print(f"❌ Errore imprevisto: {e}")
    finally:
        print("🔚 Script completato.")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())

