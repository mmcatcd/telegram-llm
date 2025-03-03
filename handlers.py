from telegram import Update
from telegram.ext import CallbackContext
from telegram_utils import restricted
import sqlite_utils
import llm
from llm.cli import load_conversation, logs_db_path
from llm.migrations import migrate
from config import default_model_id
from datetime import datetime
from telegram.error import BadRequest


model_ids = [model_with_alias.model.model_id for model_with_alias in llm.get_models_with_aliases()]

MESSAGE_HISTORY_LIMIT = 100


async def user_id(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(f"Your user id is: {update.effective_user.id}")


@restricted
async def chat_id(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(f"Your chat id is: {update.effective_chat.id}")


@restricted
async def model(update: Update, context: CallbackContext) -> None:
    current_model_id = context.user_data.get("model_id", default_model_id)

    return await update.message.reply_text(
        f"Your current model id is: `{current_model_id}`",
        parse_mode="MARKDOWN",
    )


async def set_model(update: Update, context: CallbackContext) -> None:
    if not context.args or len(context.args) == 0:
        return await update.message.reply_text(
            "You must provide a valid model id like: `/set_model gpt-4o`",
            parse_mode="MARKDOWN",
        )
    
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


async def system_prompt(update: Update, context: CallbackContext) -> None:
    system_prompt = context.user_data.get("system_prompt", "")

    if system_prompt:
        return await update.message.reply_text(
            "The current system prompt is:\n\n"
            f"> {system_prompt}\n",
            parse_mode="MARKDOWN",
        )
        
    return await update.message.reply_text(
        "The system prompt is not currently set",
    )


async def set_system_prompt(update: Update, context: CallbackContext) -> None:
    if not context.args or len(context.args) == 0:
        context.user_data["system_prompt"] = ""
        return await update.message.reply_text(
            "The system prompt has been set to blank",
        )
    
    system_prompt = " ".join(context.args)
    context.user_data["system_prompt"] = system_prompt

    await update.message.reply_text(
        "Your system prompt has been updated to:\n\n"
        f"> {system_prompt}\n",
        parse_mode="MARKDOWN",
    )


async def list_models(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        f"\n".join("`/model " + model_id + "`" for model_id in model_ids),
        parse_mode="MARKDOWN",
    )


async def help(update: Update, context: CallbackContext) -> None:
    """Send a message with a list of available commands."""
    help_text = """
    Available commands:
    /private - Send a message in isolation of the chat conversation
        - Example: /private What is integer interning in python?
    /models - Get a list of available models that you can use
    /model - Get the current model being used
    /set_model - Set the model being used
    /system_prompt - Get the current system prompt being used
    /set_system_prompt - Set the system prompt
    /help - Show this help message
    """
    await update.message.reply_text(help_text)


@restricted
async def process_private_message(update: Update, context: CallbackContext) -> None:
    if not context.args:
        return await update.message.reply_text("You need to provide a message e.g., `/private My test message`", parse_mode="MARKDOWN")

    message_text = " ".join(context.args)
    model = llm.get_model(context.user_data.get("model_id", default_model_id))
    try:
        await update.message.reply_text(model.prompt(message_text).text(), parse_mode="MARKDOWN")
    except BadRequest:
        await update.message.reply_text(model.prompt(message_text).text())


def _get_user_conversations_table(db) -> None:
    user_conversations = db.table("user_conversations", pk=("user_id",))
    if not user_conversations.exists():
        user_conversations.create({
            "user_id": int,
            "conversation_id": str,
            "last_used": str,
        }, if_not_exists=True)

    return user_conversations


def _get_user_conversation_id(user_conversations_table, current_user_id: int) -> str | None:
    results = list(user_conversations_table.rows_where("user_id = ?", [current_user_id], limit=1))
    return results[0]["conversation_id"] if results else None


def _set_user_conversation_id(user_conversations_table, conversation_id: str, current_user_id: int) -> None:
    user_conversations_table.upsert({
        "user_id": current_user_id,
        "conversation_id": conversation_id,
        "last_used": datetime.now().isoformat(),
    }, pk="user_id")


@restricted
async def process_message(update: Update, context: CallbackContext) -> None:
    """Processes a message from the user, gets an answer, and sends it back."""

    current_user_id = update.effective_user.id

    db = sqlite_utils.Database(logs_db_path())
    migrate(db) # Migrate the DB before using it, as `log_to_db` doesn't do a migration

    user_conversations_table = _get_user_conversations_table(db)

    conversation_id = _get_user_conversation_id(user_conversations_table, current_user_id)
    model_id = context.user_data.get("model_id", default_model_id)
    model = llm.get_model(model_id)

    if not conversation_id:
        conversation = model.conversation()
        _set_user_conversation_id(user_conversations_table, conversation.id, current_user_id)
    else:
        conversation = load_conversation(conversation_id)
        
        # We have to explicitly change the model type to force it to switch.
        conversation.model = model

        # Explicitly setting the message limit so it doesn't cost me a bomb.
        conversation.responses = conversation.responses[-MESSAGE_HISTORY_LIMIT:]

    response = conversation.prompt(update.message.text)
    
    # Persisting the response to the SQLite DB to keep the conversation
    response.log_to_db(db)

    try:
        await update.message.reply_text(response.text(), parse_mode="MARKDOWN")
    except BadRequest:
        await update.message.reply_text(response.text())
