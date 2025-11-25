import os
import requests

# Lettura variabili da GitHub Secrets
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
FACEBOOK_PAGE_TOKEN = os.getenv("FACEBOOK_PAGE_TOKEN")

GRAPH_API_URL = "https://graph.facebook.com/v19.0"


def publish_to_facebook(message: str) -> dict:
    """
    Pubblica un post di solo testo sulla pagina Facebook.

    :param message: Testo del post
    :return: Risposta JSON Facebook API
    """

    if not FACEBOOK_PAGE_ID or not FACEBOOK_PAGE_TOKEN:
        print("❌ Facebook non configurato (PAGE_ID o TOKEN mancanti)")
        return {"error": "missing_config"}

    url = f"{GRAPH_API_URL}/{FACEBOOK_PAGE_ID}/feed"

    payload = {
        "message": message,
        "access_token": FACEBOOK_PAGE_TOKEN
    }

    try:
        response = requests.post(url, data=payload)
        result = response.json()

        if "id" in result:
            print(f"✅ Post pubblicato su Facebook: {result['id']}")
        else:
            print(f"⚠️ Errore da Facebook: {result}")

        return result

    except Exception as e:
        print("❌ Errore chiamando le API Facebook:", e)
        return {"error": str(e)}
