import os
import re
import json
import asyncio
import sys

# ======================================================
#  FIX IMPORT PER GITHUB ACTIONS (doppia cartella offers/)
# ======================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

sys.path.append(BASE_DIR)
sys.path.append(PARENT_DIR)

# Import corretto
from publisher_facebook import publish_to_facebook



# ======================
# CONFIGURAZIONE SCRAPER
# ======================
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


# ======================
# GESTIONE CACHE
# ======================
def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {"ids": [], "texts": []}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"ids": [], "texts": []}


def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "ids": cache["ids"][-500:],
            "texts": cache["texts"][-500:]
        }, f, ensure_ascii=False, indent=2)


# ======================
# NORMALIZZAZIONE TESTO
# ======================
def normalize_text(text):
    text = re.sub(r"\s+", " ", text.lower().strip())
    text = re.sub(r"http\S+", "", text)
    return text


def replace_affiliate_tag(url):
    if "amazon." not in url:
        return url
    if "tag=" in url:
        return re.sub(r'tag=[^&]+', f'tag={AFFILIATE_TAG}', url)
    sep = "&" if "?" in url else "?"
    return url + f"{sep}tag={AFFILIATE_TAG}"


def extract_offer_data(text):
    urls = re.findall(r'https?://[^\s)]+', text)
    amazon = next((replace_affiliate_tag(u) for u in urls if "amazon." in u), None)

    price_match = re.search(r"(\d+[,.]?\d*)\s?€", text)
    price = price_match.group(1).replace(",", ".") + " €" if price_match else ""

    title_raw = re.sub(r'https?://[^\s)]+', '', text).strip()
    title = title_raw.split("\n")[0][:120] if title_raw else "Offerta Amazon"

    image = "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg"

    return {
        "title": title,
        "url": amazon or "https://www.amazon.it/",
        "price": price,
        "image": image
    }


# ======================
# PROCESSA E PULISCI TESTO
# ======================
def process_message(text):
    urls = re.findall(r'https?://[^\s)]+', text)
    for u in urls:
        if "amazon." in u:
            text = text.replace(u, replace_affiliate_tag(u))
    return text


# ======================
# LOGICA PRINCIPALE SCRAPER
# ======================
async def run_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()

    cache = load_cache()
    offers = []
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

                cleaned = process_message(text)
                await client.send_message(TARGET_CHANNEL, cleaned)

                data = extract_offer_data(text)
                offers.append(data)

                # Pubblicazione automatica su Facebook
                fb_text = f"{data['title']}\n{data['price']}\n{data['url']}"
                publish_to_facebook(fb_text)

                cache["ids"].append(msg.id)
                cache["texts"].append(normalized)
                new_posts += 1

        except Exception as e:
            print(f"⚠️ Errore con {ch}: {e}")

    save_cache(cache)

    if offers:
        os.makedirs(os.path.dirname(LATEST_JSON), exist_ok=True)
        with open(LATEST_JSON, "w", encoding="utf-8") as f:
            json.dump(offers[:20], f, ensure_ascii=False, indent=2)
        print(f"💾 Salvate {len(offers[:20])} offerte in JSON")
    else:
        print("⚠️ Nessuna offerta nuova trovata.")

    await client.disconnect()

    print("🧩 Anteprima JSON:")
    print(json.dumps(offers[:3], ensure_ascii=False, indent=2))
    print(f"✅ Fine scraper. {new_posts} offerte pubblicate.")
    return new_posts


# ======================
# MAIN CON TIMEOUT
# ======================
async def main():
    try:
        new_posts = await asyncio.wait_for(run_scraper(), timeout=120)
        print(f"📊 Offerte nuove: {new_posts}")
    except asyncio.TimeoutError:
        print("⏱️ Timeout raggiunto.")
    except (AuthKeyDuplicatedError, SessionRevokedError):
        print("⚠️ Sessione Telethon scaduta.")
        print("Rigenera TELETHON_SESSION.")
    except Exception as e:
        print(f"❌ Errore imprevisto: {e}")
    finally:
        print("🔚 Script completato.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
