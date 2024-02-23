import shlex

from typing import List, Tuple, Callable
from loguru import logger
from functools import wraps
from telegram.ext import CommandHandler, CallbackQueryHandler

from .config.commands import AUTH_COMMAND
from .config.secrets import AUTH_PASSWORD
from .database import Database


def callback(cmd=None):
    def decorator(func):
        if not cmd:
            func.main_clbk = True
        else:
            func.sub_clbk = cmd
        return func

    return decorator


def command(cmd=None):
    def decorator(func):
        if not cmd:
            func.main_cmd = True
        else:
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
            assert default_command is None, "Only one default command allowed."
            default_command = method
        if hasattr(method, "sub_clbk"):
            cls.sub_callbacks.append((method.sub_clbk, method))
        if hasattr(method, "main_clbk"):
            assert default_callback is None, "Only one default callback allowed."
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

    async def default_command(self, _update, _context, _args=None):
        del _update, _context, _args
        raise NotImplementedError

    async def handle_command(self, update, context):
        args = shlex.split(update.message.text.strip())
        if self.sub_commands:
            for s, c in self.sub_commands:
                if args[1] == s:
                    logger.debug(
                        f"Found matching subcommand. Executing {s} ({c}) with args: {args[1:]}"
                    )
                    await c(self, update, context, args[1:])
                    return

        logger.debug("No matching subcommand registered. Trying fallback")
        try:
            await self.default_command(update, context, args)
        except NotImplementedError:
            logger.error("No default command handler registered.")

    async def default_callback(self, _update, _context, _args=None):
        del _update, _context, _args
        raise NotImplementedError

    async def handle_callback(self, update, context):
        args = shlex.split(update.callback_query.data.strip())
        if self.sub_callbacks:
            for s, c in self.sub_callbacks:
                if args[0] == s:
                    logger.debug(
                        f"Found matching subcallback. Executing {s} ({c}) with args: {args[1:]}"
                    )
                    await c(self, update, context, args[1:])
                    return

        logger.debug("No matching subcallback registered. Trying fallback")
        try:
            await self.default_callback(update, context, args)
        except NotImplementedError:
            logger.error("No default callback handler registered.")
