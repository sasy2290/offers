import os
import json
import requests

FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
FACEBOOK_PAGE_TOKEN = os.getenv("FACEBOOK_PAGE_TOKEN")
JSON_PATH = "bot/latest_offers.json"

def post_to_facebook():
    if not os.path.exists(JSON_PATH):
        print("⚠️ Nessun file JSON trovato.")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        offers = json.load(f)

    for offer in offers[:5]:  # Limita i post
        message = f"{offer['title']}\n{offer['price']}\n{offer['url']}"
        url = f"https://graph.facebook.com/{FACEBOOK_PAGE_ID}/feed"
        params = {
            "message": message,
            "access_token": FACEBOOK_PAGE_TOKEN
        }
        r = requests.post(url, params=params)
        if r.status_code == 200:
            print(f"✅ Pubblicato su Facebook: {offer['title']}")
        else:
            print(f"❌ Errore Facebook: {r.text}")

if __name__ == "__main__":
    post_to_facebook()
