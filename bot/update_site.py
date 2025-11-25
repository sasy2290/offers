import os
import json
import ftplib
from ftplib import FTP_TLS

# ======================================
# Carica variabili ambiente GitHub Actions
# ======================================
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH", "").strip("/")

LOCAL_FILES = [
    "index.html",
    "bot/latest_offers.json"
]

LOCAL_UPDATES_DIR = "bot/updates"

# ======================================
# Connessione FTPS
# ======================================
def connect_ftps():
    ftps = FTP_TLS()
    ftps.connect(FTP_HOST, 21)
    ftps.login(FTP_USER, FTP_PASS)

    # Modalità sicura TLS
    ftps.prot_p()
    ftps.encoding = "utf-8"

    print("🔐 Connesso via FTPS")
    return ftps

# ======================================
# Effettua l'upload di un singolo file
# ======================================
def upload_file(ftps, local_path, remote_path):
    remote_path = remote_path.replace("//", "/")

    try:
        with open(local_path, "rb") as f:
            ftps.storbinary(f"STOR {remote_path}", f)
        print(f"⬆️  Caricato: {remote_path}")
    except Exception as e:
        print(f"❌ Errore nel caricare {local_path}: {e}")

# ======================================
# Crea directory remote se mancanti
# ======================================
def ensure_remote_dir(ftps, path):
    parts = path.split("/")
    current = ""

    for p in parts:
        if not p:
            continue
        current += f"/{p}"
        try:
            ftps.mkd(current)
            print(f"📁 Creata cartella: {current}")
        except:
            pass  # già esiste

# ======================================
# Upload principale
# ======================================
def main():
    ftps = connect_ftps()

    # Percorso sul server
    base_remote = f"/{FTP_PATH}".strip("/")

    ensure_remote_dir(ftps, base_remote)

    # -------------------------
    # UPLOAD FILE PRINCIPALI
    # -------------------------
    for file in LOCAL_FILES:
        if os.path.exists(file):
            remote_file = f"{base_remote}/{os.path.basename(file)}"
            upload_file(ftps, file, remote_file)
        else:
            print(f"⚠️ File non trovato localmente: {file}")

    # -------------------------
    # UPLOAD CARTELLA UPDATES
    # -------------------------
    if os.path.exists(LOCAL_UPDATES_DIR):
        for fname in os.listdir(LOCAL_UPDATES_DIR):
            local_file = os.path.join(LOCAL_UPDATES_DIR, fname)
            remote_file = f"{base_remote}/updates/{fname}"

            ensure_remote_dir(ftps, f"{base_remote}/updates")

            upload_file(ftps, local_file, remote_file)

    print("✅ Sito aggiornato!")
    ftps.quit()

if __name__ == "__main__":
    main()
