import shlex

from typing import List, Tuple, Callable, Optional
from loguru import logger
from functools import wraps
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

from dataclasses import dataclass
from typing import Any

from ..session_database import SessionDatabase


def get_chat_id(update):
    if update.callback_query:
        return update.callback_query.message.chat_id
    return update.message.chat_id


def default_session_state_key_fn(self, update):
    return str(self.commands[0]) + str(get_chat_id(update))


def sessionState(key_fn=default_session_state_key_fn, clear=False, init=False):
    def decorator(func):

        @wraps(func)
        async def wrapped_func(self, update, context, *args, **kwargs):
            # init calls do not need a state, as they will create it first
            if init:
                return await func(self, update, context, *args, **kwargs)

            # get state
            key = key_fn(self, update)
            state = self.session_db.get_session_entry(key)
            result = await func(self, update, context, *args, **kwargs, state=state)

            if clear:
                self.session_db.clear_session(key)
            else:
                self.session_db.add_session_entry(key, result.state)
            return result

        return wrapped_func

    return decorator
