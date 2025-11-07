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
UPDATES_DIR = "updates/"


# ---------------- HTML OFFERTE ----------------

def build_offer_html(offer):
    img = offer.get("image", "")
    title = offer.get("title", "Offerta")
    price = offer.get("price", "")
    link = offer.get("url", "#")

    return f"""
    <div class="offer-card" data-cat="tech">
        <img src="{img}" class="offer-img">
        <div class="offer-title">{title}</div>
        <div class="offer-price">{price}</div>
        <a href="{link}" target="_blank" class="btn-buy">Vai all’offerta</a>
    </div>
    """


# ---------------- SNAPSHOT ----------------

def generate_snapshot(offers, timestamp):
    html_offers = "\n".join(build_offer_html(o) for o in offers)

    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Snapshot offerte {timestamp}</title>
  <link rel="stylesheet" href="../style.css">
</head>
<body>

<h1>Snapshot offerte — {timestamp}</h1>

<div class="offer-grid">
{html_offers}
</div>

<div class="footer">
  <p>Snapshot generato automaticamente</p>
  <p><a href="../">⬅ Torna alla Home</a></p>
</div>

</body>
</html>
"""


# ---------------- ARCHIVIO ----------------

def update_archive_list():
    files = sorted(
        [f for f in os.listdir(UPDATES_DIR) if f.startswith("update_") and f.endswith(".html")],
        reverse=True
    )

    items = "\n".join(
        f'<li><a href="{f}">{f.replace("update_", "").replace(".html", "")}</a></li>'
        for f in files
    )

    archive_html = f"""
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <title>Archivio offerte — TechAndMore</title>
  <link rel="stylesheet" href="../style.css">
</head>
<body>

<h1>Archivio offerte</h1>

<ul>
{items}
</ul>

<div class="footer">
  <p><a href="https://www.techandmore.eu">⬅ Torna alla Home</a></p>
</div>

</body>
</html>
"""

    with open(f"{UPDATES_DIR}/index.html", "w", encoding="utf-8") as f:
        f.write(archive_html)


# ---------------- INDEX.HTML ----------------

def update_index_html(offers):
    with open(LOCAL_INDEX, "r", encoding="utf-8") as f:
        html = f.read()

    start = "<!-- OFFERTE START -->"
    end = "<!-- OFFERTE END -->"

    block = "\n".join(build_offer_html(o) for o in offers)

    if start in html and end in html:
        before = html.split(start)[0]
        after = html.split(end)[1]
        new_html = before + start + "\n" + block + "\n" + end + after
    else:
        print("Delimitatori mancanti.")
        return

    with open(LOCAL_INDEX, "w", encoding="utf-8") as f:
        f.write(new_html)

    print("✅ Blocco offerte aggiornato.")


# ---------------- FTP UPLOAD ----------------

def ftp_upload(local, remote):
    with FTP_TLS(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        ftp.cwd(FTP_PATH)
        with open(local, "rb") as f:
            ftp.storbinary(f"STOR {remote}", f)
        print(f"✅ Caricato: {FTP_PATH}{remote}")


# ---------------- MAIN ----------------

def main():
    if not os.path.exists(UPDATES_DIR):
        os.makedirs(UPDATES_DIR)

    with open(LOCAL_JSON, "r", encoding="utf-8") as f:
        offers = json.load(f)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    # snapshot
    snap_path = f"{UPDATES_DIR}/update_{timestamp}.html"
    with open(snap_path, "w", encoding="utf-8") as f:
        f.write(generate_snapshot(offers, timestamp))

    # aggiorna archivio
    update_archive_list()

    # aggiorna index
    update_index_html(offers)

    # upload index
    ftp_upload("index.html", "index.html")

    # upload snapshot
    ftp_upload(snap_path, f"updates/update_{timestamp}.html")

    # upload archivio
    ftp_upload(f"{UPDATES_DIR}/index.html", "updates/index.html")

    print("✅ Archivio completo generato.")


if __name__ == "__main__":
    main()
