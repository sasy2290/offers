import os
import json
from datetime import datetime
from ftplib import FTP_TLS

FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH", "/www.techandmore.eu/")
LOCAL_INDEX = "index.html"
LOCAL_JSON = "latest_offers.json"

def genera_html_offerte(offerte):
    blocchi = []
    for o in offerte:
        titolo = o.get("title", "Offerta Amazon")
        link = o.get("url", "#")
        prezzo = o.get("price", "")
        immagine = o.get("image", "https://www.amazon.it/favicon.ico")

        blocchi.append(f"""
        <div class="offerta">
            <img src="{immagine}" alt="Prodotto">
            <p class="offerta-title">{titolo}</p>
            <p class="offerta-prezzo">{prezzo}</p>
            <a href="{link}" target="_blank" rel="noopener noreferrer">Vai all'offerta 🔗</a>
        </div>
        """)
    return "\n".join(blocchi)

def aggiorna_index():
    if not os.path.exists(LOCAL_INDEX):
        print("❌ index.html non trovato.")
        return

    with open(LOCAL_INDEX, "r", encoding="utf-8") as f:
        html = f.read()

    if not os.path.exists(LOCAL_JSON):
        print("⚠️ Nessun file offerte trovato.")
        offerte_html = "<p>Nessuna offerta disponibile.</p>"
    else:
        with open(LOCAL_JSON, "r", encoding="utf-8") as f:
            offerte = json.load(f)
        offerte_html = genera_html_offerte(offerte[:12])

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    html = html.replace("<!-- OFFERTE START -->", f"<!-- OFFERTE START -->\n{offerte_html}")
    html = html.replace("Aggiornato automaticamente", f"Aggiornato automaticamente {now}")

    with open(LOCAL_INDEX, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"🕒 File HTML aggiornato a {now}")

def carica_su_aruba():
    try:
        with FTP_TLS(FTP_HOST) as ftp:
            ftp.login(FTP_USER, FTP_PASS)
            ftp.cwd(FTP_PATH)
            with open(LOCAL_INDEX, "rb") as f:
                ftp.storbinary("STOR index.html", f)
            print(f"✅ index.html aggiornato su {FTP_PATH}")
    except Exception as e:
        print(f"❌ Errore FTP: {e}")

if __name__ == "__main__":
    aggiorna_index()
    carica_su_aruba()
