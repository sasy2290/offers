import os
import json
from datetime import datetime
from ftplib import FTP_TLS
import re
from io import BytesIO

FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH", "/www.techandmore.eu/")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOCAL_INDEX = os.path.join(BASE_DIR, "index.html")
LOCAL_JSON = os.path.join(BASE_DIR, "bot", "latest_offers.json")

print(f"📁 INDEX path: {LOCAL_INDEX}")
print(f"📁 JSON path: {LOCAL_JSON}")


def scarica_index_da_aruba():
    print(f"⬇️ Download index.html da {FTP_HOST} ...")
    try:
        with FTP_TLS(FTP_HOST) as ftp:
            ftp.login(FTP_USER, FTP_PASS)
            ftp.prot_p()
            ftp.cwd(FTP_PATH)
            bio = BytesIO()
            ftp.retrbinary("RETR index.html", bio.write)
            bio.seek(0)
            contenuto = bio.read().decode("utf-8")
            with open(LOCAL_INDEX, "w", encoding="utf-8") as f:
                f.write(contenuto)
        print("✅ index.html scaricato correttamente da Aruba.")
        return True
    except Exception as e:
        print(f"❌ Errore nel download: {e}")
        return False


def genera_html_offerte(offerte):
    blocchi = []
    for o in offerte:
        titolo = o.get("title", "Offerta Amazon")
        link = o.get("url", "#")
        prezzo = o.get("price", "")
        img = o.get("image", "https://www.techandmore.eu/logo.png")
        blocco = f"""
        <div style='text-align:center;margin:20px;'>
          <a href='{link}' target='_blank' style='text-decoration:none;color:#00bfff;'>
            <img src='{img}' alt='{titolo}' style='width:200px;border-radius:8px;display:block;margin:auto;'>
            <p style='font-size:16px;font-weight:bold;'>{titolo}</p>
            <p style='color:#ff9900;'>{prezzo}</p>
          </a>
        </div>"""
        blocchi.append(blocco)
    return "\n".join(blocchi)


def aggiorna_index():
    if not os.path.exists(LOCAL_INDEX):
        print(f"❌ index.html non trovato: {LOCAL_INDEX}")
        return False

    with open(LOCAL_INDEX, "r", encoding="utf-8") as f:
        html = f.read()

    if not os.path.exists(LOCAL_JSON):
        print("⚠️ latest_offers.json non trovato. Creo file di test...")
        sample = [
            {
                "title": "Echo Dot (5ª gen)",
                "url": "https://www.amazon.it/dp/B09B96V6YP?tag=techandmore05-21",
                "price": "Ora a 29,99 €",
                "image": "https://m.media-amazon.com/images/I/61M+I7y2vZL._AC_SL1000_.jpg"
            },
            {
                "title": "Fire TV Stick 4K",
                "url": "https://www.amazon.it/dp/B0B5YHXZ7T?tag=techandmore05-21",
                "price": "Scontata a 39,99 €",
                "image": "https://m.media-amazon.com/images/I/51CGbLz7kYL._AC_SL1000_.jpg"
            }
        ]
        os.makedirs(os.path.dirname(LOCAL_JSON), exist_ok=True)
        with open(LOCAL_JSON, "w", encoding="utf-8") as f:
            json.dump(sample, f, ensure_ascii=False, indent=2)
        offerte = sample
    else:
        with open(LOCAL_JSON, "r", encoding="utf-8") as f:
            offerte = json.load(f)
        print(f"✅ Caricate {len(offerte)} offerte dal JSON.")

    offerte_html = genera_html_offerte(offerte[:12])

    if "<!-- OFFERTE START -->" in html and "<!-- OFFERTE END -->" in html:
        nuovo_html = re.sub(
            r"<!-- OFFERTE START -->.*?<!-- OFFERTE END -->",
            f"<!-- OFFERTE START -->\n{offerte_html}\n<!-- OFFERTE END -->",
            html,
            flags=re.S
        )
    else:
        print("⚠️ Mancano i commenti di delimitazione nel file HTML.")
        nuovo_html = html

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    nuovo_html = re.sub(
        r"Aggiornato automaticamente[^<]*",
        f"Aggiornato automaticamente {now}",
        nuovo_html
    )

    with open(LOCAL_INDEX, "w", encoding="utf-8") as f:
        f.write(nuovo_html)

    print(f"🕒 index.html aggiornato localmente ({now})")
    return True


def carica_su_aruba():
    try:
        with FTP_TLS(FTP_HOST) as ftp:
            ftp.login(FTP_USER, FTP_PASS)
            ftp.prot_p()
            ftp.cwd(FTP_PATH)
            with open(LOCAL_INDEX, "rb") as f:
                ftp.storbinary("STOR index.html", f)
        print(f"✅ index.html caricato con successo su {FTP_PATH}")
    except Exception as e:
        print(f"❌ Errore FTP: {e}")


if __name__ == "__main__":
    if scarica_index_da_aruba():
        if aggiorna_index():
            carica_su_aruba()
            print("✅ Homepage aggiornata su Aruba tramite FTPS.")
