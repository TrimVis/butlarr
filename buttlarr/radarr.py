from urllib.parse import quote
from loguru import logger
from typing import Optional, List, Any, Literal
from dataclasses import dataclass, replace

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from .session_database import SessionDatabase
from .common import ArrService, Action
from .tg_handler import command, callback, handler
from .tg_handler_ext import (
    construct_command,
    Response,
    authorized,
    repaint,
    clear,
    sessionState,
    default_session_state_key_fn,
)


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

    # TODO pjordan: Add quality selection
    def create_message(self, state: State, full_redraw=False):
        movie = state.movies[state.index]
        movies = state.movies
        index = state.index
        menu = state.menu
        wanted_tags = state.tags
        in_library = "id" in movie and movie["id"]

        empty_key = InlineKeyboardButton(
            "",
            callback_data="noop",
        )

        rows_menu = []
        if menu == "add":
            rows_menu = [
                [
                    InlineKeyboardButton(
                        f"{'Change' if in_library else 'Select'} Quality   ({state.quality_profile.get('name', '-')})",
                        callback_data=construct_command("quality", index),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        f"{'Change' if in_library else 'Select'} Path   ({state.root_folder.get('path', '-')})",
                        callback_data=construct_command("path", index),
                    ),
                ],
                [
                    InlineKeyboardButton(
                        f"{'Change' if in_library else 'Select'} Tags   (Total: {len(state.tags)})",
                        callback_data=construct_command("tags", index),
                    ),
                ],
            ]
            row_navigation = [
                InlineKeyboardButton(
                    (
                        "=== Adding Movie ==="
                        if not in_library
                        else "=== Editing Movie ==="
                    ),
                    callback_data="noop",
                )
            ]
        elif menu == "tags":
            tags = self.get_tags() or []
            rows_menu = [
                (
                    [
                        InlineKeyboardButton(
                            (
                                f"Tag {tag.get('label', '-')}"
                                if tag not in wanted_tags
                                else f"Remove {tag.get('label', '-')}"
                            ),
                            callback_data=construct_command("addtag", tag.get("id")),
                        )
                    ]
                    for tag in tags
                ),
                [
                    InlineKeyboardButton(
                        "Done",
                        callback_data=construct_command("addmenu"),
                    )
                ],
            ]
            row_navigation = [
                InlineKeyboardButton("=== Selecting Tags ===", callback_data="noop")
            ]
        elif menu == "path":
            rows_menu = [
                [
                    InlineKeyboardButton(
                        p.get("path", "-"),
                        callback_data=construct_command("selectpath", p.get("id")),
                    )
                ]
                for p in self.root_folders
            ]
            row_navigation = [
                InlineKeyboardButton(
                    "=== Selecting Root Folder ===", callback_data="noop"
                )
            ]
        elif menu == "quality":
            rows_menu = [
                [
                    InlineKeyboardButton(
                        p.get("name", "-"),
                        callback_data=construct_command("selectquality", p.get("id")),
                    )
                ]
                for p in self.quality_profiles
            ]
            row_navigation = [
                InlineKeyboardButton(
                    "=== Selecting Quality Profile ===", callback_data="noop"
                )
            ]
        else:
            row_navigation = [
                (
                    InlineKeyboardButton(
                        "⬅ Prev",
                        callback_data=construct_command("goto", index - 1),
                    )
                    if index > 0
                    else empty_key
                ),
                (
                    InlineKeyboardButton(
                        "TMDB",
                        url=f"https://www.themoviedb.org/movie/{movie['tmdbId']}",
                    )
                    if movie["tmdbId"]
                    else None
                ),
                (
                    InlineKeyboardButton(
                        "IMDB", url=f"https://imdb.com/title/{movie['imdbId']}"
                    )
                    if movie["imdbId"]
                    else None
                ),
                (
                    InlineKeyboardButton(
                        "Next ➡",
                        callback_data=construct_command("goto", index + 1),
                    )
                    if index < len(movies) - 1
                    else empty_key
                ),
            ]

        rows_action = [
            (
                [
                    InlineKeyboardButton(
                        f"🗑 Remove", callback_data=construct_command("remove")
                    ),
                    (
                        InlineKeyboardButton(
                            f"Edit", callback_data=construct_command("addmenu")
                        )
                        if menu != "add"
                        else InlineKeyboardButton(
                            f"✅ Submit", callback_data=construct_command("add")
                        )
                    ),
                ]
                if in_library
                else (
                    [
                        InlineKeyboardButton(
                            f"➕ Add", callback_data=construct_command("addmenu")
                        )
                    ]
                    if menu != "add"
                    else [
                        InlineKeyboardButton(
                            f"✅ Submit", callback_data=construct_command("add")
                        )
                    ]
                )
            ),
            [
                InlineKeyboardButton(
                    "❌ Cancel",
                    callback_data=construct_command("goto" if menu else "cancel"),
                )
            ],
        ]

        keyboard = [row_navigation, *rows_menu, *rows_action]
        keyboard = [[k for k in ks if k] for ks in keyboard if ks]
        keyboard_markup = InlineKeyboardMarkup(keyboard)

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
    @command()
    @authorized(min_auth_level=1)
    async def cmd_default(self, update, context, args):
        title = " ".join(args[1:])

        movies = self.search(title) or []
        root_folder = self.get_root_folders()[0]
        quality_profile = self.get_quality_profiles()[0]
        state = State(movies, 0, quality_profile, [], root_folder, None)

        self.session_db.add_session_entry(default_session_state_key_fn(update), state)

        return self.create_message(state, full_redraw=True)

    @repaint
    @callback(cmd="goto")
    @sessionState()
    @authorized(min_auth_level=1)
    async def btn_goto(self, update, context, args, state):
        return self.create_message(
            (
                replace(state, index=int(args[0]), menu=None)
                if args
                else replace(state, menu=None)
            ),
            full_redraw=(len(args)),
        )

    @repaint
    @callback(cmd="tags")
    @sessionState()
    @authorized(min_auth_level=1)
    async def btn_tags_list(self, update, context, args, state):
        return self.create_message(replace(state, tags=[], menu="tags"))

    @repaint
    @callback(cmd="addtag")
    @sessionState()
    @authorized(min_auth_level=1)
    async def btn_tags_add(self, update, context, args, state):
        return self.create_message(replace(state, tags=[*state.tags, args[0]]))

    @repaint
    @callback(cmd="remtag")
    @sessionState()
    @authorized(min_auth_level=1)
    async def btn_tags_rem(self, update, context, args, state):
        return self.create_message(
            replace(state, tags=[t for t in state.tags if t != args[0]])
        )

    @repaint
    @callback(cmd="path")
    @sessionState()
    @authorized(min_auth_level=1)
    async def btn_path_list(self, update, context, args, state):
        return self.create_message(replace(state, menu="path"))

    @repaint
    @callback(cmd="selectpath")
    @sessionState()
    @authorized(min_auth_level=1)
    async def btn_path_select(self, update, context, args, state):
        path = self.get_root_folder(args[0])
        return self.create_message(replace(state, root_folder=path, menu="add"))

    @repaint
    @callback(cmd="quality")
    @sessionState()
    @authorized(min_auth_level=1)
    async def btn_quality_list(self, update, context, args, state):
        return self.create_message(replace(state, menu="quality"))

    @repaint
    @callback(cmd="selectquality")
    @sessionState()
    @authorized(min_auth_level=1)
    async def btn_quality_select(self, update, context, args, state):
        quality_profile = self.get_quality_profile(args[0])
        return self.create_message(
            replace(state, quality_profile=quality_profile, menu="add")
        )

    @repaint
    @callback(cmd="addmenu")
    @sessionState()
    @authorized(min_auth_level=1)
    async def btn_add_menu(self, update, context, args, state):
        return self.create_message(replace(state, menu="add"))

    @clear
    @callback(cmd="add")
    @sessionState(clear=True)
    @authorized(min_auth_level=1)
    async def btn_add(self, update, context, args, state):
        # Add the movie
        self.add(
            movie=state.movies[state.index],
            quality_profile=state.quality_profile.get("id", 0),
            tags=state.tags,
            root_folder=state.root_folder.get("path", ""),
        )

        # Clear session db
        del context

        return "Movie added!"

    @clear
    @callback(cmd="remove")
    @sessionState(clear=True)
    @authorized(min_auth_level=1)
    async def btn_remove(self, update, context, args, state):
        return "Movie removed!"

    @clear
    @callback(cmd="cancel")
    @sessionState(clear=True)
    @authorized(min_auth_level=1)
    async def btn_cancel(self, update, context, args, state):
        return "Search canceled!"
