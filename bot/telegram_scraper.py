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
        json.dump(
            {"ids": cache["ids"][-500:], "texts": cache["texts"][-500:]},
            f, ensure_ascii=False, indent=2
        )


def normalize_text(text):
    text = re.sub(r"\s+", " ", text.lower().strip())
    text = re.sub(r"http\S+", "", text)
    return text


def replace_affiliate_tag(url):
    if "tag=" in url:
        return re.sub(r'tag=[^&]+', f'tag={AFFILIATE_TAG}', url)
    elif "amazon." in url:
        sep = "&" if "?" in url else "?"
        return url + f"{sep}tag={AFFILIATE_TAG}"
    return url


def estrai_dati_offerta(text):
    """Estrae titolo, link e prezzo da un messaggio Telegram."""
    urls = re.findall(r'https?://\S+', text)
    amazon_links = [replace_affiliate_tag(u) for u in urls if "amazon." in u]
    link = amazon_links[0] if amazon_links else None

    prezzo = None
    prezzo_match = re.search(r"(\d+[,.]?\d*) ?€", text)
    if prezzo_match:
        prezzo = prezzo_match.group(1).replace(",", ".") + "€"

    # Togli link e simboli inutili dal titolo
    titolo = re.sub(r'https?://\S+', '', text)
    titolo = re.sub(r'[\*\#\@\|\[\]]', '', titolo).strip()
    titolo = titolo.split("\n")[0][:120] if titolo else "Offerta Amazon"

    return {"titolo": titolo, "link": link, "prezzo": prezzo}


async def run_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()

    cache = load_cache()
    new_posts = 0
    offerte = []

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

                # Estrai dati per JSON
                offerta = estrai_dati_offerta(text)
                if offerta["link"]:
                    offerte.append(offerta)

                cache["ids"].append(msg.id)
                cache["texts"].append(normalized)
                new_posts += 1

        except Exception as e:
            print(f"⚠️ Errore con {ch}: {e}")

    save_cache(cache)

    # Salva JSON con le ultime 20 offerte
    if offerte:
        os.makedirs(os.path.dirname(LATEST_JSON), exist_ok=True)
        with open(LATEST_JSON, "w", encoding="utf-8") as f:
            json.dump(offerte[:20], f, ensure_ascii=False, indent=2)
        print(f"💾 Salvate {len(offerte[:20])} offerte in {LATEST_JSON}")
    else:
        print("⚠️ Nessuna offerta valida trovata per il JSON.")

    await client.disconnect()
    print(f"✅ Fine esecuzione. {new_posts} nuove offerte pubblicate.")
    return new_posts


def process_message(text):
    urls = re.findall(r'https?://\S+', text)
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
