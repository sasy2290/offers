import requests
import os

PAGE_ID = os.getenv("FB_PAGE_ID")
PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN")

GRAPH_URL = f"https://graph.facebook.com/v24.0/{PAGE_ID}/feed"

def publish_to_facebook(message):
    if not PAGE_TOKEN or not PAGE_ID:
        print("❌ Facebook non configurato. Manca PAGE_ID o PAGE_TOKEN.")
        return

    payload = {
        "message": message,
        "access_token": PAGE_TOKEN
    }

    response = requests.post(GRAPH_URL, data=payload)

    try:
        data = response.json()
    except:
        data = response.text

    print("Facebook:", data)
