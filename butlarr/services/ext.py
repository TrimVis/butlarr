import math
from loguru import logger
from typing import Dict, Any
from functools import wraps
from dataclasses import dataclass

from . import ArrService
from ..config.queue import WIDTH, PAGE_SIZE

from ..tg_handler import handler, escape_markdownv2_chars
from ..tg_handler.message import Response
from ..tg_handler.keyboard import Button, keyboard


@dataclass(frozen=True)
class QueueState:
    items: Dict[str, Any]
    page: int
    page_size: int


@handler
class ExtArrService(ArrService):
    @keyboard
    def create_queue_keyboard(self, state: QueueState):
        total_pages = int(state.items["totalRecords"]) // state.page_size
        return [
            [
                (
                    Button("Prev page", self.get_clbk("queue", state.page - 1))
                    if state.page > 0
                    else Button()
                ),
                (
                    Button("Next page", self.get_clbk("queue", state.page + 1))
                    if state.page < total_pages
                    else Button()
                ),
            ],
        ]

    def create_queue_message(self, state: QueueState, full_redraw=False):
        lines = ["*Queue*", ""]
        offset = state.page * state.page_size + 1
        for idx, item in enumerate(state.items["records"]):
            percent = 1.0 - (float(item.get("sizeleft", 0)) /
                             (item.get("size") or 1))
            progress = math.floor(percent * WIDTH)
            remaining = math.ceil((1.0 - percent) * WIDTH)

            title = escape_markdownv2_chars(
                item.get("title", "")[0: 2 * WIDTH])
            title_ln = rf"{offset + idx}\. *{title}*"
            progress_ln = (
                rf">`[{progress * '='}|{(remaining*' ')
                                        }]` {round(percent*100)}%"
            )

            status = escape_markdownv2_chars(item.get('status', 'N/A'))
            download_state = escape_markdownv2_chars(
                item.get('trackedDownloadState', '-'))
            time_left = escape_markdownv2_chars(item.get('timeleft', 'N/A'))

            status_ln = rf">Status: _{status}_ \(_{
                download_state}_\)   Time left: _{time_left}_"

            lines += [title_ln, progress_ln, status_ln]

        if not len(state.items["records"]):
            n = PAGE_SIZE // 4
            lines += [n * "\n", "\t_No Entries_", n * "\n"]
        elif len(lines) < state.page_size:
            lines += [(state.page_size - len(lines)) * "\n"]

        total_pages = int(state.items["totalRecords"]) // state.page_size
        lines.append(f"\t\tPage _{state.page}_ of _{total_pages}_")

        reply_message = "\n".join(lines)
        keyboard_markup = self.create_queue_keyboard(state)

        return Response(
            caption=reply_message,
            reply_markup=keyboard_markup,
            state=state,
            parse_mode="MarkdownV2",
        )

    async def cmd_queue(self, update, context, args):
        items = self.get_queue(page=0, page_size=PAGE_SIZE)

        state = QueueState(
            items=items,
            page=0,
            page_size=PAGE_SIZE,
        )

        return self.create_queue_message(state)

    async def clbk_queue(self, update, context, args):
        items = self.get_queue(page=int(args[1]), page_size=PAGE_SIZE)

        state = QueueState(
            items=items,
            page=int(args[1]),
            page_size=PAGE_SIZE,
        )

        return self.create_queue_message(state)

    async def cmd_help(self, update, context, args):
        response_message = f"""
*butlarr* - Help page for {type(self).__name__} service.

Following commands are available:
        """
        for cmd in self.commands:
            pattern = escape_markdownv2_chars(
                self.default_pattern)
            desc = escape_markdownv2_chars(self.default_description)
            response_message += f"\n - `/{cmd} {pattern}` \t _{desc}_\n"

        for cmd, pattern, desc, _ in self.sub_commands:
            pattern = escape_markdownv2_chars(pattern)
            desc = escape_markdownv2_chars(desc)
            response_message += f"\n - `/{self.commands[0]} {
                cmd} {pattern}` \t _{desc}_"

        return await update.message.reply_text(
            response_message, parse_mode="Markdown"
        )


@dataclass(frozen=True)
class ParentState:
    service: ArrService = None
    state: any = None
    menu: str = None


class Addon:
    parent: ParentState = None
    supported_services = []

    # Set the service and state that is loading this addon
    def init(func):
        @wraps(func)
        def wrapped_func(self, *args, **kwargs):
            service = kwargs.get('parent')
            logger.debug(f'[Addon] Current service set: {service}')
            state = kwargs.get('state')
            logger.debug(f'[Addon] Current service state set: {state.index}')
            menu = kwargs.get('menu')
            logger.debug(f'[Addon] Return menu set: {menu}')

            parent = ParentState(
                service=service,
                state=state,
                menu=menu
            )

            self.parent = parent

            return func(self, *args, **kwargs)

        return wrapped_func

    def load(func):
        @wraps(func)
        def wrapped_func(self, *args, **kwargs):
            parent = {
                'parent': self.parent
            }
            return func(self, *args, **parent, **kwargs)
        return wrapped_func

    @init
    def addon_buttons(self, state, **kwargs):
        raise NotImplementedError
