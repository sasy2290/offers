import os
import json
from datetime import datetime
from ftplib import FTP

CACHE_FILE = "bot/posted_cache.json"
HTML_FILE = "site/index.html"

FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return []
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_html(offers):
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TechAndMore - Offerte Amazon aggiornate</title>
<style>
body {{
  background-color: #01010f;
  background-image: radial-gradient(circle at 50% 20%, #001833, #000);
  color: #00e5ff;
  font-family: 'Segoe UI', Arial, sans-serif;
  margin: 0;
  padding: 0;
  text-align: center;
}}
h1 {{
  font-size: 2.5em;
  margin-top: 30px;
  color: #00bfff;
  text-shadow: 0 0 15px #00bfff;
}}
.container {{
  width: 90%;
  max-width: 800px;
  margin: 40px auto;
  background-color: rgba(0, 0, 30, 0.6);
  border: 1px solid #0ff;
  border-radius: 10px;
  padding: 25px;
  box-shadow: 0 0 20px #00bfff;
}}
.offer {{
  border-bottom: 1px solid rgba(0,255,255,0.2);
  padding: 10px 0;
}}
.offer a {{
  color: #00e5ff;
  font-size: 1.1em;
  text-decoration: none;
}}
.offer a:hover {{
  text-shadow: 0 0 10px #00ffff;
}}
small {{
  color: #0099cc;
  display: block;
  margin-top: 5px;
}}
button.telegram {{
  margin-top: 25px;
  background: linear-gradient(90deg, #0078ff, #00f7ff);
  border: none;
  color: white;
  font-size: 1.2em;
  padding: 12px 25px;
  border-radius: 8px;
  cursor: pointer;
  box-shadow: 0 0 15px #00ffff;
  transition: all 0.2s ease-in-out;
}}
button.telegram:hover {{
  transform: scale(1.05);
  box-shadow: 0 0 25px #00ffff;
}}
.footer {{
  margin-top: 30px;
  font-size: 0.9em;
  color: #00a3cc;
}}
</style>
</head>
<body>
  <h1>🔥 Offerte Amazon aggiornate {now} 🔥</h1>
  <div class="container">
"""

    for offer in offers[-50:][::-1]:
        link = offer.get("link", "#")
        title = offer.get("title", link)
        html += f'<div class="offer"><a href="{link}" target="_blank">{title}</a><small>{link}</small></div>\n'

    html += """
  </div>
  <button class="telegram" onclick="window.open('https://t.me/amazontechandmore','_blank')">
    📱 Segui il canale Telegram
  </button>
  <div class="footer">© TechAndMore.eu - Tutti i diritti riservati</div>
</body>
</html>
"""
    return html


def upload_via_ftp(filepath):
    with FTP(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd("/")  # radice Aruba
        with open(filepath, "rb") as f:
            ftp.storbinary("STOR index.html", f)
    print("✅ Homepage aggiornata su Aruba.")


def main():
    offers = load_cache()
    if not offers:
        print("⚠️ Nessuna offerta trovata nel file cache.")
        return
    html = build_html(offers)
    os.makedirs(os.path.dirname(HTML_FILE), exist_ok=True)
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    upload_via_ftp(HTML_FILE)


if __name__ == "__main__":
    main()
