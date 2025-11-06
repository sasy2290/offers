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


def load_json():
    if not os.path.exists(LOCAL_JSON):
        return []
    try:
        with open(LOCAL_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


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


def upload_file(filename, remote_path):
    with FTP_TLS(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        ftp.cwd(remote_path)
        with open(filename, "rb") as f:
            ftp.storbinary(f"STOR {os.path.basename(filename)}", f)
    print(f"✅ Caricato: {remote_path}/{os.path.basename(filename)}")


def generate_archive(offers):
    now = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"update_{now}.html"
    local_path = filename

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


if __name__ == "__main__":
    offers = load_json()

    if offers:
        update_index(offers)

        archive_local, archive_name = generate_archive(offers)

        upload_file(LOCAL_INDEX, FTP_PATH)
        upload_file(archive_local, FTP_PATH + "updates/")

        print("✅ Archivio salvato.")
    else:
        print("⚠️ Nessuna offerta trovata.")
