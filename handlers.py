import os
import re
from datetime import datetime
from inspect import cleandoc

import llm
import logfire
import requests
import sqlite_utils
from firecrawl import FirecrawlApp
from llm.cli import load_conversation, logs_db_path
from llm.migrations import migrate
from llm.models import Tool, ToolCall, ToolResult
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext

from config import brave_search_api_key, default_model_id, firecrawl_api_key
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
    "gpt-4o": "Oct 23",
    "gpt-3.5-turbo": "Sep 21",
    "chatgpt-4o": "Oct 23",
    "gpt-4": "Dec 23",
    "o1": "Oct 23",
    "o3": "Oct 23",
    # Google models
    "gemini-2.0-flash": "Aug 24",
    # Anthropic models
    "anthropic/claude-3-7-sonnet": "Nov 24",
    "anthropic/claude-3-5-sonnet": "Apr 24",
    "anthropic/claude-3-5-haiku": "Jul 24",
    "anthropic/claude-3-opus-latest": "Aug 23",
    "anthropic/claude-3-haiku": "Aug 23",
    # Add more models and their cutoff dates here
}

firecrawl_app = FirecrawlApp(api_key=firecrawl_api_key)

MESSAGE_HISTORY_LIMIT = 15
AGENTIC_LOOP_LIMIT = 10


