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
LOCAL_JSON = "bot/latest_offers.json"


def aggiorna_html_con_offerte(index_path, offerte_html):
    """Aggiorna solo la sezione OFFERTE nel file index.html"""
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    if "<!-- OFFERTE START -->" in html and "<!-- OFFERTE END -->" in html:
        import re
        nuovo_html = re.sub(
            r"<!-- OFFERTE START -->.*?<!-- OFFERTE END -->",
            f"<!-- OFFERTE START -->\n{offerte_html}\n<!-- OFFERTE END -->",
            html,
            flags=re.S
        )
    else:
        print("⚠️ Commenti di delimitazione non trovati, nessuna modifica eseguita.")
        return False

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(nuovo_html)

    print("✅ Sezione offerte aggiornata nel file index.html")
    return True



def aggiorna_index():
    """Aggiorna index.html con le nuove offerte e la data."""
    if not os.path.exists(LOCAL_INDEX):
        print("❌ index.html non trovato.")
        return False

    with open(LOCAL_INDEX, "r", encoding="utf-8") as f:
        html = f.read()

    # Carica le offerte
    if not os.path.exists(LOCAL_JSON):
        print(f"📁 Percorso file JSON controllato: {os.path.abspath(LOCAL_JSON)}")
        print("⚠️ Nessun file latest_offers.json trovato.")
        offerte_html = "<p style='color:#00bfff;'>⚠ Nessuna offerta trovata nel JSON.</p>"
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
