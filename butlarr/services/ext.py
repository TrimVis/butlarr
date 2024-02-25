from typing import Dict, Any
import math

from . import ArrService
from dataclasses import dataclass
from ..config.queue import WIDTH, PAGE_SIZE

from ..tg_handler.keyboard import keyboard
from ..tg_handler.message import Response
from ..tg_handler import command, callback, handler
from ..tg_handler.message import Response, repaint, clear, escape_markdownv2_chars
from ..tg_handler.auth import (
    authorized,
)
from ..tg_handler.session_state import (
    sessionState,
    default_session_state_key_fn,
)
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
            percent = 1.0 - (float(item.get("sizeleft", 0)) / item.get("size", 1))
            progress = math.floor(percent * WIDTH)
            remaining = math.ceil((1.0 - percent) * WIDTH)
            status = item.get("status", "-")

            title = escape_markdownv2_chars(item.get("title", "")[0 : 2 * WIDTH])
            title_ln = f"{offset + idx}\. *{title}*"
            progress_ln = (
                f">`[{progress * '='}|{(remaining*' ')}]` {(percent*100):.0f}%"
            )
            status_ln = f">Status: _{item.get('status', 'N/A')}_ \(_{item.get('trackedDownloadState', '-')}_\)   Time left: _{item.get('timeleft', 'N/A')}_"

            lines += [title_ln, progress_ln, status_ln]

        if not len(state.items["records"]):
            n = PAGE_SIZE // 4
            lines += [n * "\n", "\t_No Entries_", n * "\n"]
        elif len(lines) < state.page_size:
            lines += [(state.page_size - len(lines)) * "\n"]

        total_pages = int(state.items["totalRecords"]) // state.page_size
        lines.append(f"\t\tPage _{state.page}_ of _{total_pages }_")

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
