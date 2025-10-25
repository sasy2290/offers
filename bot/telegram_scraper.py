import os
import re
import json
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import AuthKeyDuplicatedError, SessionRevokedError

# === CONFIG ===
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("TELETHON_SESSION", "")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "techandmore05-21")

# canali sorgente (pubblici o ID numerici)
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

# canale di destinazione
TARGET_CHANNEL = "@amazontechandmore"

# file cache
CACHE_FILE = "bot/posted_cache.json"


# === FUNZIONI ===
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
    """Cerca e sostituisce i link Amazon"""
    urls = re.findall(r'https?://\S+', text)
    for url in urls:
        if "amazon." in url:
            text = text.replace(url, replace_affiliate_tag(url))
    return text


async def run_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("⚠️ Sessione non autorizzata. Creazione nuova...")
        await client.start()
        new_session = client.session.save()
        print(f"\nNuova SESSION_STRING generata:\n{new_session}\n")
        print("👉 Copia questa stringa nei secrets GitHub come TELETHON_SESSION.")
        await client.disconnect()
        return

    cache = load_cache()

    print("🔍 Verifica canali accessibili...")
    valid_channels = []
    for ch in SOURCE_CHANNELS:
        try:
            entity = await client.get_entity(ch)
            valid_channels.append(entity)
            print(f"✅ Accesso OK: {ch}")
        except Exception as e:
            print(f"❌ Canale non accessibile: {ch} → {e}")

    if not valid_channels:
        print("⚠️ Nessun canale valido trovato. Interruzione.")
        await client.disconnect()
        return

    @client.on(events.NewMessage(chats=[c.id for c in valid_channels]))
    async def handler(event):
        msg = event.message
        text = msg.message or ""
        if "amazon." not in text.lower():
            return

        if msg.id in cache:
            return  # già pubblicato

        updated = process_message(text)
        await client.send_message(TARGET_CHANNEL, updated)
        cache.append(msg.id)
        save_cache(cache)
        print(f"📦 Pubblicato messaggio da {event.chat.title}")

    print("🟢 Bot attivo. Monitoraggio canali Amazon in corso...")
    await client.run_until_disconnected()


async def main():
    try:
        await run_scraper()
    except (AuthKeyDuplicatedError, SessionRevokedError):
        print("⚠️ Sessione Telethon invalidata. Rigenerazione...")
        new_client = TelegramClient(StringSession(), API_ID, API_HASH)
        await new_client.start()
        new_session = new_client.session.save()
        print(f"\nNuova SESSION_STRING generata automaticamente:\n{new_session}\n")
        print("👉 Copia questa stringa nei secrets GitHub come TELETHON_SESSION.")
        await new_client.disconnect()
    except Exception as e:
        print(f"❌ Errore imprevisto: {e}")


if __name__ == "__main__":
    asyncio.run(main())
