import os
import ftplib
from datetime import datetime

# === CONFIG ===
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = "/"
LOCAL_INDEX = "index.html"

def aggiorna_data_html(file_path):
    """Aggiorna la data e ora nel file index.html"""
    if not os.path.exists(file_path):
        print(f"❌ File non trovato: {file_path}")
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    updated_html = html

    # Aggiorna la scritta visibile "Aggiornato automaticamente..."
    if "Aggiornato automaticamente" in html:
        import re
        updated_html = re.sub(
            r"Aggiornato automaticamente[^<]*",
            f"Aggiornato automaticamente {now}",
            html
        )
    else:
        # Se non esiste, la aggiunge nel footer
        updated_html = html.replace(
            "</body>",
            f"\n<p style='text-align:center;color:#aaa;font-size:12px;'>Aggiornato automaticamente {now}</p>\n</body>"
        )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(updated_html)

    print(f"🕒 Data aggiornata a {now}")
    return True


def upload_ftp(local_file, remote_file):
    """Carica il file via FTP"""
    with ftplib.FTP(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(FTP_PATH)
        with open(local_file, "rb") as f:
            ftp.storbinary(f"STOR {remote_file}", f)
        print(f"✅ File caricato su {FTP_HOST}/{remote_file}")


if __name__ == "__main__":
    if aggiorna_data_html(LOCAL_INDEX):
        upload_ftp(LOCAL_INDEX, "index.html")
        print("✅ Homepage aggiornata su Aruba.")
    else:
        print("⚠️ Nessuna modifica effettuata, ma data aggiornata comunque.")
