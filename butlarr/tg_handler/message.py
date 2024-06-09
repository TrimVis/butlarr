import shlex

from typing import List, Tuple, Callable, Optional, Literal
from loguru import logger
from functools import wraps
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

from dataclasses import dataclass
from typing import Any

from ..database import Database

bad_request_poster_error_messages = [
    "Wrong type of the web page content",
    "Wrong file identifier/http url specified",
    "Media_empty",
]

no_caption_error_messages = ["There is no caption in the message to edit"]
no_edit_error_messages = [
    "Message is not modified: specified new message content and reply markup are exactly the same as a current content and reply markup of the message"
]


@dataclass(frozen=True)
class Response:
    photo: Optional[str] = None
    caption: str = ""
    reply_markup: Optional[Any] = None
    state: Optional[Any] = None
    parse_mode: Optional[
        Literal["Markdown"] | Literal["MarkdownV2"] | Literal["HTML"]
    ] = None


def clear(func):
    @wraps(func)
    async def wrapped_func(self, update, context, *args, **kwargs):
        message = await func(self, update, context, *args, **kwargs)

        if update.callback_query:
            await update.callback_query.message.reply_text(message.caption)
            await update.callback_query.message.delete()
        else:
            await update.message.delete()

    return wrapped_func


def repaint(func):
    @wraps(func)
    async def wrapped_func(self, update, context, *args, **kwargs):
        message = await func(self, update, context, *args, **kwargs)

        if not message.photo:
            if update.callback_query:
                await update.callback_query.answer()
                try:
                    await update.callback_query.edit_message_caption(
                        reply_markup=message.reply_markup,
                        caption=message.caption,
                        parse_mode=message.parse_mode,
                    )
                except BadRequest as e:
                    if str(e) in no_caption_error_messages:
                        await update.callback_query.edit_message_text(
                            message.caption,
                            reply_markup=message.reply_markup,
                            parse_mode=message.parse_mode,
                        )
                    elif str(e) in no_edit_error_messages:
                        pass
                    else:
                        raise e
            else:
                await update.message.reply_text(
                    message.caption,
                    reply_markup=message.reply_markup,
                    parse_mode=message.parse_mode,
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
                        f"Error sending photo [{message.photo}]: BadRequest: {e}. Attempting to send with default poster..."
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
                    raise e
            finally:
                if update.callback_query:
                    await update.callback_query.answer()
                    await update.callback_query.message.delete()

    return wrapped_func


def escape_markdownv2_chars(text: str):
    for c in [
        "_",
        "*",
        "[",
        "]",
        "(",
        ")",
        "~",
        "`",
        ">",
        "#",
        "+",
        "-",
        "=",
        "|",
        "{",
        "}",
        ".",
        "!",
    ]:
        text = text.replace(c, f"\{c}")
    return text
