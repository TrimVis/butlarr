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

bad_request_poster_error_messages = [
    "Wrong type of the web page content",
    "Wrong file identifier/http url specified",
    "Media_empty",
]


@dataclass(frozen=True)
class Response:
    photo: Optional[str]
    caption: str
    reply_markup: Optional[Any]
    state: Optional[Any]


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

        if not message.photo and update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_caption(
                reply_markup=message.reply_markup,
                caption=message.caption,
            )
        else:
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
