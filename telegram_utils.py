from functools import wraps

import logfire

from config import list_of_admins

MAX_MESSAGE_LENGTH = 4096
SPECIAL_SYMBOLS = "[]()~>#+-=|{}.!''"
FORMAT_SYMBOLS = "*_~"


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


# Taken from stackoverflow
# https://stackoverflow.com/questions/40626896/telegram-does-not-escape-some-markdown-characters
# I'm not bothered to write this tedious code myself
def escape_markdown_v2(input, add_closing_code_block=True):
    if add_closing_code_block and len(input.split("```")) % 2 == 0:
        input += "\n```"

    inside_code_block = False
    inside_inline_code = False

    inside_blocks = {"*": False, "**": False, "_": False, "__": False}
    result = []

    i = 0
    while i < len(input):
        if code_block_start_at(input, i):
            inside_code_block = not inside_code_block
            result.append("```")
            i += 3
            continue

        if inside_code_block:
            i = handle_inside_code_block(input, result, i)
            i += 1
            continue

        if inside_inline_code:
            inside_inline_code = handle_inside_inline_code(input, result, i)
        else:
            i, inside_inline_code, inside_blocks = handle_outside_inline_code(
                input, result, i, inside_blocks
            )

        i += 1

    return "".join(result)


def handle_inside_code_block(input, sb, index):
    if special_symbol_at(input, index):
        sb.append(input[index])
    elif inline_code_at(input, index):
        sb.append("\\`")
    elif format_symbol_at(input, index):
        sb.append(input[index])
    elif code_block_start_at(input, index):
        sb.append("\\`\\`\\`")
        index += 2
    else:
        sb.append(input[index])
    return index


def handle_inside_inline_code(input, sb, index):
    inside_inline_code = True
    is_special = special_symbol_at(input, index)
    is_format = format_symbol_at(input, index)
    if is_special or is_format:
        sb.append("\\")
        sb.append(input[index])
    elif code_block_start_at(input, index):
        sb.append("\\`\\`\\`")
        index += 2
    elif inline_code_at(input, index):
        inside_inline_code = False
        sb.append("`")
    else:
        sb.append(input[index])
    return inside_inline_code


def handle_outside_inline_code(input, sb, index, inside_blocks):
    inside_inline_code = False
    if input[index : index + 2] == "**":
        if inside_blocks["**"]:
            sb.append("**")
            inside_blocks["**"] = False
            index += 1
        elif inline_code_has_closing_in_line(input, index, "**"):
            sb.append("**")
            inside_blocks["**"] = True
            index += 1
        else:
            sb.append("\\**")
            index += 1
    elif input[index : index + 2] == "__":
        if inside_blocks["__"]:
            sb.append("__")
            inside_blocks["__"] = False
            index += 1
        elif inline_code_has_closing_in_line(input, index, "__"):
            sb.append("__")
            inside_blocks["__"] = True
            index += 1
        else:
            sb.append("\\__")
            index += 1
    elif input[index] == "*":
        if inside_blocks["*"]:
            sb.append("*")
            inside_blocks["*"] = False
        elif inline_code_has_closing_in_line(input, index, "*"):
            sb.append("*")
            inside_blocks["*"] = True
        else:
            sb.append("\\*")
    elif input[index] == "_":
        if inside_blocks["_"]:
            sb.append("_")
            inside_blocks["_"] = False
        elif inline_code_has_closing_in_line(input, index, "_"):
            sb.append("_")
            inside_blocks["_"] = True
        else:
            sb.append("\\_")
    elif special_symbol_at(input, index):
        sb.append("\\")
        sb.append(input[index])
    elif format_symbol_at(input, index):
        sb.append("\\")
        sb.append(input[index])
    elif inline_code_at(input, index):
        if inline_code_has_closing_in_line(input, index, "`"):
            inside_inline_code = True
            sb.append("`")
        else:
            sb.append("\\`")
    elif code_block_start_at(input, index):
        sb.append("\\`\\`\\`")
        index += 2
    else:
        sb.append(input[index])
    return index, inside_inline_code, inside_blocks


def code_block_start_at(input, index):
    return (
        index + 2 < len(input)
        and input[index] == "`"
        and input[index + 1] == "`"
        and input[index + 2] == "`"
    )


def inline_code_at(input, index):
    return input[index] == "`" and not code_block_start_at(input, index)


def special_symbol_at(input, index):
    return input[index] in SPECIAL_SYMBOLS


def format_symbol_at(input, index):
    return input[index] in FORMAT_SYMBOLS


def inline_code_has_closing_in_line(input, index, symbol):
    return has_closing_symbol_in_line(input, index, symbol)


def has_closing_symbol_in_line(input, index, symbol):
    search_start = index + len(symbol)
    end_of_line = input.find("\n", search_start)
    if end_of_line == -1:
        end_of_line = len(input)
    possible_closing_index = input.find(symbol, search_start)
    return (
        possible_closing_index != -1
        and possible_closing_index <= end_of_line
        and possible_closing_index != index + 1
    )


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
        split_index = text.rfind("\n", 0, MAX_MESSAGE_LENGTH)
        if split_index == -1:
            # No newline found, split at maximum length
            split_index = MAX_MESSAGE_LENGTH

        parts.append(text[:split_index])
        text = text[split_index:].lstrip()

    # Send each part as a reply
    first_message = None
    for i, part in enumerate(parts, 1):
        if parse_mode in ("MarkdownV2", "Markdown"):
            part = escape_markdown_v2(part)

        if first_message is None:
            # First message replies to the original
            first_message = await update.message.reply_text(
                f"(Part {i}/{len(parts)})\n\n{part}", parse_mode=parse_mode
            )
        else:
            # Subsequent messages reply to the first part
            await first_message.reply_text(
                f"(Part {i}/{len(parts)})\n\n{part}", parse_mode=parse_mode
            )
