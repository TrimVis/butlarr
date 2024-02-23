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


def default_session_state_key_fn(update):
    if update.callback_query:
        return update.callback_query.message.chat_id
    return update.message.chat_id


def sessionState(key_fn=default_session_state_key_fn, clear=False):
    def decorator(func):
        @wraps(func)
        async def wrapped_func(self, update, context, *args, **kwargs):
            # get state
            chat_id = default_session_state_key_fn(update)
            state = self.session_db.get_session_entry(chat_id)
            result = await func(self, update, context, *args, **kwargs, state=state)

            if clear:
                self.session_db.clear_session(chat_id)
            else:
                self.session_db.add_session_entry(chat_id, result.state)
            return result

        return wrapped_func

    return decorator
