# Amazon Best Seller Bot 🤖

Bot Telegram che invia ogni 15 minuti i best seller Amazon (Elettronica, Libri, Casa) tramite GitHub Actions.
Può anche rispondere manualmente ai comandi /offers e /start.

## Struttura del progetto
```
bot/
 ├── bot.py
 ├── update_offers.py
 ├── requirements.txt
.github/
 └── workflows/
      └── cron.yml
```

## Configurazione
1. Crea un Bot Telegram con @BotFather e ottieni il token.
2. Crea un repository GitHub e aggiungi:
   - TELEGRAM_TOKEN
   - CHAT_ID
   nei Secrets (Settings → Secrets → Actions).
3. Il bot invierà messaggi automatici ogni 15 minuti.

## Esecuzione manuale
```
pip install -r bot/requirements.txt
python bot/bot.py
```
