import requests
import os

PAGE_ID = "805226559349193"   # tua pagina Tech & More
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")


def publish_offer_to_facebook(message, link=None, image_url=None):
    url = f"https://graph.facebook.com/v20.0/{PAGE_ID}/feed"

    data = {
        "message": message,
        "access_token": PAGE_ACCESS_TOKEN
    }

    if link:
        data["link"] = link

    if image_url:
        data["picture"] = image_url

    r = requests.post(url, data=data)
    try:
        r.raise_for_status()
    except:
        print("Errore Facebook:", r.text)
        return None

    return r.json()
