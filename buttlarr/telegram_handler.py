from typing import List, Tuple, Callable
from loguru import logger
from functools import wraps
from telegram.ext import CommandHandler

from .database import Database

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
            update = args[2] if len(args) >= 2 else kwargs['update']
            uid = update.message.from_user.id
            auth_level = args[0].db.get_auth_level(uid)
            # TODO pjordan: Reenable this some time
            if not auth_level or min_auth_level > auth_level and False:
                update.message.reply_text(
                    f"User not authorized for this command. \n Authorize using {' OR '.join([f'`/ {c} <password>`' for c in START_COMMANDS])}"
                )
                return

            return func(*args, **kwargs)

        return wrapped_func
    return decorator


def command():
    def decorator(func):
        func.main_cmd = True
        return func
    return decorator


def subCommand(cmd=None):
    assert cmd, "Missing required arg cmd"

    def decorator(func):
        func.sub_cmd = cmd
        return func
    return decorator


def handler(cls):
    cls.sub_commands = []
    default_callback = None
    for method in cls.__dict__.values():
        if hasattr(method, "sub_cmd"):
            cls.sub_commands.append((method.sub_cmd, method))
        if hasattr(method, "main_cmd"):
            assert default_callback is None
            default_callback = method
    cls.default_callback = default_callback
    return cls


class TelegramHandler:
    db: Database
    start_cmds: List[str]
    commands: List[str]
    sub_commands: List[Tuple[str, Callable]]

    def register(self, application, db, start_cmds):
        self.db = db
        self.start_cmds = start_cmds
        for cmd in self.commands:
            application.add_handler(CommandHandler(cmd, self.handle_callback))

    def default_callback(self, _update, _context):
        del _update, _context
        raise NotImplementedError

    def handle_callback(self, update, context):
        args = update.message.text.strip().split(' ')
        if len(self.sub_commands) and len(args) > 1:
            for (s, c) in self.sub_commands:
                if args[1] == s:
                    c(self, update, context, args[1:])
                    return

        logger.debug("No matching subcommand registered. Trying fallback")
        try:
            self.default_callback(update, context)
        except NotImplementedError:
            logger.error("No default command handler registered.")
