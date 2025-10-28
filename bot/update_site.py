import os
import re
import json
from datetime import datetime
from ftplib import FTP_TLS

# === CONFIG ===
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = "/www.techandmore.eu/"  # percorso del tuo sito
LOCAL_INDEX = "index.html"
OFFERS_FILE = "bot/latest_offers.json"  # file generato dallo scraper


# === FUNZIONI ===
def carica_offerte():
    """Legge il file JSON delle offerte generate dallo scraper"""
    if not os.path.exists(OFFERS_FILE):
        print("⚠️ Nessun file di offerte trovato.")
        return []

    try:
        with open(OFFERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data[:20]  # solo le prime 20 offerte
    except Exception as e:
        print(f"❌ Errore nel leggere le offerte: {e}")
        return []


def genera_html_offerte(offerte):
    """Genera blocchi HTML per le offerte"""
    blocchi = []
    for o in offerte:
        titolo = o.get("title", "Offerta Amazon")
        link = o.get("url", "#")
        prezzo = o.get("price", "")
        blocchi.append(
            f"""
            <div class="offerta">
                <a href="{link}" target="_blank" rel="noopener">
                    <p><strong>{titolo}</strong></p>
                    <p>{prezzo}</p>
                </a>
            </div>
            """
        )
    return "\n".join(blocchi)


def aggiorna_html(file_path, offerte):
    """Aggiorna index.html con nuove offerte e data"""
    if not os.path.exists(file_path):
        print(f"❌ File non trovato: {file_path}")
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    blocchi = genera_html_offerte(offerte)

    # Sostituisce il blocco delle offerte
    html = re.sub(
        r"(<!-- OFFERTE START -->)(.*?)(<!-- OFFERTE END -->)",
        f"\\1\n{blocchi}\n\\3",
        html,
        flags=re.S
    )

    # Aggiorna data
    html = re.sub(
        r"Aggiornato automaticamente[^<]*",
        f"Aggiornato automaticamente {now}",
        html
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"🕒 HTML aggiornato con {len(offerte)} offerte e data {now}")
    return True


def upload_ftps(local_file, remote_file):
    """Carica il file su Aruba via FTPS"""
    print(f"🌐 Connessione a {FTP_HOST}...")
    ftps = FTP_TLS(FTP_HOST)
    ftps.login(FTP_USER, FTP_PASS)
    ftps.prot_p()
    ftps.cwd(FTP_PATH)
    with open(local_file, "rb") as f:
        ftps.storbinary(f"STOR {remote_file}", f)
    ftps.quit()
    print(f"✅ File caricato su {FTP_PATH}{remote_file}")


# === MAIN ===
if __name__ == "__main__":
    offerte = carica_offerte()
    if aggiorna_html(LOCAL_INDEX, offerte):
        upload_ftps(LOCAL_INDEX, "index.html")
        print("✅ Homepage aggiornata su Aruba con offerte Amazon.")
    else:
        print("⚠️ Nessuna modifica eseguita.")

