from functools import wraps
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Button:
    title: str = ""
    clbk: Optional[str] = "noop"
    url: Optional[str] = None


def keyboard(func):
    def create_keyboard(buttons: List[List[Optional[Button]]]):
        keyboard = [
            [
                (
                    InlineKeyboardButton(b.title, callback_data=b.clbk)
                    if not b.url
                    else InlineKeyboardButton(b.title, url=b.url)
                )
                for b in bs
                if b
            ]
            for bs in buttons
            if bs
        ]
        keyboard_markup = InlineKeyboardMarkup(keyboard)
        return keyboard_markup

    @wraps(func)
    def wrapped_func(*args, **kwargs):
        buttons = func(*args, **kwargs)
        return create_keyboard(buttons)

    return wrapped_func
