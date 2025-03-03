from config import list_of_admins
from functools import wraps
import re


# Taken from official wiki
# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Code-snippets#restrict-access-to-a-handler-decorator
def restricted(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if str(user_id) not in list_of_admins:
            print(f"Unauthorized access denied for {user_id}.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


def escape_markdown_v2(text: str) -> str:
    special_chars = r"_*[]()~`>#+-=|{}.! "
    return re.sub(f"([{re.escape(special_chars)}])", r"\\\1", text)
