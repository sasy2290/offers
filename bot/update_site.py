import os
import json
from datetime import datetime
from ftplib import FTP_TLS

# === CONFIG ===
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH", "/www.techandmore.eu/")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOCAL_INDEX = os.path.join(BASE_DIR, "index.html")
LOCAL_JSON = os.path.join(BASE_DIR, "bot", "latest_offers.json")

print(f"📁 Percorso INDEX: {LOCAL_INDEX}")
print(f"📁 Percorso JSON: {LOCAL_JSON}")


def scarica_index_da_aruba():
    print(f"⬇️ Download index.html da {FTP_HOST} ...")
    try:
        from io import BytesIO
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
    blocchi = [
        "<div style='display:flex;flex-wrap:wrap;justify-content:center;gap:20px;padding:20px;'>"
    ]

    for o in offerte:
        titolo = o.get("title", "Offerta Amazon")
        link = o.get("url", "#")
        prezzo = o.get("price", "")
        img = o.get(
            "image",
            "https://www.techandmore.eu/logo.png"
        )

        blocco = f"""
        <div style='background-color:#111;border:1px solid #222;border-radius:12px;
                    width:220px;padding:10px;text-align:center;box-shadow:0 0 10px #000;'>
            <a href='{link}' target='_blank' style='text-decoration:none;color:#00bfff;'>
                <img src='{img}' alt='{titolo}'
                     style='width:180px;height:180px;object-fit:contain;border-radius:8px;
                            background-color:#000;margin-bottom:10px;'>
                <p style='font-size:15px;font-weight:bold;color:#00bfff;margin:6px 0 4px 0;'>{titolo}</p>
                <p style='color:#ff9900;font-weight:bold;margin:0;'>{prezzo}</p>
            </a>
        </div>
        """
        blocchi.append(blocco)

    blocchi.append("</div>")
    return "\n".join(blocchi)



def aggiorna_index():
    if not os.path.exists(LOCAL_INDEX):
        print(f"❌ index.html non trovato: {LOCAL_INDEX}")
        return False

    with open(LOCAL_INDEX, "r", encoding="utf-8") as f:
        html = f.read()

    # Debug: mostra anteprima
    print("🧩 Preview index (prime 300 linee):")
    print(html[:500])

    # Carica JSON o crea di test
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

    # Sostituzione manuale del blocco
    start = html.find("<!-- OFFERTE START -->")
    end = html.find("<!-- OFFERTE END -->")
    if start != -1 and end != -1:
        nuovo_html = (
            html[:start]
            + f"<!-- OFFERTE START -->\n{offerte_html}\n<!-- OFFERTE END -->"
            + html[end + len("<!-- OFFERTE END -->"):]
        )
        print("✅ Blocco OFFERTE sostituito manualmente.")
    else:
        print("⚠️ Delimitatori non trovati. Nessuna modifica fatta.")
        nuovo_html = html

    # Aggiorna timestamp
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    if "Aggiornato automaticamente" in nuovo_html:
        import re
        nuovo_html = re.sub(
            r"Aggiornato automaticamente[^<]*",
            f"Aggiornato automaticamente {now}",
            nuovo_html
        )
    else:
        nuovo_html += f"\n<p style='text-align:center;color:#999;font-size:12px;'>Aggiornato automaticamente {now}</p>"

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
        else:
            print("⚠️ Nessuna modifica effettuata.")
