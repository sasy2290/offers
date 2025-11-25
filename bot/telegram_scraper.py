import os
import re
import json
import asyncio
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import AuthKeyDuplicatedError, SessionRevokedError
from publisher_facebook import publish_to_facebook



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
    """Carica la cache dei messaggi già pubblicati (per evitare duplicati)."""
    if not os.path.exists(CACHE_FILE):
        return {"ids": [], "texts": []}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"ids": [], "texts": []}


def save_cache(cache):
    """Salva la cache, limitandola agli ultimi 500 elementi."""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "ids": cache["ids"][-500:],
                "texts": cache["texts"][-500:]
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


def normalize_text(text: str) -> str:
    """Normalizza il testo per confronti contro i duplicati."""
    text = re.sub(r"\s+", " ", text.lower().strip())
    text = re.sub(r"http\S+", "", text)
    return text


def replace_affiliate_tag(url: str) -> str:
    """Aggiunge o sostituisce il tag affiliato Amazon nel link."""
    if "amazon." not in url:
        return url
    if "tag=" in url:
        return re.sub(r'tag=[^&]+', f'tag={AFFILIATE_TAG}', url)
    sep = "&" if "?" in url else "?"
    return url + f"{sep}tag={AFFILIATE_TAG}"


def estrai_dati_offerta(text: str) -> dict:
    """
    Estrae titolo, link, prezzo e immagine dai messaggi Telegram.
    Usa un placeholder per l'immagine, migliorabile in seguito.
    """
    urls = re.findall(r'https?://[^\s)]+', text)
    link = next((replace_affiliate_tag(u) for u in urls if "amazon." in u), None)

    prezzo_match = re.search(r"(\d+[,.]?\d*)\s?€", text)
    prezzo = prezzo_match.group(1).replace(",", ".") + " €" if prezzo_match else ""

    titolo_raw = re.sub(r'https?://[^\s)]+', '', text).strip()
    titolo = titolo_raw.split("\n")[0][:120] if titolo_raw else "Offerta Amazon"

    # Placeholder: logo Amazon (puoi sostituire con immagine prodotto se la ricavi)
    immagine = "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg"

    return {
        "title": titolo,
        "url": link or "https://www.amazon.it/",
        "price": prezzo,
        "image": immagine,
    }


def process_message(text: str) -> str:
    """Sostituisce i link Amazon con link contenenti il tag affiliato."""
    urls = re.findall(r'https?://[^\s)]+', text)
    for url in urls:
        if "amazon." in url:
            text = text.replace(url, replace_affiliate_tag(url))
    return text


async def run_scraper():
    """Legge i canali sorgente, inoltra le offerte su Telegram e su Facebook."""
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

                # Salta se già visto
                if msg.id in cache["ids"] or normalized in cache["texts"]:
                    continue

                # Pre-elabora il messaggio con i link affiliati
                processed = process_message(text)

                # Pubblicazione su Telegram
                await client.send_message(TARGET_CHANNEL, processed)

                # Estrazione dati per JSON + Facebook
                dati = estrai_dati_offerta(processed)
                offerte.append(dati)

                # Pubblicazione su Facebook
                try:
                    fb_message = f"🔥 {dati['title']}\n💰 {dati['price']}\n👉 {dati['url']}"
                    publish_to_facebook(fb_message, dati["image"])
                    print("📘 Pubblicata anche su Facebook:", dati["title"])
                except Exception as e:
                    print("❌ Errore pubblicazione Facebook:", e)

                # Aggiorna cache
                cache["ids"].append(msg.id)
                cache["texts"].append(normalized)
                new_posts += 1

        except Exception as e:
            print(f"⚠️ Errore con {ch}: {e}")

    # Salva cache aggiornata
    save_cache(cache)

    # Salva file JSON con ultime offerte
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
