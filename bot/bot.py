import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError("Manca TELEGRAM_TOKEN nei Secrets o nelle variabili d'ambiente.")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Benvenuto! Usa /offers per ricevere gli ultimi best seller Amazon.")

async def offers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from update_offers import get_amazon_best_sellers
    categories = {
        "Elettronica": "https://www.amazon.it/gp/bestsellers/electronics",
        "Libri": "https://www.amazon.it/gp/bestsellers/books",
        "Casa": "https://www.amazon.it/gp/bestsellers/home",
    }

    for category, url in categories.items():
        try:
            items = get_amazon_best_sellers(url)
            text = f"<b>📦 Best Seller Amazon - {category}</b>\n"
            for i in items:
                text += f"{i['rank']}. {i['title']} — {i['price']}\n"
            await update.message.reply_html(text)
        except Exception as e:
            await update.message.reply_text(f"Errore su {category}: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("offers", offers))
    app.run_polling()

if __name__ == "__main__":
    main()
