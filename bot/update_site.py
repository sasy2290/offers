import os
import json
from datetime import datetime
from ftplib import FTP_TLS

# === CONFIG ===
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH", "/www.techandmore.eu/")
LOCAL_INDEX = "index.html"
LOCAL_JSON = "latest_offers.json"


def genera_html_offerte(offerte):
    """Genera il blocco HTML con le offerte."""
    blocchi = []
    for o in offerte:
        titolo = o.get("title", "Offerta Amazon")
        link = o.get("url", "#")
        prezzo = o.get("price", "")
        immagine = o.get("image", "https://www.amazon.it/favicon.ico")

        blocchi.append(f"""
        <div class="offerta">
            <img src="{immagine}" alt="Prodotto Amazon">
            <p class="offerta-title">{titolo}</p>
            <p class="offerta-prezzo">{prezzo}</p>
            <a href="{link}" target="_blank" rel="noopener noreferrer">Vai all'offerta 🔗</a>
        </div>
        """)
    return "\n".join(blocchi)


def aggiorna_index():
    """Aggiorna index.html con le nuove offerte e la data."""
    if not os.path.exists(LOCAL_INDEX):
        print("❌ index.html non trovato.")
        return False

    with open(LOCAL_INDEX, "r", encoding="utf-8") as f:
        html = f.read()

    # Carica le offerte
    if not os.path.exists(LOCAL_JSON):
        print("⚠️ Nessun file latest_offers.json trovato.")
        offerte_html = "<p>Nessuna offerta disponibile.</p>"
    else:
        with open(LOCAL_JSON, "r", encoding="utf-8") as f:
            try:
                offerte = json.load(f)
                if not isinstance(offerte, list):
                    raise ValueError("Formato JSON non valido.")
            except Exception as e:
                print(f"⚠️ Errore lettura JSON: {e}")
                offerte = []
        offerte_html = genera_html_offerte(offerte[:12])

    # Aggiorna blocco offerte
    if "<!-- OFFERTE START -->" in html and "<!-- OFFERTE END -->" in html:
        nuovo_html = html.split("<!-- OFFERTE START -->")[0] + \
                     f"<!-- OFFERTE START -->\n{offerte_html}\n<!-- OFFERTE END -->" + \
                     html.split("<!-- OFFERTE END -->")[1]
    else:
        print("⚠️ Commenti di delimitazione non trovati nel file HTML.")
        nuovo_html = html

    # Aggiorna data nel footer
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    nuovo_html = nuovo_html.replace(
        "Aggiornato automaticamente",
        f"Aggiornato automaticamente {now}"
    )

    with open(LOCAL_INDEX, "w", encoding="utf-8") as f:
        f.write(nuovo_html)

    print(f"🕒 File HTML aggiornato a {now}")
    return True


def carica_su_aruba():
    """Carica il file aggiornato su Aruba via FTPS."""
    try:
        print(f"🌐 Connessione a {FTP_HOST} ...")
        with FTP_TLS(FTP_HOST) as ftp:
            ftp.login(FTP_USER, FTP_PASS)
            ftp.prot_p()
            ftp.cwd(FTP_PATH)
            with open(LOCAL_INDEX, "rb") as f:
                ftp.storbinary("STOR index.html", f)
            print(f"✅ index.html aggiornato con successo su {FTP_PATH}")
    except Exception as e:
        print(f"❌ Errore FTP: {e}")


if __name__ == "__main__":
    if aggiorna_index():
        carica_su_aruba()
        print("✅ Homepage aggiornata su Aruba tramite FTPS.")
    else:
        print("⚠️ Nessuna modifica effettuata.")
