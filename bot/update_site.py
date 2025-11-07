import os
import json
from datetime import datetime
from ftplib import FTP_TLS

# Config
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")

FTP_BASE = "/www.techandmore.eu"
FTP_UPDATES = "/www.techandmore.eu/updates"

LOCAL_INDEX = "index.html"
LOCAL_JSON = "bot/latest_offers.json"


def load_offers():
    if not os.path.exists(LOCAL_JSON):
        return []
    try:
        with open(LOCAL_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except:
        return []


def render_offer(o):
    title = o.get("titolo", "Offerta Amazon")
    link = o.get("link", "#")
    price = o.get("prezzo", "")
    img = o.get("image", "")

    return f"""
    <div class="offer-card">
        <a href="{link}" target="_blank">
            <img src="{img}" alt="img" class="offer-img">
            <p class="offer-title">{title}</p>
            <p class="offer-price">{price}</p>
        </a>
    </div>
    """


def render_snapshot_html(offers, timestamp):
    items = "\n".join(render_offer(o) for o in offers)
    return f"""
<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Archivio {timestamp}</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>
<h1>Archivio offerte {timestamp}</h1>
<div class="offer-grid">
{items}
</div>
</body>
</html>
"""


def render_archive_index(files):
    links = "\n".join(
        f'<li><a href="{name}" target="_blank">{name}</a></li>'
        for name in sorted(files, reverse=True)
    )
    return f"""
<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Archivio Offerte</title>
</head>
<body>
<h1>Archivio aggiornamenti</h1>
<ul>
{links}
</ul>
</body>
</html>
"""


def upload(path, remote_path):
    with FTP_TLS(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        with open(path, "rb") as f:
            ftp.storbinary(f"STOR {remote_path}", f)


def update_index(offers):
    if not os.path.exists(LOCAL_INDEX):
        return

    with open(LOCAL_INDEX, "r", encoding="utf-8") as f:
        html = f.read()

    start = "<!-- OFFERTE START -->"
    end = "<!-- OFFERTE END -->"

    if start not in html or end not in html:
        print("Delimitatori mancanti.")
        return

    grid = "\n".join(render_offer(o) for o in offers)

    new_html = html.split(start)[0] + start + "\n" + grid + "\n" + end + html.split(end)[1]

    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    new_html = new_html.replace("Aggiornato automaticamente", f"Aggiornato automaticamente {timestamp}")

    with open(LOCAL_INDEX, "w", encoding="utf-8") as f:
        f.write(new_html)

    upload(LOCAL_INDEX, f"{FTP_BASE}/index.html")


def main():
    offers = load_offers()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    # Aggiorna homepage
    update_index(offers)

    # Crea snapshot
    os.makedirs("updates", exist_ok=True)
    snap_path = f"updates/update_{timestamp}.html"

    with open(snap_path, "w", encoding="utf-8") as f:
        f.write(render_snapshot_html(offers, timestamp))

    upload(snap_path, f"{FTP_UPDATES}/update_{timestamp}.html")

    # Aggiorna lista archivio
    local_files = [f for f in os.listdir("updates") if f.startswith("update_")]

    archive_index_path = "updates/index.html"
    with open(archive_index_path, "w", encoding="utf-8") as f:
        f.write(render_archive_index(local_files))

    upload(archive_index_path, f"{FTP_UPDATES}/index.html")

    print("Completo.")


if __name__ == "__main__":
    main()
