from datetime import datetime
from inspect import cleandoc

import llm
import logfire
import sqlite_utils
from llm.cli import load_conversation, logs_db_path
from llm.migrations import migrate
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext

from config import default_model_id
from telegram_utils import restricted, send_long_message

# Get all available model IDs
model_ids = [
    model_with_alias.model.model_id
    for model_with_alias in llm.get_models_with_aliases()
]

# Dictionary mapping model IDs to their knowledge cutoff dates
# Fill in the accurate cutoff dates from provider documentation
model_cutoffs = {
    # OpenAI models
    "gpt-4o": "April 2023",
    "gpt-3.5-turbo": "September 2021",
    
    # Anthropic models
    "anthropic/claude-3-opus-20240229": "August 2023",
    "anthropic/claude-3-sonnet-20240229": "August 2023",
    
    # Add more models and their cutoff dates here
}

MESSAGE_HISTORY_LIMIT = 15


async def user_id(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(f"Your user id is: {update.effective_user.id}")


@restricted
async def chat_id(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(f"Your chat id is: {update.effective_chat.id}")


@restricted
async def model(update: Update, context: CallbackContext) -> None:
    current_model_id = context.user_data.get("model_id", default_model_id)

    return await send_long_message(
        update,
        context,
        f"Your current model id is: `{current_model_id}`",
        parse_mode="MarkdownV2",
    )


@restricted
async def set_model(update: Update, context: CallbackContext) -> None:
    if not context.args or len(context.args) == 0:
        return await update.message.reply_text(
            "You must provide a valid model id like: `/set_model gpt-4o`",
            parse_mode="MARKDOWN",
        )

    model_id = context.args[0]

    if model_id not in model_ids:
        return await send_long_message(
            update,
            context,
            f"Your chosen model id: {model_id} is invalid. Please choose a valid model id.\n"
            "To find a list of valid model ids, use: /list_models",
            parse_mode="Markdown",
        )

    # Update the user's model preference
    context.user_data["model_id"] = model_id

    await send_long_message(
        update,
        context,
        f"Your model id has been changed to: `{model_id}`\n",
        parse_mode="Markdown",
    )


@restricted
async def system_prompt(update: Update, context: CallbackContext) -> None:
    system_prompt = context.user_data.get("system_prompt", "")

    if system_prompt:
        return await send_long_message(
            update,
            context,
            f"The current system prompt is:\n\n> {system_prompt}\n",
            parse_mode="Markdown",
        )

    return await update.message.reply_text(
        "The system prompt is not currently set",
    )


@restricted
async def set_system_prompt(update: Update, context: CallbackContext) -> None:
    if not context.args or len(context.args) == 0:
        context.user_data["system_prompt"] = ""
        return await send_long_message(
            update,
            context,
            "The system prompt has been set to blank",
            parse_mode="Markdown",
        )

    system_prompt = " ".join(context.args)
    context.user_data["system_prompt"] = system_prompt

    await send_long_message(
        update,
        context,
        f"Your system prompt has been updated to:\n\n> {system_prompt}\n",
        parse_mode="Markdown",
    )


@restricted
async def list_models(update: Update, context: CallbackContext) -> None:
    model_details = []
    for model_id in model_ids:
        cutoff = model_cutoffs.get(model_id, "Unknown")
        model_details.append(f"• *{model_id}*\n  ↳ Knowledge cutoff: {cutoff}")
        
    await send_long_message(
        update,
        context,
        "\n".join(model_details),
        parse_mode="Markdown",
    )


@restricted
async def attachment_types(update: Update, context: CallbackContext) -> None:
    model_id = context.user_data.get("model_id", default_model_id)
    model = llm.get_model(model_id)
    attachment_types = "\n".join("- " + type for type in model.attachment_types)
    await update.message.reply_text(
        f"Supported attachment types are:\n{attachment_types}",
    )


async def help(update: Update, context: CallbackContext) -> None:
    """Send a message with a list of available commands."""
    help_text = cleandoc("""
    Available commands:
    `/private` - Send a message in isolation of the chat conversation
        - Example: `/private What is integer interning in python?`
    `/models` - Get a list of available models with their knowledge cutoff dates
    `/model` - Get the current model being used
    `/set_model` - Set the model being used
    `/system_prompt` - Get the current system prompt being used
    `/set_system_prompt` - Set the system prompt
    `/attachment_types` - Get the attachment types supported by the current model
    `/help` - Show this help message
    """)
    await send_long_message(update, context, help_text, parse_mode="Markdown")


@restricted
async def process_private_message(update: Update, context: CallbackContext) -> None:
    if not context.args:
        return await update.message.reply_text(
            "You need to provide a message e.g., `/private My test message`",
            parse_mode="MARKDOWN",
        )

    message_text = " ".join(context.args)
    model = llm.get_model(context.user_data.get("model_id", default_model_id))
    response = model.prompt(message_text)

    try:
        response_text = response.text()
    except Exception as e:
        await update.message.reply_text(
            f"Something went wrong when trying to call the LLM: {e}"
        )
        logfire.error(e)
        return

    try:
        await send_long_message(update, context, response_text, parse_mode="Markdown")
    except BadRequest:
        await send_long_message(update, context, response_text, parse_mode=None)

    logfire.info(f"Message: {response_text} Usage: {response.usage()}")


def _get_user_conversations_table(db) -> None:
    user_conversations = db.table("user_conversations", pk=("user_id",))
    if not user_conversations.exists():
        user_conversations.create(
            {
                "user_id": int,
                "conversation_id": str,
                "last_used": str,
            },
            if_not_exists=True,
        )

    return user_conversations


def _get_user_conversation_id(
    user_conversations_table, current_user_id: int
) -> str | None:
    results = list(
        user_conversations_table.rows_where("user_id = ?", [current_user_id], limit=1)
    )
    return results[0]["conversation_id"] if results else None


def _set_user_conversation_id(
    user_conversations_table, conversation_id: str, current_user_id: int
) -> None:
    user_conversations_table.upsert(
        {
            "user_id": current_user_id,
            "conversation_id": conversation_id,
            "last_used": datetime.now().isoformat(),
        },
        pk="user_id",
    )


@restricted
async def process_message(update: Update, context: CallbackContext) -> None:
    """Processes a message from the user, gets an answer, and sends it back."""

    # Send a "Thinking..." message first
    thinking_message = await update.message.reply_text("...")

    current_user_id = update.effective_user.id

    db = sqlite_utils.Database(logs_db_path())
    migrate(db)  # Migrate the DB before using it, as `log_to_db` doesn't do a migration

    user_conversations_table = _get_user_conversations_table(db)

    conversation_id = _get_user_conversation_id(
        user_conversations_table, current_user_id
    )
    model_id = context.user_data.get("model_id", default_model_id)
    model = llm.get_model(model_id)

    if not conversation_id:
        conversation = model.conversation()
        _set_user_conversation_id(
            user_conversations_table, conversation.id, current_user_id
        )
    else:
        conversation = load_conversation(conversation_id)
        conversation.model = model
        conversation.responses = conversation.responses[-MESSAGE_HISTORY_LIMIT:]
        logfire.info(f"Number of responses: {len(conversation.responses)}")

    attachments = []
    message_text = (
        update.message.text if update.message.text else update.message.caption
    )
    logfire.info(f"Prompt: {message_text}")

    # Handle different types of attachments
    if update.message.photo:
        if "image/jpeg" not in model.attachment_types:
            await thinking_message.edit_text(
                "The current model doesn't support image attachments. "
                "Please switch to a model type that supports images."
            )
            return
        photo_file = await update.message.photo[-1].get_file()
        photo_content = await photo_file.download_as_bytearray()
        attachments.append(llm.Attachment(content=photo_content))

    elif update.message.document:
        if update.message.document.mime_type != "application/pdf":
            return await thinking_message.edit_text(
                "Only PDF documents are currently supported. "
                "The file you sent appears to be: "
                f"{update.message.document.mime_type or 'unknown type'}"
            )

        if "application/pdf" not in model.attachment_types:
            return await thinking_message.edit_text(
                "The current model doesn't support document attachments. "
                "Please switch to a model type that supports documents."
            )
        doc_file = await update.message.document.get_file()
        doc_content = await doc_file.download_as_bytearray()
        attachments.append(llm.Attachment(content=doc_content))

    elif update.message.video:
        if "video/mp4" not in model.attachment_types:
            await thinking_message.edit_text(
                "The current model doesn't support video attachments. "
                "Please switch to a model type that supports videos."
            )
            return
        video_file = await update.message.video.get_file()
        video_content = await video_file.download_as_bytearray()
        attachments.append(llm.Attachment(content=video_content))

    elif update.message.audio:
        if "audio/mpeg" not in model.attachment_types:
            await thinking_message.edit_text(
                "The current model doesn't support audio attachments. "
                "Please switch to a model type that supports audio."
            )
            return
        audio_file = await update.message.audio.get_file()
        audio_content = await audio_file.download_as_bytearray()
        attachments.append(llm.Attachment(content=audio_content))

    elif update.message.voice:
        if "audio/ogg" not in model.attachment_types:
            await thinking_message.edit_text(
                "The current model doesn't support voice attachments. "
                "Please switch to a model type that supports voice messages."
            )
            return
        voice_file = await update.message.voice.get_file()
        voice_content = await voice_file.download_as_bytearray()
        attachments.append(llm.Attachment(content=voice_content))

    response = conversation.prompt(
        message_text,
        attachments=attachments,
    )

    try:
        response_text = response.text()
    except Exception as e:
        await thinking_message.edit_text(
            f"Something went wrong when trying to call the LLM: {e}"
        )
        logfire.error(e)
        return

    # Persisting the response to the SQLite DB to keep the conversation
    response.log_to_db(db)

    try:
        # Edit the "Thinking..." message with the actual response
        await thinking_message.edit_text(response_text, parse_mode="Markdown")
    except BadRequest:
        # If Markdown parsing fails, try without it
        try:
            await thinking_message.edit_text(response_text)
        except BadRequest as e:
            # If the message is too long for a single edit, use send_long_message
            logfire.warning(
                f"Failed to edit message: {e}. Falling back to send_long_message"
            )
            await thinking_message.delete()
            await send_long_message(update, context, response_text)

    logfire.info(f"Message: {response_text} Usage: {response.usage()}")


async def error_handler(update: Update, context: CallbackContext) -> None:
    """Handle errors caused by updates."""
    # Log the error
    logfire.error(f"Update {update} caused error {context.error}")

    # Extract the error message
    error_message = str(context.error)

    # Send error message to user
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                f"❌ An error occurred: `{error_message}`",
                parse_mode="Markdown",
            )
    except Exception as e:
        logfire.error(f"Failed to send error message: {e}")
        logfire.error(f"Failed to send error message: {e}")
