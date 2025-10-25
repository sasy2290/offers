import os
import ftplib
from datetime import datetime
import time
import random
import re

# === CONFIG ===
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = "/www.techandmore.eu/"
LOCAL_INDEX = "index.html"

def aggiorna_data_html(file_path):
    """Aggiorna data visibile + cache buster"""
    if not os.path.exists(file_path):
        print(f"❌ File non trovato: {file_path}")
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    uniq = str(int(time.time()))

    if "Aggiornato automaticamente" in html:
        html = re.sub(
            r"Aggiornato automaticamente[^<]*",
            f"Aggiornato automaticamente {now} <!-- {uniq} -->",
            html
        )
    else:
        html = html.replace(
            "</body>",
            f"\n<p style='text-align:center;color:#aaa;font-size:12px;'>Aggiornato automaticamente {now} <!-- {uniq} --></p>\n</body>"
        )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"🕒 Data aggiornata a {now}")
    return True


def upload_ftp(local_file):
    """Upload con doppia rinomina per forzare cache Aruba"""
    try:
        ftps = ftplib.FTP_TLS(FTP_HOST)
        ftps.login(FTP_USER, FTP_PASS)
        ftps.prot_p()
        ftps.cwd(FTP_PATH)
        print(f"✅ Connesso a {FTP_HOST}{FTP_PATH}")

        temp_a = f"index_a_{int(time.time())}.html"
        temp_b = f"index_b_{int(time.time())}.html"

        # 1️⃣ Carica file temporaneo A
        with open(local_file, "rb") as f:
            ftps.storbinary(f"STOR {temp_a}", f)
        print(f"📤 Caricato {temp_a}")

        # 2️⃣ Rinomina A→B per creare nuova entry cache
        ftps.rename(temp_a, temp_b)
        print(f"🔁 Rinomina {temp_a} → {temp_b}")

        # 3️⃣ Cancella vecchio index.html se esiste
        try:
            ftps.delete("index.html")
        except Exception:
            pass

        # 4️⃣ Rinomina B→index.html (forza refresh CDN)
        ftps.rename(temp_b, "index.html")
        print("✅ Pubblicato definitivamente index.html")

        ftps.quit()
        print("🏁 Upload e refresh cache completati.")

    except Exception as e:
        print(f"❌ Errore FTP: {e}")


if __name__ == "__main__":
    if aggiorna_data_html(LOCAL_INDEX):
        upload_ftp(LOCAL_INDEX)
    else:
        print("⚠️ Nessuna modifica effettuata.")