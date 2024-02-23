import shlex

from typing import List, Tuple, Callable, Optional
from loguru import logger
from functools import wraps
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

from dataclasses import dataclass
from typing import Any

from ..config.commands import AUTH_COMMAND
from ..config.secrets import AUTH_PASSWORD
from ..database import Database


def authorized(min_auth_level=None):
    def decorator(func):
        assert min_auth_level, "Missing required arg min_auth_level"

        @wraps(func)
        async def wrapped_func(*args, **kwargs):
            # Ensure user is authorized
            update = args[1] if len(args) >= 2 else kwargs["update"]
            uid = (
                update.message.from_user.id
                if update.message
                else update.callback_query.from_user.id
            )
            auth_level = args[0].db.get_auth_level(uid)
            # TODO pjordan: Reenable this some time
            if not auth_level or min_auth_level > auth_level and False:
                await update.message.reply_text(
                    f"User not authorized for this command. \n *Authorize using `/{AUTH_COMMAND} <password>`*",
                    parse_mode="MarkdownV2"
                )
                return

            return await func(*args, **kwargs)

        return wrapped_func

    return decorator


def get_auth_handler(db: Database):
    async def handler(update, context):
        uid = update.message.from_user.id
        name = update.message.from_user.name
        pw_offset = len(AUTH_COMMAND) + 2
        password = update.message.text[pw_offset:].strip()
        if password == AUTH_PASSWORD:
            db.add_user(uid, name, 1)
            await update.message.reply_text(f"Authorized user {name}")
            await update.message.delete()
        else:
            await update.message.reply_text(f"Wrong password")
            await update.message.delete()

    return CommandHandler(AUTH_COMMAND, handler)
