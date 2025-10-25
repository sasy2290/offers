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
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Offerte Amazon TechAndMore</title>
<style>
body {{ background-color: #0a0a0a; color: #0ff; font-family: Arial; }}
a {{ color: #4df; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.container {{ width: 90%; margin: 40px auto; }}
h1 {{ text-align: center; color: #00bfff; }}
.offer {{ border-bottom: 1px solid #333; padding: 10px 0; }}
small {{ color: #888; }}
</style>
</head>
<body>
<div class="container">
<h1>🔥 Offerte Amazon aggiornate {datetime.now().strftime("%d/%m/%Y %H:%M")} 🔥</h1>
"""
    for offer in offers[-50:][::-1]:
        link = offer.get("link", "#")
        title = offer.get("title", link)
        html += f'<div class="offer"><a href="{link}" target="_blank">{title}</a><br><small>{link}</small></div>\n'

    html += "</div></body></html>"
    return html

def upload_via_ftp(filepath):
    with FTP(FTP_HOST) as ftp:
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd("/")  # radice hosting Aruba
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
