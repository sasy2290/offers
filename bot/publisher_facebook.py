import requests

# ID della pagina Facebook Tech & More
FACEBOOK_PAGE_ID = "852999117901077"

# Page Access Token generato da /me/accounts (quello lungo EAAT/EAAG...)
FACEBOOK_PAGE_TOKEN = "INSERISCI_QUI_IL_TUO_PAGE_TOKEN"

GRAPH_API_BASE_URL = "https://graph.facebook.com/v24.0"


def publish_facebook_post(message: str) -> dict:
    """
    Pubblica un semplice post di testo sulla pagina Facebook.

    :param message: Testo del post (la stessa stringa che mandi a Telegram)
    :return: Risposta JSON dell'API Facebook
    """
    url = f"{GRAPH_API_BASE_URL}/{FACEBOOK_PAGE_ID}/feed"
    payload = {
        "message": message,
        "access_token": FACEBOOK_PAGE_TOKEN,
    }

    response = requests.post(url, data=payload, timeout=20)

    try:
        data = response.json()
    except Exception:
        data = {"error": "Invalid JSON", "text": response.text}

    if not response.ok:
        # Puoi loggare o stampare l'errore
        print("Facebook API error:", data)

    return data