async def user_id(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(f"Your user id is: {update.effective_user.id}")


@restricted
async def chat_id(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(f"Your chat id is: {update.effective_chat.id}")


@restricted
async def conversation_id(update: Update, context: CallbackContext) -> None:
    db = sqlite_utils.Database(logs_db_path())
    migrate(db)  # Migrate the DB before using it, as `log_to_db` doesn't do a migration

    chat_conversations_table = _get_chat_conversations_table(db)

    conversation_id = _get_chat_conversation_id(
        chat_conversations_table, update.effective_chat.id
    )
    await update.message.reply_text(f"Your conversation id is: {conversation_id}")


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
        # Finds the most specific model cutoff date
        cutoff = next(
            (
                cutoff
                for key, cutoff in sorted(
                    model_cutoffs.items(),
                    key=lambda x: len(os.path.commonprefix([model_id, x[0]])),
                    reverse=True,
                )
                if model_id.startswith(key)
            ),
            "Unknown",
        )
        model_details.append(f"• `{model_id}`")

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
    
    Special syntax:
    `@think` - Make the model think step-by-step and show its reasoning process
        - Example: `@think What would happen if gravity suddenly increased by 10%?`
    `@web search query` - Search the web for information related to your query
        - Example: `@web latest quantum computing breakthroughs`
    `@https://example.com` or `@example.com/path` - Scrape a webpage and include its content in the context
        - Example: `Explain this documentation page @https://docs.python.org/3/tutorial/classes.html`
    """)
    await send_long_message(update, context, help_text, parse_mode="Markdown")


@restricted
async def process_private_message(update: Update, context: CallbackContext) -> None:
    if not context.args:
        return await update.message.reply_text(
            "You need to provide a message e.g., `/private My test message`",
            parse_mode="MARKDOWN",
        )

    # Send a "Thinking..." message first
    thinking_message = await update.message.reply_text("...")

    message_text = " ".join(context.args)
    model = llm.get_model(context.user_data.get("model_id", default_model_id))
    system_prompt = context.user_data.get("system_prompt", "")
    response = model.prompt(message_text, system=system_prompt)

    try:
        response_text = response.text()
        # First try to edit with markdown
        try:
            await thinking_message.edit_text(response_text, parse_mode="Markdown")
            return
        except BadRequest:
            pass

        # Then try without markdown
        try:
            await thinking_message.edit_text(response_text)
            return
        except BadRequest:
            pass

        # Finally, delete thinking message and use send_long_message
        await thinking_message.delete()
        await send_long_message(update, context, response_text)

    except Exception as e:
        await update.message.reply_text(
            f"Something went wrong when trying to call the LLM: {e}"
        )
        logfire.error(e)
        return

    logfire.info(f"Message: {response_text} Usage: {response.usage()}")


def _get_chat_conversations_table(db) -> None:
    chat_conversations = db.table("chat_conversations", pk=("chat_id",))
    if not chat_conversations.exists():
        chat_conversations.create(
            {
                "chat_id": int,
                "conversation_id": str,
                "last_used": str,
            },
            if_not_exists=True,
        )

    return chat_conversations


def _get_chat_conversation_id(
    chat_conversations_table, current_chat_id: int
) -> str | None:
    results = list(
        chat_conversations_table.rows_where("chat_id = ?", [current_chat_id], limit=1)
    )
    return results[0]["conversation_id"] if results else None


def _set_chat_conversation_id(
    chat_conversations_table, conversation_id: str, current_chat_id: int
) -> None:
    chat_conversations_table.upsert(
        {
            "chat_id": current_chat_id,
            "conversation_id": conversation_id,
            "last_used": datetime.now().isoformat(),
        },
        pk="chat_id",
    )


def _get_responses_compatible_with_model(
    conversation: llm.Conversation, model: llm.Model
) -> list[llm.Response]:
    """
    We need to remove any responses from the conversation history that have incompatible attachments.
    Initially I thought we could just filter the attachments out, but that doesn't seem to work because
    the underlying model calls generated are not compatible with the input messages that have the attachments.
    """
    filtered_responses = []
    for response in conversation.responses[-MESSAGE_HISTORY_LIMIT:]:
        # For responses with attachments, we need to handle them carefully
        if hasattr(response, "attachments") and response.attachments:
            # Check if any attachments are incompatible
            has_incompatible_attachments = any(
                getattr(attachment, "mime_type", None) not in model.attachment_types
                for attachment in response.attachments
            )

            if has_incompatible_attachments:
                continue

        filtered_responses.append(response)

    return filtered_responses


def _perform_web_search(query: str) -> str:
    """Perform a web search using the Brave Search API and return the formatted results."""
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": brave_search_api_key,
    }

    params = {
        "q": query,
        "count": 10,  # Number of results to return
    }

    try:
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        results = response.json()

        # Format the results as markdown
        if "web" in results and "results" in results["web"]:
            formatted_results = "### Web Search Results\n\n"
            for result in results["web"]["results"]:
                title = result.get("title", "No title")
                url = result.get("url", "")
                description = result.get("description", "No description available")
                formatted_results += f"**[{title}]({url})**\n{description}\n\n"
            return formatted_results
        else:
            return "No search results found."
    except Exception as e:
        logfire.error(f"Error performing web search: {e}")
        return f"Error performing web search: {str(e)}"


@restricted
async def process_message(update: Update, context: CallbackContext) -> None:
    """Processes a message from the user, gets an answer, and sends it back."""

    # Send a "Thinking..." message first
    thinking_message = await update.message.reply_text("...")

    db = sqlite_utils.Database(logs_db_path())
    migrate(db)  # Migrate the DB before using it, as `log_to_db` doesn't do a migration

    chat_conversations_table = _get_chat_conversations_table(db)

    conversation_id = _get_chat_conversation_id(
        chat_conversations_table, update.effective_chat.id
    )
    model_id = context.user_data.get("model_id", default_model_id)
    model = llm.get_model(model_id)

    if not conversation_id:
        conversation = model.conversation()
    else:
        conversation = load_conversation(conversation_id)
        conversation.model = model
        conversation.responses = _get_responses_compatible_with_model(
            conversation, model
        )
        logfire.info(f"Number of responses: {len(conversation.responses)}")

    attachments = []
    message_text: str | None = (
        update.message.text if update.message.text else update.message.caption
    )
    logfire.info(f"Prompt: {message_text}")

    # Find links in the message text
    fragments = []
    url_pattern = r"@(https?://[^\s]+|[^\s]+\.[^\s]+/[^\s]*)"
    urls = re.findall(url_pattern, message_text) if message_text else []

    if urls:
        for url in urls:
            scrape_result = firecrawl_app.scrape_url(
                url, params={"formats": ["markdown"]}
            )
            source_context = cleandoc(f"""
            <source_context url={url}>
            {scrape_result["markdown"]}
            </source_context>
            """)
            fragments.append(source_context)

    # Check if this is a thinking request
    thinking_requested = "@think" in message_text if message_text else False
    thinking_output = ""

    if thinking_requested:
        # Remove the @think command from the message
        clean_message = message_text.replace("@think", "").strip()

        # Create a thinking prompt with instructions
        thinking_prompt = cleandoc(f"""
        This is a message from the user: "{clean_message}"
        
        Think step-by-step about your answer. Consider multiple different paths.
        Critique your thinking and backtrack if necessary.
        Explain your reasoning process thoroughly.

        Do not include any tags in your response like <thinking> or <thinking_output>.
        """)

        # Make the initial "thinking" call to the model
        system_prompt = context.user_data.get("system_prompt", "")
        thinking_response = conversation.prompt(thinking_prompt, system=system_prompt)
        thinking_output = thinking_response.text()

        # Log the thinking output
        logfire.info(f"Thinking output: {thinking_output}...")

        # Send the thinking output to the user in an expandable blockquote
        await thinking_message.edit_text(
            f"<blockquote expandable>\n{thinking_output}\n</blockquote>",
            parse_mode="HTML",
        )

        # Create a new thinking message for the final response
        thinking_message = await update.message.reply_text("...")

        # Add the thinking output to the context for the final response
        fragments.append(f"\n\n<thinking>\n{thinking_output}\n</thinking>\n\n")

        # Use the clean message (without @think) for the final prompt
        message_text = clean_message

    # Check for @web search commands
    web_search_pattern = r"@web"
    web_searches = re.findall(web_search_pattern, message_text) if message_text else []

    if web_searches:
        search_prompt = f"Based on this message: '{message_text}', create a specific web search query that will help answer the user's question. Make it concise but specific."
        search_response = model.prompt(search_prompt)
        search_query = search_response.text().strip()

        logfire.info(f"Web search query: {search_query}")

        # Perform the web search
        search_results = _perform_web_search(search_query)

        logfire.info(f"Web search results: {search_results}")

        # Add the search results to the context
        web_context = cleandoc(f"""
        <web_search_results query="{search_query}">
        {search_results}
        </web_search_results>
        """)
        fragments.append("\n\n" + web_context)

        # Remove the @web part from the message
        message_text = message_text.replace("@web", "").strip()

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
        logfire.info(f"Audio file mime type: {update.message.audio.mime_type}")
        logfire.info(
            f"Audio content type: {type(audio_content)}, length: {len(audio_content) if audio_content is not None else 'None'}"
        )
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
        logfire.info(f"Voice file mime type: {update.message.voice.mime_type}")
        logfire.info(
            f"Voice content type: {type(voice_content)}, length: {len(voice_content) if voice_content is not None else 'None'}"
        )
        attachments.append(llm.Attachment(content=voice_content))

    pretty_print_tool_calls = []

    # A hacky way of collecting info about tool calls for now. Ideally, this function
    # would also print it out to the telegram chat. This doesn't work for now because
    # we don't make LLM calls using asyncio.
    def after_call(tool: Tool, tool_call: ToolCall, tool_result: ToolResult) -> None:
        nonlocal pretty_print_tool_calls
        pretty_print_tool_calls.append(
            cleandoc(f"""
        <blockquote expandable>
        <b>🪛Tool Call</b>
        <i>Name:</i> {tool.name}
        <i>Args</i>: <code>{tool_call.arguments}</code>
        <i>Result:</i> <code>{tool_result.output}</code>
        </blockquote>""")
        )
        logfire.info(f"Tool call: {tool}, {tool_call}, {tool_result}")

    response = conversation.chain(
        message_text,
        fragments=fragments,
        attachments=attachments,
        after_call=after_call,
        chain_limit=AGENTIC_LOOP_LIMIT,
    )

    try:
        response_text = response.text()
        await thinking_message.delete()
        if pretty_print_tool_calls:
            for tool_call in pretty_print_tool_calls:
                await update.message.reply_text(tool_call, parse_mode="HTML")
        # First try to reply with markdown
        try:
            await update.message.reply_text(response_text, parse_mode="Markdown")
        except BadRequest:
            # Then try without markdown
            try:
                await update.message.reply_text(response_text)
            except BadRequest:
                await send_long_message(update, context, response_text)

    except Exception as e:
        await update.message.reply_text(
            f"Something went wrong when trying to call the LLM: {e}"
        )
        logfire.error(e)
        return

    # Persisting the response to the SQLite DB to keep the conversation
    response.log_to_db(db)

    # Only persist the conversation after logging to the DB
    if not conversation_id:
        _set_chat_conversation_id(
            chat_conversations_table, conversation.id, update.effective_chat.id
        )

    if hasattr(response, "usage"):
        logfire.info(f"Message: {response_text} Usage: {response.usage()}")
    else:
        for r in response.responses():
            logfire.info(f"Message: {r.text()} Usage: {r.usage()}")


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
