import os
import ftplib

FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_ROOT = "/"  # root del sito
FTP_UPDATES = "/updates"

LOCAL_JSON = "latest_offers.json"
LOCAL_UPDATES_DIR = "updates_html"


def upload_file(ftps, local_path, remote_path):
    print(f"Uploading: {remote_path}")
    with open(local_path, "rb") as f:
        ftps.storbinary(f"STOR {remote_path}", f)
    print("OK!")


def main():
    print("Connecting to FTP...")
    ftps = ftplib.FTP_TLS()
    ftps.connect(FTP_HOST, 21)
    ftps.login(FTP_USER, FTP_PASS)
    ftps.prot_p()

    print("Connected!")

    # Upload SOLO il latest_offers.json nella root
    if os.path.exists(LOCAL_JSON):
        upload_file(ftps, LOCAL_JSON, f"{FTP_ROOT}/latest_offers.json")
    else:
        print("ERROR: latest_offers.json non trovato!")

    # Carica HTML archivio in /updates/
    if os.path.isdir(LOCAL_UPDATES_DIR):

        # crea cartella updates se non esiste
        try:
            ftps.mkd(FTP_UPDATES)
        except:
            pass

        for file in os.listdir(LOCAL_UPDATES_DIR):
            local_file = os.path.join(LOCAL_UPDATES_DIR, file)
            remote_file = f"{FTP_UPDATES}/{file}"
            upload_file(ftps, local_file, remote_file)

    ftps.quit()
    print("DONE.")


if __name__ == "__main__":
    main()
