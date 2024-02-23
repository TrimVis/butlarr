from urllib.parse import quote
from loguru import logger
from typing import Optional, List, Any, Literal
from dataclasses import dataclass, replace

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from .session_database import SessionDatabase
from .common import ArrService, Action
from .tg_handler import command, callback, handler, construct_command
from .tg_handler.message import (
    Response,
    repaint,
    clear,
)
from .tg_handler.auth import (
    authorized,
)
from .tg_handler.session_state import (
    sessionState,
    default_session_state_key_fn,
)
from .tg_handler.keyboard import Button, keyboard


@dataclass(frozen=True)
class State:
    movies: List[Any]
    index: int
    quality_profile: str
    tags: List[str]
    root_folder: str
    menu: Optional[
        Literal["path"] | Literal["tags"] | Literal["quality_profile"] | Literal["add"]
    ]


@handler
class Radarr(ArrService):
    def __init__(
        self,
        commands: List[str],
        api_host: str,
        api_key: str,
        id="Radarr",
    ):
        self.session_db = SessionDatabase()

        self.id = id
        self.commands = commands
        self.api_key = api_key

        # Detect version and api_url
        self.api_url = f"{api_host.rstrip('/')}/api/v3"
        self.api_version = ""
        status = self.request("system/status")
        if not status:
            self.api_url = f"{api_host.rstrip('/')}/api"
            status = self.request("system/status")
            assert not status, "Only Radarr v3 is supported"

        assert status, "Could not find version. Is the service down?"
        self.api_version = status.get("version", "")

        self.root_folders = self.get_root_folders()
        self.quality_profiles = self.get_quality_profiles()

    def search(self, term: str = None, *, is_tmdb_id=False):
        if not term:
            return []

        return self.request(
            "movie/lookup",
            params={"term": f"tmdb:{term}" if is_tmdb_id else term},
            fallback=[],
        )

    def add(
        self,
        movie=None,
        *,
        tmdb_id: Optional[str] = None,
        min_availability="released",
        quality_profile: str = "",
        tags: List[str] = [],
        root_folder: str = "",
        monitored=True,
        search_for_movie=True,
    ):
        assert (
            movie or tmdb_id
        ), "Missing required args! Either provide the movie object or the tmdb_id"
        if not movie and tmdb_id:
            movie = self.search(tmdb_id, is_tmdb_id=True)[0]

        return self.request(
            "movie",
            action=Action.POST,
            params={
                **movie,
                "qualityProfileId": quality_profile,
                "rootFolderPath": root_folder,
                "tags": tags,
                "monitored": monitored,
                "minimumAvailability": min_availability,
                "addOptions": {"searchForMovie": search_for_movie},
            },
        )

    def get_root_folders(self) -> List[str]:
        return self.request("rootfolder", fallback=[])

    def get_root_folder(self, id: str) -> List[str]:
        return self.request(f"rootfolder/{id}", fallback={})

    def get_tags(self):
        return self.request("tag", fallback=[])

    def get_tag(self, id: str):
        return self.request(f"tag/{id}", fallback={})

    def add_tag(self, tag):
        return self.request(
            "tag", action=Action.POST, params={"label": tag}, fallback={}
        )

    def get_quality_profiles(self):
        return self.request("qualityprofile", fallback=[])

    def get_quality_profile(self, id):
        return self.request(f"qualityprofile/{id}", fallback=[])

    @keyboard
    def keyboard(self, state: State):
        movie = state.movies[state.index]
        in_library = "id" in movie and movie["id"]

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
                        construct_command("quality", state.index),
                    ),
                ],
                [
                    Button(
                        f"Change Path   ({state.root_folder.get('path', '-')})",
                        construct_command("path", state.index),
                    )
                ],
                [
                    Button(
                        f"Change Tags   (Total: {len(state.tags)})",
                        construct_command("tags", state.index),
                    ),
                ],
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
                            construct_command("addtag", tag.get("id")),
                        )
                    ]
                    for tag in tags
                ),
                [
                    Button(
                        "Done",
                        construct_command("addmenu"),
                    )
                ],
            ]
        elif state.menu == "path":
            row_navigation = [Button("=== Selecting Root Folder ===")]
            rows_menu = [
                [
                    Button(
                        p.get("path", "-"),
                        construct_command("selectpath", p.get("id")),
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
                        construct_command("selectquality", p.get("id")),
                    )
                ]
                for p in self.quality_profiles
            ]
        else:
            row_navigation = [
                (
                    Button("⬅ Prev", construct_command("goto", state.index - 1))
                    if state.index > 0
                    else Button()
                ),
                (
                    Button(
                        "TMDB",
                        url=f"https://www.themoviedb.org/movie/{movie['tmdbId']}",
                    )
                    if movie["tmdbId"]
                    else None
                ),
                (
                    Button("IMDB", url=f"https://imdb.com/title/{movie['imdbId']}")
                    if movie["imdbId"]
                    else None
                ),
                (
                    Button("Next ➡", construct_command("goto", state.index + 1))
                    if state.index < len(state.movies) - 1
                    else Button()
                ),
            ]

        rows_action = []
        if in_library:
            if state.menu != "add":
                rows_action.append(
                    [
                        Button(f"🗑 Remove", construct_command("remove")),
                        Button(f"✏️ Edit", construct_command("addmenu")),
                    ]
                )
            else:
                rows_action.append(
                    [
                        Button(f"🗑 Remove", construct_command("remove")),
                        Button(f"✅ Submit", construct_command("add")),
                    ]
                )
        else:
            if state.menu != "add":
                rows_action.append([Button(f"➕ Add", construct_command("addmenu"))])
            else:
                rows_action.append([Button(f"✅ Submit", construct_command("add"))])

        if state.menu:
            rows_action.append([Button("🔙 Back", construct_command("goto"))])
        else:
            rows_action.append([Button("❌ Cancel", construct_command("cancel"))])

        return [row_navigation, *rows_menu, *rows_action]

    def create_message(self, state: State, full_redraw=False):
        movie = state.movies[state.index]

        keyboard_markup = self.keyboard(state)

        reply_message = f"{movie['title']} "
        if movie["year"] and str(movie["year"]) not in movie["title"]:
            reply_message += f"({movie['year']}) "

        if movie["runtime"]:
            reply_message += f"{movie['runtime']}min "

        reply_message += f"- {movie['status'].title()}\n\n{movie['overview']}"
        reply_message = reply_message[0:1024]

        return Response(
            photo=movie["remotePoster"] if full_redraw else None,
            caption=reply_message,
            reply_markup=keyboard_markup,
            state=state,
        )

    @repaint
    @command(default=True)
    @authorized(min_auth_level=1)
    async def cmd_default(self, update, context, args):
        title = " ".join(args)

        movies = self.search(title) or []
        root_folder = self.get_root_folders()[0]
        quality_profile = self.get_quality_profiles()[0]
        state = State(movies, 0, quality_profile, [], root_folder, None)

        self.session_db.add_session_entry(default_session_state_key_fn(update), state)

        return self.create_message(state, full_redraw=True)

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
            "addmenu",
        ]
    )
    @sessionState()
    @authorized(min_auth_level=1)
    async def clbk_update(self, update, context, args, state):
        full_redraw = False
        if args[0] == "goto":
            if len(args) > 1:
                state = replace(state, index=int(args[1]), menu=None)
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
            # Add the movie
            self.add(
                movie=state.movies[state.index],
                quality_profile=state.quality_profile.get("id", 0),
                tags=state.tags,
                root_folder=state.root_folder.get("path", ""),
            )

            return Response(caption="Movie added!")
        elif args[0] == "remove":
            return Response(caption="Movie removed!")
        elif args[0] == "cancel":
            return Response(caption="Search canceled!")
