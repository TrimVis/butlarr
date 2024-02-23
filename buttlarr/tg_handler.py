import shlex

from typing import List, Tuple, Callable
from loguru import logger
from functools import wraps
from telegram.ext import CommandHandler, CallbackQueryHandler

from .config.commands import AUTH_COMMAND
from .config.secrets import AUTH_PASSWORD
from .database import Database


def callback(cmds=[], default=False):
    def decorator(func):
        if default:
            func.clbk_default = True
        if cmds:
            func.clbk_cmds = cmds
        return func

    return decorator


def command(cmds=[], default=False):
    def decorator(func):
        if default:
            func.cmd_default = True
        if cmds:
            func.cmd_cmds = cmds
        return func

    return decorator


def handler(cls):
    cls.sub_commands = []
    cls.sub_callbacks = []
    default_command = None
    default_callback = None
    for method in cls.__dict__.values():
        if hasattr(method, "cmd_cmds"):
            cls.sub_commands += [(cmd, method) for cmd in method.cmd_cmds]
        if hasattr(method, "cmd_default"):
            assert default_command is None, "Only one default command allowed."
            default_command = method
        if hasattr(method, "clbk_cmds"):
            cls.sub_callbacks += [(cmd, method) for cmd in method.clbk_cmds]
        if hasattr(method, "clbk_default"):
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
            await self.default_command(update, context, args[1:])
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
                    await c(self, update, context, args)
                    return

        logger.debug("No matching subcallback registered. Trying fallback")
        try:
            await self.default_callback(update, context, args)
        except NotImplementedError:
            logger.error("No default callback handler registered.")
