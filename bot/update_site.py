import os
import ftplib
from datetime import datetime
import random
import time
import re

# === CONFIG ===
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = "/www.techandmore.eu/"
LOCAL_INDEX = "index.html"

def aggiorna_data_html(file_path):
    """Aggiorna la data visibile e aggiunge tag univoco"""
    if not os.path.exists(file_path):
        print(f"❌ File non trovato: {file_path}")
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    unique_tag = str(int(time.time()))

    if "Aggiornato automaticamente" in html:
        html = re.sub(r"Aggiornato automaticamente[^<]*",
                      f"Aggiornato automaticamente {now} <!-- {unique_tag} -->",
                      html)
    else:
        html = html.replace("</body>",
                            f"\n<p style='text-align:center;color:#aaa;font-size:12px;'>Aggiornato automaticamente {now} <!-- {unique_tag} --></p>\n</body>")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"🕒 Data aggiornata a {now}")
    return True


def upload_ftp(local_file):
    """Forza aggiornamento su Aruba"""
    temp_name = f"index_{int(time.time())}.html"
    try:
        ftps = ftplib.FTP_TLS(FTP_HOST)
        ftps.login(FTP_USER, FTP_PASS)
        ftps.prot_p()
        ftps.cwd(FTP_PATH)
        print(f"✅ Connessione FTPS → {FTP_PATH}")

        # carica file temporaneo
        with open(local_file, "rb") as f:
            ftps.storbinary(f"STOR {temp_name}", f)
        print(f"📤 Caricato temporaneo: {temp_name}")

        # elimina vecchio index.html
        try:
            ftps.delete("index.html")
        except Exception:
            pass

        # rinomina il file temporaneo in index.html
        ftps.rename(temp_name, "index.html")
        print("🔁 Rinomina forzata completata → index.html")

        ftps.quit()
        print("✅ Pubblicazione forzata completata su Aruba.")
    except Exception as e:
        print(f"❌ Errore FTP: {e}")


if __name__ == "__main__":
    if aggiorna_data_html(LOCAL_INDEX):
        upload_ftp(LOCAL_INDEX)
    else:
        print("⚠️ Nessuna modifica.")