from loguru import logger
from typing import Optional, List, Any, Literal
from dataclasses import dataclass, replace

from . import ArrService, Action, ArrVariants, find_first
from .ext import ExtArrService, QueueState
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
class State:
    items: List[Any]
    index: int
    quality_profile: str
    tags: List[str]
    root_folder: str
    menu: Optional[
        Literal["path"] | Literal["tags"] | Literal["quality_profile"] | Literal["add"]
    ]


@handler
class Radarr(ExtArrService, ArrService):
    def __init__(
        self,
        commands: List[str],
        api_host: str,
        api_key: str,
    ):
        self.commands = commands
        self.api_key = api_key

        self.api_version = self.detect_api(api_host)
        self.arr_variant = ArrVariants.RADARR
        self.root_folders = self.get_root_folders()
        self.quality_profiles = self.get_quality_profiles()

    @keyboard
    def keyboard(self, state: State):
        item = state.items[state.index]
        in_library = "id" in item and item["id"]

        rows_menu = []
        if state.menu == "add":
            if in_library:
                row_navigation = [Button("=== Editing Movie ===", "noop")]
            else:
                row_navigation = [Button("=== Adding Movie ===", "noop")]
            rows_menu = [
                [
                    Button(
                        f"Change Quality   ({state.quality_profile.get('name', '-')})",
                        self.get_clbk("quality", state.index),
                    ),
                ],
                [
                    Button(
                        f"Change Path   ({state.root_folder.get('path', '-')})",
                        self.get_clbk("path", state.index),
                    )
                ],
                # [
                #     Button(
                #         f"Change Tags   (Total: {len(state.tags)})",
                #         self.get_clbk("tags", state.index),
                #     ),
                # ],
            ]

        elif state.menu == "tags":
            row_navigation = [Button("=== Selecting Tags ===")]
            tags = self.get_tags() or []
            rows_menu = [
                (
                    [
                        Button(
                            (
                                f"Tag {tag.get('label', '-')}"
                                if tag not in state.tags
                                else f"Remove {tag.get('label', '-')}"
                            ),
                            self.get_clbk("addtag", tag.get("id")),
                        )
                    ]
                    for tag in tags
                ),
                [
                    Button(
                        "Done",
                        self.get_clbk("addmenu"),
                    )
                ],
            ]
        elif state.menu == "path":
            row_navigation = [Button("=== Selecting Root Folder ===")]
            rows_menu = [
                [
                    Button(
                        p.get("path", "-"),
                        self.get_clbk("selectpath", p.get("id")),
                    )
                ]
                for p in self.root_folders
            ]
        elif state.menu == "quality":
            row_navigation = [Button("=== Selecting Quality Profile ===")]
            rows_menu = [
                [
                    Button(
                        p.get("name", "-"),
                        self.get_clbk("selectquality", p.get("id")),
                    )
                ]
                for p in self.quality_profiles
            ]
        else:
            if in_library:
                monitored = item.get("monitored", True)
                missing = not item.get("hasFile", False)
                rows_menu = [
                    [
                        Button("📺 Monitored" if monitored else "Unmonitored"),
                        Button("💾 Missing" if missing else "Downloaded"),
                    ]
                ]
            row_navigation = [
                (
                    Button("⬅ Prev", self.get_clbk("goto", state.index - 1))
                    if state.index > 0
                    else Button()
                ),
                (
                    Button(
                        "TMDB",
                        url=f"https://www.themoviedb.org/movie/{item['tmdbId']}",
                    )
                    if item.get("tmdbId", None)
                    else None
                ),
                (
                    Button("IMDB", url=f"https://imdb.com/title/{item['imdbId']}")
                    if item.get("imdbId", None)
                    else None
                ),
                (
                    Button("Next ➡", self.get_clbk("goto", state.index + 1))
                    if state.index < len(state.items) - 1
                    else Button()
                ),
            ]

        rows_action = []
        if in_library:
            if state.menu != "add":
                rows_action.append(
                    [
                        Button(f"🗑 Remove", self.get_clbk("remove")),
                        Button(f"✏️ Edit", self.get_clbk("addmenu")),
                    ]
                )
            else:
                rows_action.append(
                    [
                        Button(f"🗑 Remove", self.get_clbk("remove")),
                        Button(f"✅ Submit", self.get_clbk("add")),
                    ]
                )
        else:
            if not state.menu:
                rows_action.append([Button(f"➕ Add", self.get_clbk("addmenu"))])
            elif state.menu == "add":
                rows_action.append([Button(f"✅ Submit", self.get_clbk("add"))])

        if state.menu:
            rows_action.append([Button("🔙 Back", self.get_clbk("goto"))])
        else:
            rows_action.append([Button("❌ Cancel", self.get_clbk("cancel"))])

        return [row_navigation, *rows_menu, *rows_action]

    def create_message(self, state: State, full_redraw=False):
        item = state.items[state.index]

        keyboard_markup = self.keyboard(state)

        reply_message = f"{item['title']} "
        if item["year"] and str(item["year"]) not in item["title"]:
            reply_message += f"({item['year']}) "

        if item["runtime"]:
            reply_message += f"{item['runtime']}min "

        reply_message += f"- {item['status'].title()}\n\n{item.get('overview', '')}"
        reply_message = reply_message[0:1024]

        return Response(
            photo=item.get("remotePoster") if full_redraw else None,
            caption=reply_message,
            reply_markup=keyboard_markup,
            state=state,
        )

    @repaint
    @command(default=True)
    @sessionState(init=True)
    @authorized(min_auth_level=1)
    async def cmd_default(self, update, context, args):
        title = " ".join(args)
        items = self.lookup(title)

        state = State(
            items=items,
            index=0,
            root_folder=find_first(
                self.root_folders,
                lambda x: items[0].get("folderName").startswith(x.get("path")),
            ),
            quality_profile=find_first(
                self.quality_profiles,
                lambda x: items[0].get("qualityProfileId") == x.get("id"),
            ),
            tags=items[0].get("tags", []),
            menu=None,
        )

        self.session_db.add_session_entry(
            default_session_state_key_fn(self, update), state
        )

        return self.create_message(state, full_redraw=True)

    @repaint
    @command(cmds=["queue"])
    @authorized(min_auth_level=1)
    async def cmd_queue(self, update, context, args):
        return await ExtArrService.cmd_queue(self, update, context, args)

    @repaint
    @callback(
        cmds=[
            "goto",
            "tags",
            "addtag",
            "remtag",
            "path",
            "selectpath",
            "quality",
            "selectquality",
            "addmenu",
        ]
    )
    @sessionState()
    @authorized(min_auth_level=1)
    async def clbk_update(self, update, context, args, state):
        full_redraw = False
        if args[0] == "goto":
            if len(args) > 1:
                idx = int(args[1])
                item = state.items[idx]
                state = replace(
                    state,
                    index=idx,
                    root_folder=find_first(
                        self.root_folders,
                        lambda x: item.get("folderName").startswith(x.get("path")),
                    ),
                    quality_profile=find_first(
                        self.quality_profiles,
                        lambda x: item.get("qualityProfileId") == x.get("id"),
                    ),
                    tags=item.get("tags", []),
                    menu=None,
                )
                full_redraw = True
            else:
                state = replace(state, menu=None)
        elif args[0] == "tags":
            state = replace(state, tags=[], menu="tags")
        elif args[0] == "addtag":
            state = replace(state, tags=[*state.tags, args[1]])
        elif args[0] == "remtag":
            state = replace(state, tags=[t for t in state.tags if t != args[1]])
        elif args[0] == "path":
            state = replace(state, menu="path")
        elif args[0] == "selectpath":
            path = self.get_root_folder(args[1])
            state = replace(state, root_folder=path, menu="add")
        elif args[0] == "quality":
            state = replace(state, menu="quality")
        elif args[0] == "selectquality":
            quality_profile = self.get_quality_profile(args[1])
            state = replace(state, quality_profile=quality_profile, menu="add")
        elif args[0] == "addmenu":
            state = replace(state, menu="add")

        return self.create_message(
            state,
            full_redraw=full_redraw,
        )

    @clear
    @callback(cmds=["add", "remove", "cancel"])
    @sessionState(clear=True)
    @authorized(min_auth_level=1)
    async def btn_add(self, update, context, args, state):
        if args[0] == "add":
            self.add(
                item=state.items[state.index],
                quality_profile_id=state.quality_profile.get("id"),
                root_folder_path=state.root_folder.get("path"),
                tags=state.tags,
            )

            return Response(caption="Movie added!")
        elif args[0] == "remove":
            self.remove(id=state.items[state.index].get("id"))
            return Response(caption="Movie removed!")
        elif args[0] == "cancel":
            return Response(caption="Search canceled!")
