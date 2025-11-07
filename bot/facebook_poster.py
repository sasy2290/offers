import os
import json
import time
import requests
from pathlib import Path

PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "").strip()
PAGE_TOKEN = os.getenv("FACEBOOK_PAGE_TOKEN", "").strip()

JSON_PATH = "bot/latest_offers.json"
CACHE_PATH = "bot/facebook_posted.json"   # per evitare doppioni fra run
MAX_POSTS_PER_RUN = 5                     # limitiamo per sicurezza
POST_DELAY_SEC = 3                        # piccola pausa tra i post


def load_json(path):
    if not Path(path).exists():
        print(f"⚠️ File non trovato: {path}")
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"⚠️ Errore lettura {path}: {e}")
        return []


def load_cache():
    if not Path(CACHE_PATH).exists():
        return {"urls": []}
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"urls": []}


def save_cache(cache):
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"urls": cache["urls"][-1000:]}, f, ensure_ascii=False, indent=2)


def check_env():
    if not PAGE_ID or not PAGE_TOKEN:
        raise RuntimeError("FACEBOOK_PAGE_ID o FACEBOOK_PAGE_TOKEN mancanti.")


def post_link(offer):
    """
    Pubblica con anteprima link su /{page-id}/feed.
    """
    url = f"https://graph.facebook.com/{PAGE_ID}/feed"
    message = f"{offer.get('title','Offerta')}\n{offer.get('price','')}"
    params = {
        "message": message.strip(),
        "link": offer.get("url", ""),
        "access_token": PAGE_TOKEN
    }
    r = requests.post(url, params=params, timeout=20)
    return r


def post_photo_fallback(offer):
    """
    Fallback se /feed fallisce: pubblica immagine con caption su /{page-id}/photos.
    Facebook mostrerà la foto; il link Amazon resta in caption.
    """
    url = f"https://graph.facebook.com/{PAGE_ID}/photos"
    caption = f"{offer.get('title','Offerta')}\n{offer.get('price','')}\n{offer.get('url','')}"
    params = {
        "url": offer.get("image",""),
        "caption": caption.strip(),
        "access_token": PAGE_TOKEN
    }
    r = requests.post(url, params=params, timeout=20)
    return r


def main():
    check_env()

    offers = load_json(JSON_PATH)
    if not offers:
        print("⚠️ Nessuna offerta da pubblicare.")
        return

    cache = load_cache()
    posted = 0

    for off in offers:
        if posted >= MAX_POSTS_PER_RUN:
            break

        link = off.get("url", "").strip()
        title = off.get("title", "").strip()
        if not link or not title:
            continue

        # evita doppioni per URL
        if link in cache["urls"]:
            continue

        # tenta post con anteprima link
        r = post_link(off)
        if r.status_code == 200:
            print(f"✅ Pubblicato (link): {title}")
            cache["urls"].append(link)
            posted += 1
            time.sleep(POST_DELAY_SEC)
            continue

        # se fallisce, prova fallback foto
        print(f"ℹ️ Fallback foto per: {title} | Errore link: {r.status_code} {r.text}")
        r2 = post_photo_fallback(off)
        if r2.status_code == 200:
            print(f"✅ Pubblicato (foto): {title}")
            cache["urls"].append(link)
            posted += 1
            time.sleep(POST_DELAY_SEC)
            continue

        print(f"❌ Errore Facebook definitivo: {r.status_code} {r.text} | Fallback: {r2.status_code} {r2.text}")

    save_cache(cache)
    print(f"📊 Pubblicati ora: {posted} post. Cache totale: {len(cache['urls'])}")


if __name__ == "__main__":
    main()
