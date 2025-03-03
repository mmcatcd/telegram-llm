from telegram import Update
from telegram.ext import CallbackContext
from model_providers import get_current_user_model, LLMModel, update_user_model
from telegram_utils import restricted
from pydantic import TypeAdapter
from pydantic_ai.messages import ModelMessage
from pydantic_ai import Agent
import json


model_message_adapter = TypeAdapter(ModelMessage)
agent = Agent()


async def user_id(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(f"Your user id is: {update.effective_user.id}")


@restricted
async def chat_id(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(f"Your chat id is: {update.effective_chat.id}")


@restricted
async def private_mode(update: Update, context: CallbackContext) -> None:
    """Set private mode for the user. When enabled, message history is not stored or sent to the LLM.
    Usage: /private_mode [true|false]
    If no argument is provided, it toggles the current state."""
    
    # Initialize privacy_mode in user_data if it doesn't exist
    if "private_mode" not in context.user_data:
        context.user_data["private_mode"] = False
    
    # Check if an argument was provided
    if context.args:
        arg = context.args[0].lower()
        if arg in ["true", "on", "yes", "1"]:
            context.user_data["private_mode"] = True
        elif arg in ["false", "off", "no", "0"]:
            context.user_data["private_mode"] = False
        else:
            await update.message.reply_text(
                "Invalid argument. Use '/private_mode true' or '/private_mode false'.\n"
                "You can also use '/private_mode' without arguments to toggle the current state."
            )
            return
    else:
        # Toggle the privacy mode if no argument was provided
        context.user_data["private_mode"] = not context.user_data["private_mode"]
    
    # Inform the user about the current state
    status = "enabled" if context.user_data["private_mode"] else "disabled"
    await update.message.reply_text(
        f"Private mode is now {status}.\n" + 
        (f"Your messages will not be stored or sent with history to the LLM." 
         if context.user_data["private_mode"] else 
         f"Your message history will be stored and sent to the LLM.")
    )


@restricted
async def set_model(update: Update, context: CallbackContext) -> None:
    """Change the LLM model used by the bot for this user.
    Usage: /model [provider] [model_id]
    Examples: 
      /model anthropic claude-3-7-sonnet-latest
      /model openai gpt-4o
    If no arguments are provided, it shows the current model."""

    current_user_model = get_current_user_model(context)

    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            f"Your current model provider is: {current_user_model.model_provider}\n"
            f"Your current model id is: {current_user_model.model_id}\n\n"
            f"To change the model, use: /model [provider] [model_id]\n"
            f"Examples:\n"
            f"  /model anthropic claude-3-7-sonnet-latest\n"
            f"  /model openai gpt-4o"
        )
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Please specify both provider and model ID.\n"
            "Usage: /model [provider] [model_id]\n"
            "Examples:\n"
            "  /model anthropic claude-3-7-sonnet-latest\n"
            "  /model openai gpt-4o"
        )
        return
    
    provider = context.args[0].upper()
    model_id = context.args[1].lower()

    # Update the user's model preference
    update_user_model(context, LLMModel(model_provider=provider, model_id=model_id))

    await update.message.reply_text(
        f"Your model provider has been changed to: {provider.lower()}\n"
        f"Your model id has been changed to: {model_id}"
    )


@restricted
async def get_model(update: Update, context: CallbackContext) -> str:
    await update.message.reply_text(get_current_user_model(context).model_string)


async def help(update: Update, context: CallbackContext) -> None:
    """Send a message with a list of available commands."""
    help_text = """
    Available commands:
    /user_id - Get your Telegram user ID
    /chat_id - Get the current chat ID
    /set_model [provider] [id] - Change the LLM model being used
        - [provider]: 'anthropic', 'openai'
        - [id]: any model ID supported by the providers API
        - Example: /model anthropic claude-3-7-sonnet-latest
    /get_model - Get the id of the currently used model
    /private_mode - Toggle private mode for messages
    /help - Show this help message
    """
    await update.message.reply_text(help_text)


@restricted
async def process_message(update: Update, context: CallbackContext) -> None:
    """Processes a message from the user, gets an answer, and sends it back."""

    # Checks if private mode is enabled for this user
    private_mode = context.user_data.get("private_mode")

    # Getting message history
    old_messages = []
    if not private_mode:
        message_history = context.chat_data.get("message_history")
        old_messages = [model_message_adapter.validate_python(msg) for msg in json.loads(message_history)] if message_history else []

    # Calling LLM
    result = await agent.run(
        update.message.text,
        message_history=old_messages,
        model=get_current_user_model(context).model_string,
    )

    if not private_mode:
        context.chat_data["message_history"] = result.all_messages_json()

    # Sending response to telegram bot
    await update.message.reply_text(result.data, parse_mode="MARKDOWN")
