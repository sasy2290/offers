import os
import json
from datetime import datetime
from ftplib import FTP_TLS

FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH", "/www.techandmore.eu/")

LOCAL_INDEX = "index.html"
LOCAL_JSON = "bot/latest_offers.json"

# === HTML TEMPLATE PER UNA SINGOLA PAGINA DI AGGIORNAMENTO ===
def render_snapshot_html(offerte, timestamp):
    blocchi = ""
    for o in offerte:
        blocchi += f"""
        <div class="card">
            <a href="{o['link']}" target="_blank">
                <img src="{o['image']}" alt="{o['title']}">
                <h3>{o['title']}</h3>
                <p class="price">{o['price']}</p>
            </a>
        </div>
        """

    return f"""
<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Offerte {timestamp}</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>
<h1>Offerte Amazon del {timestamp}</h1>
<div class="grid">
{blocchi}
</div>
<p style="text-align:center;margin-top:40px;">
<a href="index.html">Torna allo storico</a>
</p>
</body>
</html>
"""


# === HTML PER LISTA COMPLETA DELLO STORICO ===
def render_storico_html(lista):
    righe = ""
    for t in lista:
        righe += f'<li><a href="{t}.html">{t}</a></li>'

    return f"""
<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Storico aggiornamenti</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>
<h1>Storico Aggiornamenti</h1>
<ul class="storico">
{righe}
</ul>
<p style="text-align:center;margin-top:40px;">
<a href="../index.html">Torna alla Home</a>
</p>
</body>
</html>
"""


# === GENERAZIONE HTML PER INDEX PRINCIPALE ===
def render_index_html(offerte, timestamp):
    blocchi = ""
    for o in offerte[:12]:
        blocchi += f"""
        <div class="card">
            <a href="{o['link']}" target="_blank">
                <img src="{o['image']}" alt="{o['title']}">
                <h3>{o['title']}</h3>
                <p class="price">{o['price']}</p>
            </a>
        </div>
        """

    return f"""
<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>TechAndMore — Offerte Amazon</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<h1>TechAndMore</h1>
<p>🔥 Offerte Amazon aggiornate automaticamente ogni 15 minuti</p>

<h2>Ultime offerte</h2>

<div class="grid">
{blocchi}
</div>

<p class="update">Aggiornato automaticamente {timestamp}</p>

<p style="text-align:center;margin-top:40px;">
<a href="updates/index.html">📁 Vai allo storico offerte</a>
</p>

</body>
</html>
"""


# === UPLOAD FTPS ===
def ftp_upload(path_remote, local_file):
    with FTP_TLS(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.prot_p()
        ftp.cwd(path_remote)
        with open(local_file, "rb") as f:
            ftp.storbinary(f"STOR {os.path.basename(local_file)}", f)


# === MAIN UPDATE ===
def main():
    if not os.path.exists(LOCAL_JSON):
        print("❌ JSON non trovato.")
        return

    with open(LOCAL_JSON, "r", encoding="utf-8") as f:
        offerte = json.load(f)

    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    nome_snapshot = f"{timestamp}.html"

    # 1) crea snapshot locale
    snapshot_html = render_snapshot_html(offerte, timestamp)
    os.makedirs("updates", exist_ok=True)
    path_snapshot = f"updates/{nome_snapshot}"
    with open(path_snapshot, "w", encoding="utf-8") as f:
        f.write(snapshot_html)

    # 2) aggiorna storico index
    storico_dir = "updates/index.html"
    files = sorted(
        [f.replace(".html", "") for f in os.listdir("updates") if f.endswith(".html") and f != "index.html"],
        reverse=True
    )
    with open(storico_dir, "w", encoding="utf-8") as f:
        f.write(render_storico_html(files))

    # 3) aggiorna index principale
    index_html = render_index_html(offerte, timestamp)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(index_html)

    # 4) upload su Aruba
    ftp_upload(FTP_PATH, "index.html")
    ftp_upload(FTP_PATH + "/updates", path_snapshot)
    ftp_upload(FTP_PATH + "/updates", "updates/index.html")

    print("✅ Aggiornamento completato.")


if __name__ == "__main__":
    main()
