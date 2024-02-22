import shlex

from typing import List, Tuple, Callable
from loguru import logger
from functools import wraps
from telegram.ext import CommandHandler, CallbackQueryHandler

from .config.commands import AUTH_COMMAND
from .config.secrets import AUTH_PASSWORD
from .database import Database


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


bad_request_poster_error_messages = [
    "Wrong type of the web page content",
    "Wrong file identifier/http url specified",
    "Media_empty",
]


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


def callback():
    def decorator(func):
        func.main_clbk = True
        return func

    return decorator


def subCallback(cmd=None):
    assert cmd, "Missing required arg cmd"

    def decorator(func):
        func.sub_clbk = cmd
        return func

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
    cls.sub_callbacks = []
    default_command = None
    default_callback = None
    for method in cls.__dict__.values():
        if hasattr(method, "sub_cmd"):
            cls.sub_commands.append((method.sub_cmd, method))
        if hasattr(method, "main_cmd"):
            assert default_command is None
            default_command = method
        if hasattr(method, "sub_clbk"):
            cls.sub_callbacks.append((method.sub_clbk, method))
        if hasattr(method, "main_clbk"):
            assert default_callback is None
            default_callback = method
    cls.default_command = default_command
    cls.default_callback = default_callback
    return cls


class TelegramHandler:
    db: Database
    commands: List[str]
    sub_commands: List[Tuple[str, Callable]]
    sub_callbacks: List[Tuple[str, Callable]]

    def register(self, application, db):
        self.db = db
        for cmd in self.commands:
            application.add_handler(CommandHandler(cmd, self.handle_command))
        application.add_handler(CallbackQueryHandler(self.handle_callback))

    async def default_command(self, _update, _context):
        del _update, _context
        raise NotImplementedError

    async def handle_command(self, update, context):
        args = shlex.split(update.message.text.strip())
        if len(self.sub_commands) and len(args) > 1:
            for s, c in self.sub_commands:
                if args[1] == s:
                    await c(self, update, context, args[1:])
                    return

        logger.debug("No matching subcommand registered. Trying fallback")
        try:
            await self.default_command(update, context, args)
        except NotImplementedError:
            logger.error("No default command handler registered.")

    async def default_callback(self, _update, _context):
        del _update, _context
        raise NotImplementedError

    async def handle_callback(self, update, context):
        args = shlex.split(update.callback_query.data.strip())
        if len(self.sub_callbacks) and len(args) > 1:
            for s, c in self.sub_callbacks:
                if args[0] == s:
                    await c(self, update, context, args[1:])
                    return

        logger.debug("No matching subcallback registered. Trying fallback")
        try:
            await self.default_callback(update, context, args)
        except NotImplementedError:
            logger.error("No default callback handler registered.")
