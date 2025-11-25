import requests
import json

# ======================================================
# CONFIG FACEBOOK
# ======================================================
FACEBOOK_PAGE_ID = "852999117901077"  # Tech & More
FACEBOOK_PAGE_TOKEN = "EAATqIm2ucDkBQEKEj7ZBTRVlhwDqrH9SZAebyjinZCATBw9hIWKa5QQSZCn0sT8HHG3RMSPM5S5xZCxpoPWliC0Akpnix30ZG7xe"

GRAPH_API_URL = f"https://graph.facebook.com/v18.0/{FACEBOOK_PAGE_ID}/feed"


# ======================================================
# INOLTRO POST SU FACEBOOK
# ======================================================
def publish_to_facebook(message: str) -> dict:
    """
    Pubblica un post testuale sulla pagina Facebook.

    :param message: testo del post
    :return: risposta JSON dell’API
    """

    payload = {
        "message": message,
        "access_token": FACEBOOK_PAGE_TOKEN
    }

    try:
        response = requests.post(GRAPH_API_URL, data=payload)
        result = response.json()

        print("📘 Risposta API Facebook:", json.dumps(result, indent=2, ensure_ascii=False))
        return result

    except Exception as e:
        print(f"❌ Errore durante la pubblicazione su Facebook: {e}")
        return {"error": str(e)}
