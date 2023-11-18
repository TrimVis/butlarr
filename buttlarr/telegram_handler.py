from typing import List, Tuple, Callable
from loguru import logger
from functools import wraps
from .config import START_COMMANDS, DB

bad_request_poster_error_messages = [
    "Wrong type of the web page content",
    "Wrong file identifier/http url specified",
    "Media_empty",
]


def authorized(min_auth_level=None):
    def decorator(func):
        assert min_auth_level, "Missing required arg min_auth_level"

        @wraps(func)
        def wrapped_func(*args, **kwargs):
            # Ensure user is authorized
            update = kwargs['update']
            uid = update.message.from_user.id
            auth_level = DB.get_auth_level(uid)
            if not auth_level or min_auth_level > auth_level:
                update.message.reply_text(
                    f"User not authorized for this command. \n Authorize using {' OR '.join([f'`/ {c} <password>`' for c in START_COMMANDS])}"
                )
                return

            return func(*args, **kwargs)

        return wrapped_func
    return decorator


def command():
    def decorator(func):
        @wraps(func)
        def wrapped_func(*args, **kwargs):
            # remember this as a the default command
            args[0].default_callback = func

            return func(*args, **kwargs)

        return wrapped_func
    return decorator


def subCommand(cmd=None):
    def decorator(func):
        assert cmd, "Missing required arg cmd"

        @wraps(func)
        def wrapped_func(*args, **kwargs):
            # remember this as a subcommand
            self = args[0]
            if not self.sub_commands:
                self.sub_commands = []
            self.sub_commands.append((cmd, func))

            return func(*args, **kwargs)

        return wrapped_func
    return decorator


class TelegramHandler:
    commands: List[str]
    sub_commands: List[Tuple[str, Callable]]

    def default_callback(self, _update, _context):
        del _update, _context
        raise NotImplementedError

    def handle_callback(self, update, context):
        if len(self.sub_commands):
            args = update.message.text.strip().split(' ')
            for (s, c) in self.sub_commands:
                if args[0] == s:
                    c(self, update, context, args[1:])
                    return

        logger.debug("No matching subcommand registered. Trying fallback")
        try:
            self.default_callback(update, context)
        except NotImplementedError:
            logger.error("No default command handler registered.")
