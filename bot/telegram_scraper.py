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
        json.dump({"ids": cache["ids"][-500:], "texts": cache["texts"][-500:]}, f, ensure_ascii=False, indent=2)


def normalize_text(text):
    text = re.sub(r"\s+", " ", text.lower().strip())
    text = re.sub(r"http\S+", "", text)
    return text


def replace_affiliate_tag(url):
    """Aggiunge o sostituisce il tag affiliato."""
    if "amazon." not in url:
        return url
    if "tag=" in url:
        return re.sub(r'tag=[^&]+', f'tag={AFFILIATE_TAG}', url)
    sep = "&" if "?" in url else "?"
    return url + f"{sep}tag={AFFILIATE_TAG}"


def estrai_dati_offerta(text):
    """Estrae titolo, link, prezzo e immagine dai messaggi Telegram."""
    urls = re.findall(r'https?://[^\s)]+', text)
    link = next((replace_affiliate_tag(u) for u in urls if "amazon." in u), None)

    prezzo_match = re.search(r"(\d+[,.]?\d*)\s?€", text)
    prezzo = prezzo_match.group(1).replace(",", ".") + " €" if prezzo_match else ""

    titolo_raw = re.sub(r'https?://[^\s)]+', '', text).strip()
    titolo = titolo_raw.split("\n")[0][:120] if titolo_raw else "Offerta Amazon"

    immagine = "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg"

    return {
        "title": titolo,
        "url": link or "https://www.amazon.it/",
        "price": prezzo,
        "image": immagine
    }


async def run_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()

    cache = load_cache()
    offerte = []
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
                if msg.id in cache["ids"] or normalized in cache["texts"]:
                    continue

                processed = process_message(text)
                await client.send_message(TARGET_CHANNEL, processed)

                dati = estrai_dati_offerta(text)
                offerte.append(dati)

                cache["ids"].append(msg.id)
                cache["texts"].append(normalized)
                new_posts += 1

        except Exception as e:
            print(f"⚠️ Errore con {ch}: {e}")

    save_cache(cache)

    if offerte:
        os.makedirs(os.path.dirname(LATEST_JSON), exist_ok=True)
        with open(LATEST_JSON, "w", encoding="utf-8") as f:
            json.dump(offerte[:20], f, ensure_ascii=False, indent=2)
        print(f"💾 Salvate {len(offerte[:20])} offerte in {LATEST_JSON}")
    else:
        print("⚠️ Nessuna offerta valida trovata per il JSON.")

    await client.disconnect()
    print("🧩 Anteprima JSON salvato:")
    print(json.dumps(offerte[:3], ensure_ascii=False, indent=2))
    print(f"✅ Fine esecuzione. {new_posts} nuove offerte pubblicate.")
    return new_posts


def process_message(text):
    urls = re.findall(r'https?://[^\s)]+', text)
    for url in urls:
        if "amazon." in url:
            text = text.replace(url, replace_affiliate_tag(url))
    return text


import sys


async def main():
    try:
        new_posts = await asyncio.wait_for(run_scraper(), timeout=120)
        print(f"📊 Totale offerte nuove trovate: {new_posts}")
    except asyncio.TimeoutError:
        print("⏱️ Timeout raggiunto, chiusura forzata.")
    except (AuthKeyDuplicatedError, SessionRevokedError):
        print("⚠️ Sessione Telethon invalidata o scaduta.")
        print("🔁 Rigenera la TELETHON_SESSION localmente con generate_session.py")
    except Exception as e:
        print(f"❌ Errore imprevisto: {e}")
    finally:
        print("🔚 Script completato.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
