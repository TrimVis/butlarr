import shlex
import inspect

from typing import List, Tuple, Callable
from loguru import logger
from functools import wraps
from telegram.ext import CommandHandler, CallbackQueryHandler
from typing import TypeAlias

from ..config.commands import AUTH_COMMAND, HELP_COMMAND, START_COMMAND
from ..config.secrets import ADMIN_AUTH_PASSWORD
from ..database import Database


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
        text = text.replace(c, rf"\{c}")
    return text


CmdStr: TypeAlias = str  # The command itself
CmdPattern: TypeAlias = str  # Help text: Descriptive pattern for arguments
CmdDescription: TypeAlias = str  # Help text: Description of command
Cmd: TypeAlias = CmdStr | Tuple[CmdStr, CmdPattern, CmdDescription]


def get_help_handler_fn(services):
    response_message = f"""
Welcome to *butlarr*! \n
*butlarr* is a bot that helps you interact with various _arr_ services. \n
To use this service you have to authorize using a password first: `/{AUTH_COMMAND} <password>`. \n
After doing so you can interact with the various services using:
    """
    for s in services:
        for cmd in s.commands:
            response_message += f"\n - `/{cmd} {escape_markdownv2_chars(s.default_pattern)}` \t _{escape_markdownv2_chars(s.default_description)}_"
    response_message += "\n"

    for s in services:
        for cmd, pattern, desc, _ in s.sub_commands:
            response_message += f"\n - `/{s.commands[0]} {cmd} {escape_markdownv2_chars(pattern)}` \t _{escape_markdownv2_chars(desc)}_"

    async def handler(update, context):
        await update.message.reply_text(response_message, parse_mode="Markdown")

    return handler


def get_common_handlers(services):
    help_handler = get_help_handler_fn(services)
    return [
        CommandHandler(HELP_COMMAND, help_handler),
        CommandHandler(START_COMMAND, help_handler),
    ]


def get_clbk_handler(services):
    async def handler(update, context):
        args = shlex.split(update.callback_query.data.strip())
        if args[0] == "noop":
            await update.callback_query.answer()
            return
        logger.debug(f"Received callback: {args}")
        for s in services:
            if args[0] == s.commands[0]:
                return await s.handle_callback(update, context)
        logger.error("Found no matching callback handler!")

    return CallbackQueryHandler(handler)


def callback(
    cmds: List[str] = [],
    default: bool = False,
):
    def decorator(func):
        if default:
            func.clbk_default = True
        if cmds:
            func.clbk_cmds = cmds
        return func

    return decorator


def command(
    cmds: List[Cmd] = [],
    default: bool = False,
    default_description: CmdDescription = "",
    default_pattern: CmdPattern = "",
):
    def decorator(func):
        if default:
            func.cmd_default = (default_description, default_pattern)
        if cmds:
            if isinstance(cmds[0], tuple):
                assert (
                    len(cmds[0]) == 3
                ), "CmdTuple needs to contain pattern as well as description"
                func.cmd_cmds = cmds
            else:
                func.cmd_cmds = [(cmd, "", "") for cmd in cmds]
        return func

    return decorator


def handler(cls):
    cls.sub_commands = []
    cls.sub_callbacks = []
    cls.default_command = None
    cls.default_callback = None
    cls.default_description = ""
    cls.default_pattern = ""
    has_default_command = False
    has_default_callback = False

    for method in list(cls.__dict__.values()):
        if hasattr(method, "cmd_cmds"):
            cls.sub_commands += [
                (cmd, pattern, desc, method) for (cmd, pattern, desc) in method.cmd_cmds
            ]
        if hasattr(method, "cmd_default"):
            assert not has_default_command, f"Only one default command allowed."
            cls.default_command = method
            (desc, pattern) = method.cmd_default
            cls.default_description = desc
            cls.default_pattern = pattern
            has_default_command = True
        if hasattr(method, "clbk_cmds"):
            cls.sub_callbacks += [(cmd, method) for cmd in method.clbk_cmds]
        if hasattr(method, "clbk_default"):
            assert not has_default_callback, "Only one default callback allowed."
            cls.default_callback = method
            has_default_callback = True

    return cls


class TelegramHandler:
    db: Database
    commands: List[CmdStr]
    sub_commands: List[Tuple[CmdStr, CmdPattern, CmdDescription, Callable]]
    sub_callbacks: List[Tuple[str, Callable]]

    def register(self, application, db):
        self.db = db
        for cmd in self.commands:
            application.add_handler(CommandHandler(cmd, self.handle_command))

    async def default_command(self, _update, _context, _args=None):
        del _update, _context, _args
        raise NotImplementedError

    async def handle_command(self, update, context):
        args = shlex.split(update.message.text.strip())
        logger.info(f"Received command: {args}")

        if self.sub_commands and len(args) > 1:
            for s, _, _, c in self.sub_commands:
                if args[1] == s:
                    logger.debug(f"Subcommand - Executing {s} ({c.__name__})")
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
        if args[0] != self.commands[0]:
            return
        if self.sub_callbacks and len(args) > 1:
            for s, c in self.sub_callbacks:
                if args[1] == s:
                    logger.debug(f"Subcallback - Executing {s} ({c.__name__})")
                    await c(self, update, context, args[1:])
                    return

            logger.debug("No matching subcallback registered. Trying fallback")
        try:
            await self.default_callback(update, context, args[1:])
        except NotImplementedError:
            logger.error("No default callback handler registered.")

    def get_clbk(self, *args: List[str]):
        args = [self.commands[0], *args]
        return (" ").join([f'"{arg}"' for arg in args])
