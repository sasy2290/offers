import re
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import os

# Variabili da Secrets GitHub
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("TELETHON_SESSION")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")

# Canali sorgente (pubblici o ID numerici)
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

# Canale di destinazione
TARGET_CHANNEL = "@amazontechandmore"  # il tuo canale

# --- Funzioni di utilità ---

def replace_affiliate_tag(url):
    """Sostituisce il tag Amazon nel link con quello personale"""
    if "tag=" in url:
        return re.sub(r'tag=[^&]+', f'tag={AFFILIATE_TAG}', url)
    elif "amazon." in url:
        sep = "&" if "?" in url else "?"
        return url + f"{sep}tag={AFFILIATE_TAG}"
    return url


def process_message(text):
    """Trova e sostituisce i link Amazon"""
    urls = re.findall(r'https?://\S+', text)
    modified_text = text
    for url in urls:
        if "amazon." in url:
            new_url = replace_affiliate_tag(url)
            modified_text = modified_text.replace(url, new_url)
    return modified_text


async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

    await client.start()
    print("🔍 Verifica accesso ai canali Telegram...")

    valid_channels = []
    for ch in SOURCE_CHANNELS:
        try:
            entity = await client.get_entity(ch)
            valid_channels.append(entity)
            print(f"✅ Canale accessibile: {ch} (ID {entity.id})")
        except Exception as e:
            print(f"❌ Canale NON accessibile: {ch} → {e}")

    if not valid_channels:
        print("⚠️ Nessun canale valido trovato. Controlla SOURCE_CHANNELS.")
        await client.disconnect()
        return

    @client.on(events.NewMessage(chats=[c.id for c in valid_channels]))
    async def handler(event):
        msg = event.message.message
        if "amazon." in msg:
            new_msg = process_message(msg)
            await client.send_message(TARGET_CHANNEL, new_msg)
            print(f"📦 Offerta inviata da {event.chat.title}")

    print("🚀 Bot attivo. Monitoraggio canali Amazon in corso...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())


# Filtra e modifica messaggi con link Amazon
def process_message(text):
    urls = re.findall(r'https?://\S+', text)
    modified_text = text
    for url in urls:
        if "amazon." in url:
            new_url = replace_affiliate_tag(url)
            modified_text = modified_text.replace(url, new_url)
    return modified_text

async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

    @client.on(events.NewMessage(chats=SOURCE_CHANNELS))
    async def handler(event):
        msg = event.message.message
        if "amazon." in msg:
            new_msg = process_message(msg)
            await client.send_message(TARGET_CHANNEL, new_msg)

    print("📡 Bot attivo. Importa offerte dai canali sorgente...")
    await client.start()
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
