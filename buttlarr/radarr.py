from urllib.parse import quote
from loguru import logger
from typing import Optional, List, Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

from .session_database import SessionDatabase
from .common import ArrService, Action
from .telegram_handler import (
    command,
    authorized,
    subCommand,
    bad_request_poster_error_messages,
    handler,
    construct_command,
)


@handler
class Radarr(ArrService):
    def __init__(
        self,
        commands: List[str],
        api_host: str,
        api_key: str,
        allow_path_selection=True,
        allow_tag_selection=True,
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
        self.allow_path_selection = allow_path_selection
        self.allow_tag_selection = allow_tag_selection

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

    # TODO pjordan: Add quality selection

    async def reply(self, update, context, movies, index, menu=None, wanted_tags=[]):
        movie = movies[index]

        keyboard_nav_row = [
            (
                InlineKeyboardButton(
                    "⬅",
                    callback_data=construct_command("goto", index - 1),
                )
                if index > 0
                else None
            ),
            (
                InlineKeyboardButton(
                    "TMDB", url=f"https://www.themoviedb.org/movie/{movie['tmdbId']}"
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
                    "➡",
                    callback_data=construct_command("goto", index + 1),
                )
                if index < len(movies) - 1
                else None
            ),
        ]

        keyboard_menu_row = None
        keyboard_act_row_0 = []
        keyboard_act_row_1 = []
        if menu == "tags":
            tags = self.get_all_tags() or []
            keyboard_menu_row = [
                (
                    [
                        InlineKeyboardButton(
                            f"Tag {tag}" if tag not in wanted_tags else f"Remove {tag}",
                            callback_data=construct_command("tag", *wanted_tags, i),
                        )
                    ]
                    for (i, tag) in enumerate(tags)
                ),
                [
                    InlineKeyboardButton(
                        "Done",
                        callback_data=construct_command("add", index, p, wanted_tags),
                    )
                ],
            ]
        elif menu == "paths":
            paths = self.get_root_folders() or []
            keyboard_menu_row = [
                (
                    [
                        InlineKeyboardButton(
                            f"Add {p}",
                            callback_data=construct_command(
                                "add", index, p, wanted_tags
                            ),
                        )
                    ]
                    for p in paths
                )
            ]
        elif not menu:
            if not movie["id"]:
                keyboard_act_row_0 += [
                    InlineKeyboardButton(
                        f"Add {p}",
                        callback_data=construct_command("add", index, p, wanted_tags),
                    )
                ]
                keyboard_act_row_1 += [
                    (
                        InlineKeyboardButton(
                            "Add to Path",
                            callback_data=construct_command("path", index),
                        )
                        if self.allow_path_selection
                        else None
                    ),
                    (
                        InlineKeyboardButton(
                            "Add with Tags",
                            callback_data=construct_command("tags", index),
                        )
                        if self.allow_tag_selection
                        else None
                    ),
                ]
            else:
                keyboard_act_row_0 += [
                    InlineKeyboardButton(
                        "Remove", callback_data=construct_command("remove", index)
                    ),
                ]
                keyboard_act_row_1 += [
                    (
                        InlineKeyboardButton(
                            "Change Path",
                            callback_data=construct_command("path", index),
                        )
                        if self.allow_path_selection
                        else None
                    ),
                    (
                        InlineKeyboardButton(
                            "Change Tags",
                            callback_data=construct_command("tags", index),
                        )
                        if self.allow_tag_selection
                        else None
                    ),
                ]

        keyboard_act_row_2 = [
            InlineKeyboardButton(
                "Cancel",
                callback_data="cancel",
            ),
        ]

        keyboard = [
            keyboard_nav_row,
            keyboard_menu_row,
            keyboard_act_row_0,
            keyboard_act_row_1,
            keyboard_act_row_2,
        ]

        # Ignore this ugly piece of code, we are just filtering out all Nones
        keyboard = [[k for k in ks if k] for ks in keyboard if ks]
        keyboard = [[k for k in ks if k] for ks in keyboard if ks]

        keyboard_markup = InlineKeyboardMarkup(keyboard)

        reply_message = f"{movie['title']} "
        if movie["year"] and str(movie["year"]) not in movie["title"]:
            reply_message += f"({movie['year']}) "

        if movie["runtime"]:
            reply_message += f"{movie['runtime']}min "

        reply_message += f"- {movie['status'].title()}\n\n{movie['overview']}"
        reply_message = reply_message[0:1024]

        try:
            await context.bot.sendPhoto(
                chat_id=update.message.chat.id,
                photo=movie["remotePoster"],
                caption=reply_message,
                reply_markup=keyboard_markup,
            )
        except BadRequest as e:
            if str(e) in bad_request_poster_error_messages:
                logger.error(
                    f"Error sending photo [{movie['remotePoster']}]: BadRequest: {e}. Attempting to send with default poster..."
                )
                await context.bot.sendPhoto(
                    chat_id=update.message.chat.id,
                    photo="https://artworks.thetvdb.com/banners/images/missing/movie.jpg",
                    caption=reply_message,
                    reply_markup=keyboard_markup,
                )
            else:
                raise

    @command()
    @authorized(min_auth_level=1)
    async def cmd_default(self, update, context, args):
        title = " ".join(args[1:])
        chat_id = update.message.chat.id

        # Search movies and store the results in the session db
        movies = self.search(title) or []
        self.session_db.add_session_entry(chat_id, movies, key="movies")

        await self.reply(update, context, movies, 0)

    @subCommand(cmd="goto")
    @authorized(min_auth_level=1)
    async def cmd_goto(self, update, context, args):
        movie_id = args[0]
        chat_id = update.message.chat.id

        # Retrieve movies from the session db
        movies = self.session_db.get_session_entry(chat_id, key="movies")

        await self.reply(update, context, movies, movie_id)

    @subCommand(cmd="tags")
    @authorized(min_auth_level=1)
    async def cmd_goto(self, update, context, args):
        movie_id = args[0]
        chat_id = update.message.chat.id

        # Retrieve movies from the session db
        movies = self.session_db.get_session_entry(chat_id, key="movies")

        await self.reply(
            update, context, movies, movie_id, menu="paths", wanted_tags=args[1:]
        )

    @subCommand(cmd="path")
    @authorized(min_auth_level=1)
    async def cmd_goto(self, update, context, args):
        movie_id = args[0]
        chat_id = update.message.chat.id

        # Retrieve movies from the session db
        movies = self.session_db.get_session_entry(chat_id, key="movies")

        await self.reply(
            update, context, movies, movie_id, menu="paths", wanted_tags=args[1:]
        )

    @subCommand(cmd="add")
    @authorized(min_auth_level=1)
    async def cmd_add(self, update, context):
        movie_id = args[0]

        chat_id = update.message.chat.id

        # Retrieve movies from the session db
        movies = self.session_db.get_session_entry(chat_id, key="movies")

        # Add the movie
        self.add(movie=movies[movie_id], quality_profile=args[1], tags=args[2:])

        # Clear session db & remove context
        del context
        del movies
        self.session_db.clear_session(chat_id)

        await update.query.message.reply_text("Movie added!")

    @subCommand(cmd="remove")
    @authorized(min_auth_level=1)
    async def cmd_remove(self, update, context):
        del context
        chat_id = update.message.chat.id

        # Clear session db
        self.session_db.clear_session(chat_id)

        await update.query.message.reply_text("Movie removed!")

    @subCommand(cmd="cancel")
    @authorized(min_auth_level=1)
    async def cmd_cancel(self, update, context):
        del context
        chat_id = update.message.chat.id

        # Clear session db
        self.session_db.clear_session(chat_id)

        await update.query.message.reply_text("Search canceled")
        await update.query.message.delete()
