from urllib.parse import quote
from loguru import logger
from typing import Optional, List, Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.error import BadRequest
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

from .common import Endpoints, EndpointKeys, ensure_keys, ArrService
from .telegram_handler import command, authorized, subCommand, bad_request_poster_error_messages


class Radarr(ArrService):
    def __init__(self, commands: List[str], api_host: str, api_key: str, kind="Radarr"):
        self.kind = kind
        self.commands = commands
        self.api_key = api_key

        # Detect version and api_url
        self.api_url = f"{api_host}/api/v3"
        self.api_version = ""
        status = self._get("system/status")
        if not status:
            self.api_url = f"{api_host}/api"
            status = self._get("system/status")

        assert status, 'Could not find version. Is the service down?'
        self.api_version = status.json().get('version', '')

        self.endpoints = Endpoints(
            status="system/status",
            search="movie/lookup",
            add="movie",
            root_folders="RootFolder",
            profiles=(
                "qualityProfile"
                if not self.api_version.startswith('0.')
                else "profile"
            ),
            tag="tag",
            add_tag="tag",
        )
        self.preserved_keys = EndpointKeys(
            search=[
                ("title", None),
                ("overview", "No overview available"),
                ("status", "Unknown status"),
                ("inCinemas", None),
                ("remotePoster", "https://artworks.thetvdb.com/banners/images/missing/movie.jpg",),
                ("year", None),
                ("tmdbId", None),
                ("imdbId", None),
                ("runtime", None),
                ("id", None),
                ("titleSlug", None),
                ("images", None),
            ],
        )
        self.root_folders = self.get_root_folders()

    def search(self, title: Optional[str] = None, tmdb_id: Optional[str] = None):
        if tmdb_id:
            return self._get_endpoint('search', {"term": f"tmdb:{tmdb_id}"}, [])
        if title:
            return self._get_endpoint('search', {"term": quote(title)}, [])
        return []

    def add(self,
            movie_info: Optional[Any] = None,
            tmdb_id: Optional[str] = None,
            search=True,
            monitored=True,
            min_avail="released",
            quality_profile: str = '',
            tags: List[str] = [],
            root_folder: str = '',
            ):

        if not movie_info and tmdb_id:
            movie_infos = self.search(tmdb_id=tmdb_id)
            if isinstance(movie_infos, list) and len(movie_infos):
                movie_info = ensure_keys(movie_infos[0], [
                    ("tmdbId", None),
                    ("title", None),
                    ("year", None),
                    ("titleSlug", None),
                    ("images", None)
                ])

        if not movie_info:
            return False

        return self._post_endpoint('add', {
            **movie_info,
            "qualityProfileId": quality_profile,
            "rootFolderPath": root_folder,
            "tags": tags,
            "monitored": monitored,
            "minimumAvailability": min_avail,
            "tags": tags,
            "addOptions": {"searchForMovie": search},
        })

    def get_root_folders(self) -> List[str]:
        return self._get_endpoint('root_folders', fallback=[])

    def get_all_tags(self):
        return self._get_endpoint('tag', fallback=[])

    def get_filtered_tags(self, allowed_tags, excluded_tags):
        if not allowed_tags == []:
            return [
                x
                for x in self.get_all_tags() or []
                if not x["label"].startswith("searcharr-")
                and not x["label"] in excluded_tags
            ]

        return [
            x
            for x in self.get_all_tags() or []
            if not x["label"].startswith("searcharr-")
            and (x["label"] in allowed_tags or x["id"] in allowed_tags)
            and x["label"] not in excluded_tags
        ]

    def add_tag(self, tag):
        self._post_endpoint('add_tag', {'label': tag}, {})

    def get_tag_id(self, tag: str):
        all_tags = self.get_all_tags()
        assert all_tags, "Failed to fetch all tags"
        if tag_id := next(
                iter([
                    x.get("id") for x in all_tags
                    if x.get("label", '').lower() == tag.lower()
                ]), None,
        ):
            return tag_id
        else:
            res = self.add_tag(tag)
            assert res, "Failed to add tag"
            return res.get('id', None)

    def lookup_quality_profile(self):
        return self._get_endpoint('profiles')

    def lookup_root_folder(self, v):
        assert self.root_folders, "Root folders missing"
        return next(
            (x for x in self.root_folders if str(
                v) in [x["path"], str(x["id"])]),
            None,
        )

    # TODO pjordan: Add quality selection

    def reply(self, update, context, movie, index, total_results, menu=None):
        keyboardNavRow = [(InlineKeyboardButton(
            "⬅",
            callback_data='prev'
        ) if index > 0 else None),
            InlineKeyboardButton(
                "TMDB", url=f"https://www.themoviedb.org/movie/{movie['tmdbId']}"
        ) if movie["tmdbId"] else None,
            InlineKeyboardButton(
                "IMDb", url=f"https://imdb.com/title/{movie['imdbId']}"
        ) if movie["imdbId"] else None,
            InlineKeyboardButton(
                "➡",
                callback_data="next",
        ) if total_results > 1 and index < total_results - 1 else None,
        ]

        keyboardMenuRow = None
        if menu:
            if menu == 'tags':
                tags = self.get_all_tags() or []
                keyboardMenuRow = [
                    ([InlineKeyboardButton(
                        f"Tag {tag}", callback_data="tag")] for tag in tags[:12]),
                    [InlineKeyboardButton("Done", callback_data="add",)],
                ]
            elif menu == 'paths':
                paths = self.get_root_folders() or []
                keyboardMenuRow = [
                    ([InlineKeyboardButton(
                        f"Add {p}", callback_data="add")] for p in paths)
                ]

        keyboardActRow = []
        if not menu:
            if not movie['id']:
                keyboardActRow += [InlineKeyboardButton("Add", "add")]
            else:
                keyboardActRow += [InlineKeyboardButton(
                    "Added", callback_data="noop"), ]

        keyboardActRow += [InlineKeyboardButton(
            "Cancel", callback_data="cancel",), ]

        reply_markup = InlineKeyboardMarkup([
            keyboardNavRow,
            keyboardMenuRow,
            keyboardActRow,
        ])
        reply_message = f"{movie['title']} "
        if movie['year'] and movie['year'] not in movie['title']:
            reply_message += f"({movie['year']}) "

        if movie['runtime']:
            reply_message += f"{movie['runtime']}min "

        reply_message += f"- {movie['status'].title()}\n\n{movie['overview']}"
        reply_message = reply_message[0:1024]

        try:
            context.bot.sendPhoto(
                chat_id=update.message.chat.id,
                photo=movie["remotePoster"],
                caption=reply_message,
                reply_markup=reply_markup,
            )
        except BadRequest as e:
            if str(e) in bad_request_poster_error_messages:
                logger.error(
                    f"Error sending photo [{movie['remotePoster']}]: BadRequest: {e}. Attempting to send with default poster..."
                )
                context.bot.sendPhoto(
                    chat_id=update.message.chat.id,
                    photo="https://artworks.thetvdb.com/banners/images/missing/movie.jpg",
                    caption=reply_message,
                    reply_markup=reply_markup,
                )
            else:
                raise

    @ command()
    @ authorized(min_auth_level=1)
    def cmd_default(self, update, context):
        title = update.message.text
        movies = self.search(title) or []
        self.reply(update, context, movies[0], 0, len(movies))

    @ subCommand(cmd='add')
    @ authorized(min_auth_level=1)
    def cmd_add(self, update, context):
        pass

    @ subCommand(cmd='cancel')
    @ authorized(min_auth_level=1)
    def cmd_cancel(self, update, context):
        del context
        update.query.message.reply_text("Search canceled")
        update.query.message.delete()

    @ subCommand(cmd='next')
    @ authorized(min_auth_level=1)
    def cmd_next(self, update, context):
        pass

    @ subCommand(cmd='prev')
    @ authorized(min_auth_level=1)
    def cmd_prev(self, update, context):
        pass
