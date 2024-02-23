from typing import Dict, Any
import math

from . import ArrService
from ..tg_handler.keyboard import keyboard
from ..tg_handler.message import Response
from dataclasses import dataclass

from ..tg_handler import command, callback, handler
from ..tg_handler.message import (
    Response,
    repaint,
    clear,
)
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
    def create_queue_keyboard(self, state):
        return []

    def create_queue_message(self, state: QueueState, full_redraw=False):
        lines = ["*Queue*"]
        for item in state.items["records"]:
            percent = 1.0 - (float(item.get("sizeleft", 0)) / item.get("size", 1))
            progress = math.floor(percent * 15)
            remaining = math.ceil((1.0 - percent) * 15)

            title_ln = " - " + item.get("title", "")[0:25]
            progress_ln = f"`[{progress * '='}|{(remaining*' ')}]` {(percent*100):.2f}%"

            lines += [title_ln, progress_ln]

        if not len(state.items["records"]):
            lines += [5 * "\n", "\t_No Entries_", 5 * "\n"]
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
        )

    async def cmd_queue(self, update, context, args):
        items = self.get_queue(page=0, page_size=15)

        state = QueueState(
            items=items,
            page=0,
            page_size=15,
        )

        self.session_db.add_session_entry(
            default_session_state_key_fn(self, update), state
        )

        return self.create_queue_message(state, full_redraw=True)
