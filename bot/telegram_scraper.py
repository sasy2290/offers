import re
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import os

# Legge i secret da GitHub Actions (oppure variabili locali per test)
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("TELETHON_SESSION")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")

# Canali sorgente da cui copiare offerte (aggiungi i @usernames)
SOURCE_CHANNELS = [
    "offertepertutti",  # esempio
    "scontiesubito",    # aggiungi altri
    "offertepiu", 
    @SoloOfferteECodiciSconto,
    @offertebenesseretop,
    @offerte24hgruppo,
    @DottSconto,
    @offertepaz,
    @ilmondodelrisparmio,
    @LeoffertedelGiorno,
    @mondodiofferte,
    @giga_offertee,
    @codici_sconto_sconti,
]

# Canale tuo dove pubblicare
TARGET_CHANNEL = "@amazontechandmore"  # metti qui il tuo canale

# Sostituisce il tag Amazon nel link
def replace_affiliate_tag(url):
    if "tag=" in url:
        return re.sub(r'tag=[^&]+', f'tag={AFFILIATE_TAG}', url)
    elif "amazon." in url:
        return url + f"&tag={AFFILIATE_TAG}"
    return url

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
