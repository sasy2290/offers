import os
import json
from datetime import datetime
from ftplib import FTP_TLS

FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = "/www.techandmore.eu/"

LOCAL_INDEX = "index.html"
LOCAL_JSON = "bot/latest_offers.json"


# === CARICA JSON OFFERTE ===
def load_json():
    if not os.path.exists(LOCAL_JSON):
        return []
    try:
        with open(LOCAL_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


# === CREA HTML OFFERTE ===
def build_offers_html(offers):
    html = ""
    for o in offers:
        html += f"""
<div class='offer-card'>
    <a href='{o["url"]}' target='_blank'>
        <img src='{o["image"]}' class='offer-img'>
        <div class='offer-title'>{o["title"]}</div>
        <div class='offer-price'>{o["price"]}</div>
    </a>
</div>
"""
    return html


# === AGGIORNA LA HOME INDEX ===
def update_index(offers):
    if not os.path.exists(LOCAL_INDEX):
        print("❌ index.html mancante.")
        return False

    with open(LOCAL_INDEX, "r", encoding="utf-8") as f:
        html = f.read()

    offers_block = build_offers_html(offers)
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    if "<!-- OFFERTE START -->" in html:
        start = html.split("<!-- OFFERTE START -->")[0]
        end = html.split("<!-- OFFERTE END -->")[1]

        new_html = (
            start
            + "<!-- OFFERTE START -->\n"
            + offers_block
            + "\n<!-- OFFERTE END -->"
            + end
        )
    else:
        print("⚠️ Delimitatori mancanti.")
        return False

    new_html = new_html.replace("Aggiornato automaticamente", f"Aggiornato automaticamente {now}")

    with open(LOCAL_INDEX, "w", encoding="utf-8") as f:
        f.write(new_html)

    return True


# === UPLOAD FILE VIA FTPS ===
def upload_file(filename, remote_path):
    with FTP_TLS(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        ftp.cwd(remote_path)
        with open(filename, "rb") as f:
            ftp.storbinary(f"STOR {os.path.basename(filename)}", f)
    print(f"✅ Caricato: {remote_path}/{os.path.basename(filename)}")


# === CREA PAGINA ARCHIVIO SINGOLO ===
def generate_archive(offers):
    now = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"update_{now}.html"
    local_path = f"updates/{filename}"

    block = build_offers_html(offers)

    html = f"""
<!DOCTYPE html>
<html lang='it'>
<head>
<meta charset='UTF-8'>
<title>Archivio offerte {now}</title>
<link rel='stylesheet' href='../style.css'>
</head>
<body>
<h2>Archivio aggiornamento {now}</h2>
{block}
</body>
</html>
"""

    with open(local_path, "w", encoding="utf-8") as f:
        f.write(html)

    return local_path, filename


# === CREA /updates/index.html CON LISTA SNAPSHOT ===
def generate_archive_index():
    entries = []

    for f in os.listdir("updates"):
        if f.startswith("update_") and f.endswith(".html"):
            entries.append(f)

    entries.sort(reverse=True)

    lista = ""

    for name in entries:
        timestamp = name.replace("update_", "").replace(".html", "")
        lista += f"<li><a href='{name}'>{timestamp}</a></li>\n"

    html = f"""
<!DOCTYPE html>
<html lang='it'>
<head>
<meta charset='UTF-8'>
<title>Storico aggiornamenti</title>
<link rel='stylesheet' href='../style.css'>
</head>
<body>
<h1>Storico aggiornamenti</h1>
<ul>
{lista}
</ul>
<p><a href='../index.html'>Torna alla Home</a></p>
</body>
</html>
"""

    with open("updates/index.html", "w", encoding="utf-8") as f:
        f.write(html)

    return "updates/index.html"


# === MAIN ===
if __name__ == "__main__":
    offers = load_json()

    if offers:
        update_index(offers)

        # snapshot
        archive_local, archive_name = generate_archive(offers)

        # storico
        archive_index = generate_archive_index()

        # upload
        upload_file(LOCAL_INDEX, FTP_PATH)
        upload_file(archive_local, FTP_PATH + "updates/")
        upload_file(archive_index, FTP_PATH + "updates/")

        print("✅ Archivio completo generato.")
    else:
        print("⚠️ Nessuna offerta trovata.")
