import shlex

from typing import List, Tuple, Callable
from loguru import logger
from functools import wraps
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

from dataclasses import dataclass
from typing import Any

from .config.commands import AUTH_COMMAND
from .config.secrets import AUTH_PASSWORD
from .database import Database

bad_request_poster_error_messages = [
    "Wrong type of the web page content",
    "Wrong file identifier/http url specified",
    "Media_empty",
]


@dataclass(frozen=True)
class Response:
    photo: str
    caption: str
    reply_markup: Any
    state: Any


def clear(func):
    @wraps(func)
    async def wrapped_func(self, update, context, *args, **kwargs):
        message = await func(self, update, context, *args, **kwargs)

        if update.callback_query:
            await update.callback_query.message.reply_text(message)
            await update.callback_query.message.delete()
        else:
            await update.message.delete()

    return wrapped_func


def repaint(func):
    @wraps(func)
    async def wrapped_func(self, update, context, *args, **kwargs):
        message = await func(self, update, context, *args, **kwargs)

        try:
            await context.bot.send_photo(
                chat_id=(
                    update.message.chat.id
                    if update.message
                    else update.callback_query.message.chat.id
                ),
                photo=message.photo,
                caption=message.caption,
                reply_markup=message.reply_markup,
            )
        except BadRequest as e:
            if str(e) in bad_request_poster_error_messages:
                logger.error(
                    f"Error sending photo [{movie['remotePoster']}]: BadRequest: {e}. Attempting to send with default poster..."
                )
                await context.bot.send_photo(
                    chat_id=(
                        update.message.chat.id
                        if update.message
                        else update.callback_query.message.chat.id
                    ),
                    photo="https://artworks.thetvdb.com/banners/images/missing/movie.jpg",
                    caption=message.caption,
                    reply_markup=message.reply_markup,
                )
            else:
                raise
        finally:
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.message.delete()

    return wrapped_func


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
                    f"User not authorized for this command. \n Authorize using '/{AUTH_COMMAND} <password>'"
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


def construct_command(*args: List[str]):
    return (" ").join([f'"{arg}"' for arg in args])
