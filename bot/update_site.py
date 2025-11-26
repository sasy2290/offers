def upload_site():
    """
    Carica SOLO latest_offers.json nella root FTP.
    NON tocca index.html.
    """
    print("🌐 Upload JSON via FTPS...")

    ftps = FTP_TLS(FTP_HOST)
    ftps.login(FTP_USER, FTP_PASS)
    ftps.prot_p()

    remote_base = f"/{FTP_PATH}".rstrip("/")

    if remote_base:
        ftps.cwd(remote_base)

    # upload latest_offers.json
    if os.path.exists(LATEST_JSON):
        with open(LATEST_JSON, "rb") as f:
            ftps.storbinary("STOR latest_offers.json", f)
        print("⬆️ Caricato: latest_offers.json")
    else:
        print("⚠️ latest_offers.json non trovato")

    ftps.quit()
    print("✅ Upload completato")
