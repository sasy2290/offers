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

# Canali sorgente (pubblici)
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
]

# Canale destinazione
TARGET_CHANNEL = "@amazontechandmore"

# File cache
CACHE_FILE = "bot/posted_cache.json"


def load_cache():
    """Carica ID messaggi già pubblicati"""
    if not os.path.exists(CACHE_FILE):
        return []
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_cache(cache):
    """Salva la cache su file"""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache[-500:], f, ensure_ascii=False, indent=2)


def replace_affiliate_tag(url):
    """Sostituisce o aggiunge il tag affiliato Amazon"""
    if "tag=" in url:
        return re.sub(r'tag=[^&]+', f'tag={AFFILIATE_TAG}', url)
    elif "amazon." in url:
        sep = "&" if "?" in url else "?"
        return url + f"{sep}tag={AFFILIATE_TAG}"
    return url


def process_message(text):
    """Sostituisce i link Amazon nel testo"""
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

    print("🔍 Controllo nuovi messaggi...")

    for ch in SOURCE_CHANNELS:
        try:
            entity = await client.get_entity(ch)
            messages = await client.get_messages(entity, limit=10)

            for msg in messages:
                if not msg.message or "amazon." not in msg.message.lower():
                    continue
                if msg.id in cache:
                    continue

                text = process_message(msg.message)
                await client.send_message(TARGET_CHANNEL, text)
                cache.append(msg.id)
                new_posts += 1

        except Exception as e:
            print(f"⚠️ Errore con {ch}: {e}")

    save_cache(cache)
    await client.disconnect()

    print(f"✅ Fine esecuzione. {new_posts} nuovi post pubblicati.")
    return new_posts


import sys
import asyncio

async def main():
    try:
        # Timeout massimo: 120 secondi
        await asyncio.wait_for(run_scraper(), timeout=120)
    except asyncio.TimeoutError:
        print("⏱️ Timeout raggiunto, chiusura forzata.")
    except (AuthKeyDuplicatedError, SessionRevokedError):
        print("⚠️ Sessione Telethon invalidata. Rigenerazione necessaria.")
    except Exception as e:
        print(f"❌ Errore imprevisto: {e}")
    finally:
        print("🔚 Script completato, terminazione pulita.")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
