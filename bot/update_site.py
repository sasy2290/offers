import os
from ftplib import FTP_TLS

FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH").strip("/")

LOCAL_INDEX = "index.html"
LOCAL_JSON = "bot/latest_offers.json"

REMOTE_INDEX = "index.html"
REMOTE_JSON = "latest_offers.json"

def connect():
    ftps = FTP_TLS(FTP_HOST)
    ftps.login(FTP_USER, FTP_PASS)
    ftps.prot_p()
    ftps.encoding = "utf-8"
    print("🔐 Connesso FTPS")
    return ftps

def upload(ftps, local_path, remote_path):
    with open(local_path, "rb") as f:
        ftps.storbinary(f"STOR " + remote_path, f)
    print(f"⬆️  Caricato: {remote_path}")

def main():
    if not os.path.exists(LOCAL_JSON):
        print("❌ ERRORE: latest_offers.json NON ESISTE in bot/")
        return

    ftps = connect()
    ftps.cwd("/" + FTP_PATH)

    # carica JSON
    upload(ftps, LOCAL_JSON, REMOTE_JSON)

    # carica index.html
    if os.path.exists(LOCAL_INDEX):
        upload(ftps, LOCAL_INDEX, REMOTE_INDEX)
    else:
        print("⚠️ index.html non trovato in locale")

    ftps.quit()
    print("✅ Sito aggiornato!")

if __name__ == "__main__":
    main()
