import os
import ftplib
from datetime import datetime
import random
import re

# === CONFIG ===
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH", "/")
LOCAL_INDEX = "index.html"

def aggiorna_data_html(file_path):
    """Aggiorna la data e aggiunge cache-buster nel footer"""
    if not os.path.exists(file_path):
        print(f"❌ File non trovato: {file_path}")
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    rand_tag = random.randint(1000, 9999)

    # Aggiorna la scritta visibile o la aggiunge se non presente
    if "Aggiornato automaticamente" in html:
        html = re.sub(
            r"Aggiornato automaticamente[^<]*",
            f"Aggiornato automaticamente {now} <!-- {rand_tag} -->",
            html
        )
    else:
        html = html.replace(
            "</body>",
            f"\n<p style='text-align:center;color:#aaa;font-size:12px;'>Aggiornato automaticamente {now} <!-- {rand_tag} --></p>\n</body>"
        )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"🕒 Data aggiornata a {now}")
    return True


def upload_ftp(local_file, remote_file):
    """Carica il file via FTPS e rinomina per forzare pubblicazione"""
    try:
        ftps = ftplib.FTP_TLS(FTP_HOST)
        ftps.login(FTP_USER, FTP_PASS)
        ftps.prot_p()  # protezione TLS
        ftps.cwd(FTP_PATH)
        print(f"✅ Connessione riuscita, directory: {FTP_PATH}")

        temp_name = "index_temp.html"

        # carica file temporaneo
        with open(local_file, "rb") as f:
            ftps.storbinary(f"STOR {temp_name}", f)
        print(f"📤 Caricato {temp_name}")

        # elimina vecchio index.html se esiste
        try:
            ftps.delete("index.html")
        except Exception:
            pass

        # rinomina file temporaneo in index.html
        ftps.rename(temp_name, "index.html")
        print(f"🔁 Rinomina completata → index.html")

        ftps.quit()
        print("✅ Upload e pubblicazione completati.")

    except Exception as e:
        print(f"❌ Errore FTP: {e}")


if __name__ == "__main__":
    if aggiorna_data_html(LOCAL_INDEX):
        upload_ftp(LOCAL_INDEX, "index.html")
    else:
        print("⚠️ Nessuna modifica effettuata.")