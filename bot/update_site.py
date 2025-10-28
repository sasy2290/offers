import os
import json
from datetime import datetime
from ftplib import FTP_TLS
import re
from io import BytesIO

# === CONFIG ===
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_PATH = os.getenv("FTP_PATH", "/www.techandmore.eu/")

# Percorsi assoluti
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LOCAL_INDEX = os.path.join(REPO_ROOT, "index.html")
LOCAL_JSON = os.path.join(REPO_ROOT, "bot", "latest_offers.json")

print(f"📁 INDEX path: {LOCAL_INDEX}")
print(f"📁 JSON path: {LOCAL_JSON}")


def scarica_index_da_aruba():
    """Scarica index.html da Aruba e lo salva in locale"""
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
            os.makedirs(os.path.dirname(LOCAL_INDEX), exist_ok=True)
            with open(LOCAL_INDEX, "w", encoding="utf-8") as f:
                f.write(contenuto)
        print("✅ index.html scaricato correttamente da Aruba.")
        return True
    except Exception as e:
        print(f"❌ Errore nel download: {e}")
        return False


def genera_html_offerte(offerte):
    """Genera blocco HTML per le offerte del JSON."""
    blocchi = []
    for o in offerte:
        titolo = o.get("titolo") or o.get("title") or "Offerta Amazon"
        link = o.get("link") or o.get("url") or "#"
        prezzo = o.get("prezzo") or o.get("price") or ""
        img = o.get("image") or "https://www.techandmore.eu/logo.png"

        blocco = f"""
        <div style="text-align:center; margin:20px;">
            <a href="{link}" target="_blank" style="text-decoration:none; color:#00bfff;">
                <img src="{img}" alt="{titolo}" style="width:200px; border-radius:8px; display:block; margin:auto;">
                <p style="font-size:16px; font-weight:bold;">{titolo}</p>
                <p style="color:#ff9900;">{prezzo}</p>
            </a>
        </div>
        """
        blocchi.append(blocco)
    return "\n".join(blocchi)


def aggiorna_index():
    """Aggiorna index.html scaricato con le nuove offerte"""
    if not os.path.exists(LOCAL_INDEX):
        print(f"❌ index.html non trovato: {LOCAL_INDEX}")
        return False

    with open(LOCAL_INDEX, "r", encoding="utf-8") as f:
        html = f.read()

    print(f"📂 Lettura JSON da: {LOCAL_JSON}")
    if not os.path.exists(LOCAL_JSON):
        print("⚠️ Nessun file latest_offers.json trovato.")
        offerte_html = "<p>Nessuna offerta disponibile.</p>"
    else:
        try:
            with open(LOCAL_JSON, "r", encoding="utf-8") as f:
                offerte = json.load(f)
            print(f"✅ Caricate {len(offerte)} offerte dal JSON.")
            offerte_html = genera_html_offerte(offerte[:12])
        except Exception as e:
            print(f"⚠️ Errore lettura JSON: {e}")
            offerte_html = "<p>Errore nel caricamento delle offerte.</p>"

    # Sostituisci solo la sezione OFFERTE
    if "<!-- OFFERTE START -->" in html and "<!-- OFFERTE END -->" in html:
        nuovo_html = re.sub(
            r"<!-- OFFERTE START -->.*?<!-- OFFERTE END -->",
            f"<!-- OFFERTE START -->\n{offerte_html}\n<!-- OFFERTE END -->",
            html,
            flags=re.S
        )
    else:
        print("⚠️ Commenti di delimitazione non trovati nel file HTML.")
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
    """Carica il file aggiornato su Aruba via FTPS"""
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
            print("⚠️ Nessuna modifica eseguita.")
