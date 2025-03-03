import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from handlers import (
    user_id,
    process_message,
    chat_id,
    process_private_message,
    help,
    model,
    list_models,
    system_prompt,
    set_system_prompt,
    set_model,
)
import logfire
from config import logfire_api_key

logfire.configure(token=logfire_api_key)
load_dotenv()

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("_user_id", user_id))
    app.add_handler(CommandHandler("_chat_id", chat_id))
    app.add_handler(CommandHandler("private", process_private_message))
    app.add_handler(CommandHandler("system_prompt", system_prompt))
    app.add_handler(CommandHandler("set_system_prompt", set_system_prompt))
    app.add_handler(CommandHandler("models", list_models))
    app.add_handler(CommandHandler("model", model))
    app.add_handler(CommandHandler("set_model", set_model))
    app.add_handler(CommandHandler("help", help))

    # Handles non-command messages, sends to Agent, and returns reply.
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, process_message))

    app.run_polling()
