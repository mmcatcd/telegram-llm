from config import list_of_admins
from functools import wraps
import re
import logfire


MAX_MESSAGE_LENGTH = 4096


# Taken from official wiki
# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Code-snippets#restrict-access-to-a-handler-decorator
def restricted(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if str(user_id) not in list_of_admins:
            logfire.error(f"Unauthorized access denied for {user_id}.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


def escape_markdown_v2(text: str) -> str:
    special_chars = r"_*[]()~`>#+-=|{}.! "
    return re.sub(f"([{re.escape(special_chars)}])", r"\\\1", text)


async def send_long_message(update, context, text: str, parse_mode="MarkdownV2"):
    """
    Splits a long message into multiple parts and sends them as replies.
    Each message will be <= 4096 characters.
    
    Args:
        update: Telegram update object
        context: Telegram context object
        text: The text to send
        parse_mode: The parse mode to use (default: MarkdownV2)
    """
    
    # If message is short enough, send it directly
    if len(text) <= MAX_MESSAGE_LENGTH:
        await update.message.reply_text(text, parse_mode=parse_mode)
        return

    # Split into parts, trying to break at newlines when possible
    parts = []
    while text:
        if len(text) <= MAX_MESSAGE_LENGTH:
            parts.append(text)
            break
        
        # Try to find a newline to split at
        split_index = text.rfind('\n', 0, MAX_MESSAGE_LENGTH)
        if split_index == -1:
            # No newline found, split at maximum length
            split_index = MAX_MESSAGE_LENGTH
        
        parts.append(text[:split_index])
        text = text[split_index:].lstrip()

    # Send each part as a reply
    first_message = None
    for i, part in enumerate(parts, 1):
        if parse_mode == "MarkdownV2":
            part = escape_markdown_v2(part)
        
        if first_message is None:
            # First message replies to the original
            first_message = await update.message.reply_text(
                f"(Part {i}/{len(parts)})\n\n{part}",
                parse_mode=parse_mode
            )
        else:
            # Subsequent messages reply to the first part
            await first_message.reply_text(
                f"(Part {i}/{len(parts)})\n\n{part}",
                parse_mode=parse_mode
            )
