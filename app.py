import os

import logfire
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from config import environment, logfire_api_key
from handlers import (
    attachment_types,
    chat_id,
    conversation_id,
    error_handler,
    help,
    list_models,
    model,
    process_message,
    process_private_message,
    set_model,
    set_system_prompt,
    system_prompt,
    user_id,
)

logfire.configure(token=logfire_api_key, environment=environment)
load_dotenv()

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("_user_id", user_id))
    app.add_handler(CommandHandler("_chat_id", chat_id))
    app.add_handler(CommandHandler("_conversation_id", conversation_id))
    app.add_handler(CommandHandler("private", process_private_message))
    app.add_handler(CommandHandler("system_prompt", system_prompt))
    app.add_handler(CommandHandler("set_system_prompt", set_system_prompt))
    app.add_handler(CommandHandler("models", list_models))
    app.add_handler(CommandHandler("model", model))
    app.add_handler(CommandHandler("set_model", set_model))
    app.add_handler(CommandHandler("attachment_types", attachment_types))
    app.add_handler(CommandHandler("help", help))

    # Handles non-command messages, sends to Agent, and returns reply.
    app.add_handler(
        MessageHandler(
            (
                filters.TEXT
                | filters.PHOTO
                | filters.AUDIO
                | filters.ATTACHMENT
                | filters.VIDEO
                | filters.VOICE
            )
            & ~filters.COMMAND,
            process_message,
        )
    )

    # Add error handler
    app.add_error_handler(error_handler)

    app.run_polling()
