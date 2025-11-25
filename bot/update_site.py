import os
import json
from ftplib import FTP_TLS

LATEST_JSON = "bot/latest_offers.json"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ultime Offerte Amazon</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #fafafa;
        }}
        h1 {{
            text-align: center;
        }}
        .offer {{
            margin-bottom: 25px;
            padding: 15px;
            background: #fff;
            border-radius: 8px;
            border: 1px solid #ddd;
        }}
        .price {{
            font-size: 18px;
            color: #d32f2f;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <h1>🔥 Ultime Offerte Amazon</h1>
    {offers}
</body>
</html>
"""

def generate_html(offers):
    blocks = []
    for offer in offers:
        block = f"""
        <div class="offer">
            <h2>{offer['title']}</h2>
            <p class="price">{offer['price']}</p>
            <p><a href="{offer['url']}" target="_blank">Vai all'offerta</a></p>
        </div>
        """
        blocks.append(block)
    return HTML_TEMPLATE.format(offers="\n".join(blocks))

def upload_file_ftp(local_path, remote_path):
    host = os.getenv("FTP_HOST")
    user = os.getenv("FTP_USER")
    password = os.getenv("FTP_PASS")
    ftp_path = os.getenv("FTP_PATH")

    ftps = FTP_TLS(host)
    ftps.login(user, password)
    ftps.prot_p()
    ftps.cwd(ftp_path)

    with open(local_path, "rb") as f:
        ftps.storbinary(f"STOR {remote_path}", f)

    ftps.quit()
    print(f"Caricato: {remote_path}")

def main():
    if not os.path.exists(LATEST_JSON):
        print("Nessun file JSON trovato.")
        return

    with open(LATEST_JSON, "r", encoding="utf-8") as f:
        offers = json.load(f)

    html = generate_html(offers[:20])

    local_file = "index.html"
    with open(local_file, "w", encoding="utf-8") as f:
        f.write(html)

    upload_file_ftp(local_file, "index.html")
    print("Sito aggiornato!")

if __name__ == "__main__":
    main()

