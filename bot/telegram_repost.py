from telethon import TelegramClient
import re
import os
import asyncio

# === CONFIG ===
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session_name = "techandmore_session"

SOURCE_CHANNELS = ["@offerteTech", "@scontiPrime, @offertepoint, @DottSconto, @SoloOfferteECodiciSconto, @giga_offertee"]  # canali sorgente
DEST_CHANNEL = "@amazontechandmore"                 # canale di destinazione
AFFILIATE_TAG = "techandmor03f-21"                  # tag Amazon personale


def replace_amazon_tag(text: str) -> str:
    """Sostituisce o aggiunge il tag affiliato Amazon nei link."""
    if not text:
        return text
    text = re.sub(r"tag=[A-Za-z0-9\-]+", f"tag={AFFILIATE_TAG}", text)
    text = re.sub(r"(https?://(?:www\.)?amazon\.it/[^\s]+)(?!.*tag=)", r"\1?tag=" + AFFILIATE_TAG, text)
    text = re.sub(r"(https?://amzn\.to/[^\s]+)", r"\1?tag=" + AFFILIATE_TAG, text)
    return text


async def main():
    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()
    print("✅ Connesso a Telegram")

    for source in SOURCE_CHANNELS:
        print(f"→ Lettura da {source}")
        async for msg in client.iter_messages(source, limit=30):
            if not msg.message:
                continue
            text = msg.message
            if "amazon" in text.lower() or "amzn.to" in text.lower():
                new_text = replace_amazon_tag(text)
                await client.send_message(DEST_CHANNEL, new_text)
                print(f"✔ Copiato messaggio da {source}")

    await client.disconnect()
    print("✅ Operazione completata.")


if __name__ == "__main__":
    asyncio.run(main())
