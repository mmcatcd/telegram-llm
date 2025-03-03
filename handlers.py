from telegram import Update
from telegram.ext import CallbackContext
from model_providers import get_current_user_model
from telegram_utils import restricted
import sqlite_utils
import llm
from llm.cli import load_conversation, logs_db_path
from llm.migrations import migrate
from config import default_model_id


model_ids = [model_with_alias.model.model_id for model_with_alias in llm.get_models_with_aliases()]

MESSAGE_HISTORY_LIMIT = 100


async def user_id(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(f"Your user id is: {update.effective_user.id}")


@restricted
async def chat_id(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(f"Your chat id is: {update.effective_chat.id}")


@restricted
async def model(update: Update, context: CallbackContext) -> None:
    """Change the LLM model used by the bot for this user.
    Usage: /model [provider] [model_id]
    Examples: 
      /model anthropic claude-3-7-sonnet-latest
      /model openai gpt-4o
    If no arguments are provided, it shows the current model."""

    current_model_id = context.user_data.get("model_id", default_model_id)

    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            f"Your current model provider is: `{current_model_id}`\n"
            f"To change the model, use: /model [model_id]\n"
            f"Examples:\n"
            f"  `/model openai gpt-4o`",
            parse_mode="MARKDOWN",
        )
        return
    
    model_id = context.args[0]

    if not model_id in model_ids:
        await update.message.reply_text(
            f"Your chosen model id: {model_id} is invalid. Please choose a valid model id.\n"
            "To find a list of valid model ids, use: /list_models"
        )

    # Update the user's model preference
    context.user_data["model_id"] = model_id

    await update.message.reply_text(
        f"Your model id has been changed to: `{model_id}`\n",
        parse_mode="MARKDOWN",
    )


@restricted
async def get_model(update: Update, context: CallbackContext) -> str:
    await update.message.reply_text(get_current_user_model(context).model_string)


async def list_models(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        f"\n".join("`/model " + model_id + "`" for model_id in model_ids),
        parse_mode="MARKDOWN",
    )


async def help(update: Update, context: CallbackContext) -> None:
    """Send a message with a list of available commands."""
    help_text = """
    Available commands:
    /list_models - Get a list of available models that you can use
    /model - Set the model id to use
    /private - Send a message in isolation of the chat conversation
        - Example: `/private What is integer interning in python?`
    /user_id - Get your Telegram user ID
    /chat_id - Get the current chat ID
    /help - Show this help message
    """
    await update.message.reply_text(help_text, parse_mode="MARKDOWN")


@restricted
async def process_private_message(update: Update, context: CallbackContext) -> None:
    message_text = " ".join(context.args)
    model = llm.get_model(context.user_data.get("model_id", default_model_id))
    await update.message.reply_text(model.prompt(message_text).text(), parse_mode="MARKDOWN")


@restricted
async def process_message(update: Update, context: CallbackContext) -> None:
    """Processes a message from the user, gets an answer, and sends it back."""

    conversation_id = context.user_data.get("conversation_id")
    model_id = context.user_data.get("model_id", default_model_id)
    model = llm.get_model(model_id)

    db = sqlite_utils.Database(logs_db_path())
    migrate(db) # Migrate the DB before using it, as `log_to_db` doesn't do a migration

    if not conversation_id:
        conversation = model.conversation()
        context.user_data["conversation_id"] = conversation.id
    else:
        conversation = load_conversation(conversation_id)
        
        # We have to explicitly change the model type to force it to switch.
        conversation.model = model

        # Explicitly setting the message limit so it doesn't cost me a bomb.
        conversation.responses = conversation.responses[-MESSAGE_HISTORY_LIMIT:]

    response = conversation.prompt(update.message.text)
    
    # Persisting the response to the SQLite DB to keep the conversation
    response.log_to_db(db)

    await update.message.reply_text(response.text(), parse_mode="MARKDOWN")
