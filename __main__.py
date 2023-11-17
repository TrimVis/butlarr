import click
import datetime
from loguru import logger
import yaml
from .common import ArrService
from .database import Database
from typing import List

from urllib.parse import parse_qsl

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.error import BadRequest
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler



_bad_request_poster_error_messages = [
    "Wrong type of the web page content",
    "Wrong file identifier/http url specified",
    "Media_empty",
]


def insert_media(kind: str, update, context, reply_message, reply_markup, photo):
    query = update.callback_query
    insert_callback = (
        context.bot.sendPhoto if kind == "send" else update.callback_query.edit_media
    )
    try:
        insert_callback(
            chat_id=update.message.chat.id,
            photo=photo,
            caption=reply_message,
            reply_markup=reply_markup,
        )
    except BadRequest as e:
        if str(e) in _bad_request_poster_error_messages:
            logger.error(
                f"Error sending photo [{photo}]: BadRequest: {e}. Attempting to send with default poster..."
            )
            insert_callback(
                chat_id=update.message.chat.id,
                photo="https://artworks.thetvdb.com/banners/images/missing/movie.jpg",
                caption=reply_message,
                reply_markup=reply_markup,
            )
        else:
            raise
        if kind == "edit":
            query.bot.edit_message_caption(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                caption=reply_message,
                reply_markup=reply_markup,
            )
    pass


class Buttlarr:
    db: Database
    converstations = []
    token: str
    services: List[ArrService]

    def __init__(self, db, token, services, lang="en-US"):
        self.db = db
        self.token = token
        self.services = services
        self._lang = self._load_language(lang)
        self._lang_default = self._load_language("en-US")

    def _load_language(self, lang_ietf="en-US"):
        logger.debug(
            f"Attempting to load language file: lang/{lang_ietf}.yml...")
        try:
            with open(f"lang/{lang_ietf}.yml", mode="r", encoding="utf-8") as y:
                lang = yaml.load(y, Loader=yaml.SafeLoader)
        except FileNotFoundError:
            logger.error(
                f"Error loading lang/{lang_ietf}.yml. Confirm searcharr_language in settings.py has a corresponding yml file in the lang subdirectory. Using default (English) language file."
            )
            with open("lang/en-us.yml", "r") as y:
                lang = yaml.load(y, Loader=yaml.SafeLoader)
        return lang

    def _xlate(self, key, **kwargs):
        if t := self._lang.get(key):
            return t.format(**kwargs)
        else:
            logger.error(f"No translation found for key [{key}]!")
            if self._lang.get("language_ietf") != "en-us":
                if t := self._lang_default.get(key):
                    logger.info(f"Using default language for key [{key}]...")
                    return t.format(**kwargs)
        return "(translation not found)"

    def check_authenticated(self, update, _):
        uid = update.message.from_user.id
        if not (authenticated := self.db._authenticated(uid)):
            update.message.reply_text(
                self._xlate(
                    "auth_required",
                    commands=" OR ".join(
                        [f"`/{c} <{self._xlate('password')}>`" for c in START_COMMANDS]
                    ),
                )
            )

        return authenticated

    def _strip_entities(self, message):
        text = message.text
        entities = message.parse_entities()
        logger.debug(f"{entities=}")
        for v in entities.values():
            text = text.replace(v, "")
        text = text.replace("  ", "").strip()
        logger.debug(
            f"Stripped entities from message [{message.text}]: [{text}]")
        return text

    def _prepare_response(
        self,
        kind,
        r,
        cid,
        i,
        total_results,
        paths=None,
        options=None,
        option_kind=None,
        tags=None,
    ):
        keyboard = []
        keyboardNavRow = [
            (InlineKeyboardButton(
                self._xlate("prev_button"),
                callback_data=self.build_resp(cid, i, 'media', 'prev')
            ) if i > 0 else None),
            InlineKeyboardButton(
                "tvdb", url=f"https://thetvdb.com/series/{r['titleSlug']}"
            ) if kind == "series" and r["tvdbId"] else None,
            InlineKeyboardButton(
                "TMDB", url=f"https://www.themoviedb.org/movie/{r['tmdbId']}"
            ) if kind == "movie" and r["tmdbId"] else None,
            ((
                InlineKeyboardButton(link["name"], url=link["url"])
                for link in r["links"]
            ) if kind == "book" and r["links"] else None),
            InlineKeyboardButton(
                "IMDb", url=f"https://imdb.com/title/{r['imdbId']}"
            ) if kind == "series" or kind == "movie" and r["imdbId"] else None,
            InlineKeyboardButton(
                self._xlate("next_button"),
                callback_data=self.build_resp(cid, i, 'media', 'next')
            ) if total_results > 1 and i < total_results - 1 else None,
        ]
        keyboard.append(keyboardNavRow)

        no_add = False
        if tags:
            keyboard += [
                ([InlineKeyboardButton(
                    self._xlate("add_tag_button", tag=tag["label"]),
                    callback_data=self.build_resp(
                        cid, i, 'media', 'add', f'tt={tag["id"]}')
                )] for tag in tags[:12]),
                [InlineKeyboardButton(
                    self._xlate("finished_tagging_button"),
                    callback_data=self.build_resp(
                        cid, i, 'media', 'add', 'td=1')
                )],
            ]
        elif options:
            # monitor_button, add_quality_button, add_metadata_button
            keyboard += [
                ([InlineKeyboardButton(
                    self._xlate(option_kind, option=o),
                    callback_data=self.build_resp(
                        cid, i, 'media', 'add', f'm={k}')
                )] for k, o in enumerate(options)),
                # TODO pjordan: Fix the options variables type
            ]
        elif paths:
            keyboard += [
                ([InlineKeyboardButton(
                    self._xlate("add_path_button", path=p["path"]),
                    callback_data=self.build_resp(
                        cid, i, 'media', 'add', f'p={p["id"]}')
                )] for p in paths)
            ]
        else:
            no_add = True

        keyboardActRow = []
        if no_add:
            keyboardActRow += [
                InlineKeyboardButton(
                    self._xlate(
                        "add_button", kind=self._xlate(kind).title()),
                    callback_data=self.build_resp(cid, i, 'media', 'add')
                ) if not r["id"] else
                InlineKeyboardButton(
                    self._xlate("already_added_button"),
                    callback_data=self.build_resp(cid, i, 'media', 'noop')
                ),
            ]

        keyboardActRow += [
            InlineKeyboardButton(
                self._xlate("cancel_search_button"),
                callback_data=self.build_resp(cid, i, 'media', 'cancel')
            ),
        ]
        keyboard.append(keyboardActRow)

        reply_markup = InlineKeyboardMarkup(keyboard)

        if kind == "series":
            reply_message = f"{r['title']}{' (' + str(r['year']) + ')' if r['year'] and str(r['year']) not in r['title'] else ''} - {r['seasonCount']} Season{'s' if r['seasonCount'] != 1 else ''}{' - ' + r['network'] if r['network'] else ''} - {r['status'].title()}\n\n{r['overview']}"[
                0:1024
            ]
        elif kind == "movie":
            reply_message = f"{r['title']}{' (' + str(r['year']) + ')' if r['year'] and str(r['year']) not in r['title'] else ''}{' - ' + str(r['runtime']) + ' min' if r['runtime'] else ''} - {r['status'].title()}\n\n{r['overview']}"[
                0:1024
            ]
        elif kind == "book":
            try:
                release = datetime.strptime(
                    r["releaseDate"], "%Y-%m-%dT%H:%M:%SZ"
                ).strftime("%b %d, %Y")
            except (ValueError, TypeError):
                release = "???"
            reply_message = f"{r['author']['authorName']} - {r['title']}{' - ' + r['disambiguation'] if r['disambiguation'] else ''}{' - ' + r['seriesTitle'] if r['seriesTitle'] else ''} ({release})\n\n{r['overview']}"[
                0:1024
            ]
        else:
            reply_message = self._xlate("unexpected_error")

        return (reply_message, reply_markup)

    def service_cmd_callback(self, service, update, context):
        def handler(update, context):
            logger.debug(
                f"Received book cmd from [{update.message.from_user.username}]"
            )
            if not self.check_authenticated(update, context):
                return

            title = self._strip_entities(update.message)
            if not len(title):
                x_title = self._xlate("title").title()
                update.message.reply_text(
                    self._xlate(
                        "include_book_title_in_cmd",
                        commands=" OR ".join(
                            [f"`/{c} {x_title}`" for c in service.commands]
                        ),
                    )
                )
                return
            results = service.search(title)
            cid = self.db._generate_cid()
            self.db._create_conversation(
                id=cid,
                username=str(update.message.from_user.username),
                kind=service.commands[0],
                results=results,
            )

            if not len(results):
                update.message.reply_text(self._xlate("no_matching_books"))
            else:
                r = results[0]
                # TODO pjordan: Add this
                reply_message, reply_markup = self._prepare_response(
                    service.commands[0], r, cid, 0, len(results)
                )

        return handler

    def run(self):
        self.db._init_db()
        updater = Updater(self.token, use_context=True)

        for c in HELP_COMMANDS:
            logger.debug(f"Registering [/{c}] as a help command")
            updater.dispatcher.add_handler(CommandHandler(c, self.cmd_help))
        for c in START_COMMANDS:
            logger.debug(f"Registering [/{c}] as a start command")
            updater.dispatcher.add_handler(CommandHandler(c, self.cmd_start))

        for s in self.services():
            handler = self.service_cmd_callback(service)
            for c in s.commands:
                logger.debug(f"Registering [/{c}] as a {s.kind} command")
                updater.dispatcher.add_handler(CommandHandler(c, handler))

        updater.dispatcher.add_handler(CallbackQueryHandler(self.callback))
        if not self.DEV_MODE:
            updater.dispatcher.add_error_handler(self.handle_error)
        else:
            logger.info(
                "Developer mode is enabled; skipping registration of error handler--exceptions will be raised."
            )

        updater.start_polling()
        updater.idle()

    def _prepare_response_users(self, cid, users, offset, num, total_results):
        keyboard = []
        for u in users[offset: offset + num]:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        self._xlate("remove_user_button"),
                        callback_data=f"{cid}^^^{u['id']}^^^remove_user",
                    ),
                    InlineKeyboardButton(
                        f"{u['username'] if u['username'] != 'None' else u['id']}",
                        callback_data=f"{cid}^^^{u['id']}^^^noop",
                    ),
                    InlineKeyboardButton(
                        self._xlate("remove_admin_button")
                        if u["admin"]
                        else self._xlate("make_admin_button"),
                        callback_data=f"{cid}^^^{u['id']}^^^{'remove_admin' if u['admin'] else 'make_admin'}",
                    ),
                ]
            )
        keyboardNavRow = filter(lambda x: x is not None, [
            InlineKeyboardButton(
                self._xlate("prev_button"),
                callback_data=f"{cid}^^^{offset - num}^^^prev",
            ) if offset > 0 else None,
            InlineKeyboardButton(
                self._xlate("done"), callback_data=f"{cid}^^^{offset}^^^done"
            ),
            InlineKeyboardButton(
                self._xlate("next_button"),
                callback_data=f"{cid}^^^{offset + num}^^^next",
            ) if total_results > 1 and offset + num < total_results else None
        ])
        keyboard.append(keyboardNavRow)
        reply_markup = InlineKeyboardMarkup(keyboard)

        reply_message = self._xlate(
            "listing_users_pagination",
            page_info=f"{offset + 1}-{min(offset + num, total_results)} of {total_results}",
        )
        return (reply_message, reply_markup)

    def build_resp(self, cid, uid, cat, op, op_flags=None):
        # TODO pjordan: Add op_flags support
        return f"{cid}^^^{uid}^^^{cat}^^^{op}"

    def extract_resp(self, data):
        cid, uid, cat, op = data.split("^^^")
        op_flags = None
        if "^^" in op:
            op, op_flags = op.split("^^")
            op_flags = dict(parse_qsl(op_flags))
            for k, v in op_flags.items():
                logger.debug(
                    f"Adding/Updating additional data for cid=[{cid}], key=[{k}], value=[{v}]..."
                )
                self.db._update_add_data(cid, k, v)
        return (cid, int(uid), cat, op, op_flags)

    def reply_error(self, query, text):
        query.message.reply_text(text)
        query.message.delete()
        query.answer()

    def callback(self, update, context):
        query = update.callback_query
        logger.debug(
            f"Received callback from [{query.from_user.username}]: [{query.data}]"
        )

        if not (auth_level := self.db._authenticated(query.from_user.id)):
            return
        if not query.data or not len(query.data):
            query.answer()
            return

        cid, uid, cat, op, op_flags = self.extract_resp(query.data)

        if not (convo := self.db._get_conversation(cid)):
            self.reply_error(query, self._xlate("convo_not_found"))
            return

        if op == "noop":
            return
        elif cat == "media":
            if op == "cancel":
                self.db._delete_conversation(cid)
                query.message.reply_text(self._xlate("search_canceled"))
                query.message.delete()
            elif op == "done":
                self.db._delete_conversation(cid)
                query.message.delete()
            elif op == "prev":
                self.prev(update, context, convo, uid, cid)
            elif op == "next":
                self.next(update, context, convo, uid, cid)
            elif op == "add":
                self.add(update, context, convo, uid, cid)
        elif cat == "user" and auth_level == 2:
            if op == "remove_user":
                self.remove_user(query, context, convo, uid, cid)
            elif op == "make_admin":
                self.make_admin(query, context, convo, uid, cid)
            elif op == "remove_admin":
                self.remove_admin(query, context, convo, uid, cid)
        elif cat == "user":
            error_msg = self._xlate(
                "admin_auth_required",
                commands=" OR ".join([
                    f"`/{c} <{self._xlate('admin_password')}>`"
                    for c in START_COMMANDS
                ]))
            self.reply_error(query, error_msg)

    def prev(self, update, context, convo, i, cid):
        query = update.callback_query
        if convo["type"] == "users":
            if i <= 0:
                i = 0
            reply_message, reply_markup = self._prepare_response_users(
                cid,
                convo["results"],
                i,
                5,
                len(convo["results"]),
            )
            context.bot.edit_message_text(
                chat_id=query.message.chat.id,
                message_id=query.message.message_id,
                text=reply_message,
                reply_markup=reply_markup,
            )
        else:
            if i <= 0:
                query.answer()
                return
            r = convo["results"][i - 1]
            reply_message, reply_markup = self._prepare_response(
                convo["type"], r, cid, i - 1, len(convo["results"])
            )
            insert_media(
                "edit", update, context, reply_message, reply_markup, r["remotePoster"]
            )

    def next(self, update, context, convo, i, cid):
        query = update.callback_query
        if convo["type"] == "users":
            if i > len(convo["results"]):
                query.answer()
                return
            reply_message, reply_markup = self._prepare_response_users(
                cid,
                convo["results"],
                i,
                5,
                len(convo["results"]),
            )
            context.bot.edit_message_text(
                chat_id=query.message.chat.id,
                message_id=query.message.message_id,
                text=reply_message,
                reply_markup=reply_markup,
            )
        else:
            if i >= len(convo["results"]):
                query.answer()
                return
            r = convo["results"][i + 1]
            logger.debug(f"{r=}")
            reply_message, reply_markup = self._prepare_response(
                convo["type"], r, cid, i + 1, len(convo["results"])
            )
            insert_media(
                "edit", update, context, reply_message, reply_markup, r["remotePoster"]
            )

    def add(self, update, context, convo, i, cid):
        query = update.callback_query

        r = convo["results"][i]
        # TODO pjordan: Fix this
        additional_data = self.db._get_add_data(cid)
        logger.debug(f"{additional_data=}")
        service = next(
            [s for s in self.services if convo["type"] == s.commands[0]], None
        )
        assert service, "No active service found"
        paths = service.root_folders

        # def add(self,
        #         movie_info: Optional[Any] = None,
        #         tmdb_id: Optional[str] = None,
        #         search=True,
        #         monitored=True,
        #         min_avail="released",
        #         quality_profile: str = '',
        #         tags: List[str] = [],
        #         root_folder: str = '',
        #         ):
        def update_option(key, possible_values, error_msg):
            value = additional_data.get(key)
            if not value:
                if len(possible_values) > 1:
                    # prepare response to prompt user to select quality profile, and return
                    reply_message, reply_markup = self._prepare_response(
                        convo["type"],
                        r,
                        cid,
                        i,
                        len(convo["results"]),
                        add=True,
                        possible_values=possible_values,
                    )
                    insert_media(
                        "edit",
                        update,
                        context,
                        reply_message,
                        reply_markup,
                        r["remotePoster"],
                    )
                    query.answer()
                    return False
                elif len(possible_values) == 1:
                    self.db._update_add_data(cid, key, possible_values[0])
                else:
                    self.db._delete_conversation(cid)
                    query.message.reply_text(
                        self._xlate(
                            error_msg, kind=self._xlate(convo["type"]), app=service.kind
                        )
                    )
                    query.message.delete()
                    query.answer()
                    return False
            return True

        if not update_option("path_id", [p["path"] for p in paths], "no_root_folders"):
            return

        if not update_option(
            "quality_id",
            [p["id"] for p in service.quality_profiles],
            "no_quality_profiles",
        ):
            return

        if convo["type"] == "book" and not update_option(
            "metadata_id",
            [p["id"] for p in service.quality_profiles],
            "no_metadata_profiles",
        ):
            return

        if (
            convo["type"] == "series"
            and settings.sonarr_season_monitor_prompt
            and additional_data.get("m", False) is False
        ):
            # m = monitor season(s)
            monitor_options = [
                self._xlate("all_seasons"),
                self._xlate("first_season"),
                self._xlate("latest_season"),
            ]
            # prepare response to prompt user to select quality profile, and return
            reply_message, reply_markup = self._prepare_response(
                convo["type"],
                r,
                cid,
                i,
                len(convo["results"]),
                add=True,
                monitor_options=monitor_options,
            )
            insert_media(
                "edit", update, context, reply_message, reply_markup, r["remotePoster"]
            )
            query.answer()
            return

        all_tags = service.get_filtered_tags()
        allow_user_to_select_tags = service.allow_user_to_select_tags
        forced_tags = service.forced_tags
        if allow_user_to_select_tags and not additional_data.get("td"):
            if not len(all_tags):
                logger.warning(
                    f"User tagging is enabled, but no tags found. Make sure there are tags{' in Sonarr' if convo['type'] == 'series' else ' in Radarr' if convo['type'] == 'movie' else ' in Readarr' if convo['type'] == 'book' else ''} matching your Searcharr configuration."
                )
            elif not additional_data.get("tt"):
                reply_message, reply_markup = self._prepare_response(
                    convo["type"],
                    r,
                    cid,
                    i,
                    len(convo["results"]),
                    add=True,
                    tags=all_tags,
                )
                insert_media(
                    "edit",
                    update,
                    context,
                    reply_message,
                    reply_markup,
                    r["remotePoster"],
                )
                query.answer()
                return
            else:
                tag_ids = (
                    additional_data.get("t", "").split(",")
                    if len(additional_data.get("t", ""))
                    else []
                )
                tag_ids.append(additional_data["tt"])
                logger.debug(f"Adding tag [{additional_data['tt']}]")
                self._update_add_data(cid, "t", ",".join(tag_ids))
                return

        tags = (
            additional_data.get("tags").split(",")
            if len(additional_data.get("tags", ""))
            else []
        )
        logger.debug(f"{tags=}")
        if settings.tag_with_username:
            tag = f"searcharr-{query.from_user.username if query.from_user.username else query.from_user.id}"
            if tag_id := service.get_tag_id(tag):
                tags.append(str(tag_id))
            else:
                self.logger.warning(
                    f"Tag lookup/creation failed for [{tag}]. This tag will not be added to the {convo['type']}."
                )
        for tag in forced_tags:
            if tag_id := service.get_tag_id(tag):
                tags.append(str(tag_id))
            else:
                self.logger.warning(
                    f"Tag lookup/creation failed for forced tag [{tag}]. This tag will not be added to the {convo['type']}."
                )
        self.db._update_add_data(cid, "tags", ",".join(list(set(tags))))

        logger.debug("All data is accounted for, proceeding to add...")
        try:
            if convo["type"] == "series":
                added = service.add_series(
                    series_info=r,
                    monitored=settings.sonarr_add_monitored,
                    search=settings.sonarr_search_on_add,
                    additional_data=self._get_add_data(cid),
                )
            elif convo["type"] == "movie":
                added = service.add_movie(
                    movie_info=r,
                    monitored=settings.radarr_add_monitored,
                    search=settings.radarr_search_on_add,
                    min_avail=settings.radarr_min_availability,
                    additional_data=self._get_add_data(cid),
                )
            elif convo["type"] == "book":
                added = service.add_book(
                    book_info=r,
                    monitored=settings.readarr_add_monitored,
                    search=settings.readarr_search_on_add,
                    additional_data=self._get_add_data(cid),
                )
            else:
                added = False
        except Exception as e:
            logger.error(f"Error adding {convo['type']}: {e}")
            added = False
        logger.debug(f"Result of attempt to add {convo['type']}: {added}")
        if added:
            self.db._delete_conversation(cid)
            query.message.reply_text(self._xlate("added", title=r["title"]))
            query.message.delete()
        else:
            query.message.reply_text(
                self._xlate("unknown_error_adding", kind=convo["type"])
            )

    def remove_user(self, query, context, convo, uid, cid):
        try:
            self.db._remove_user(uid)
            convo.update({"results": self.db._get_users()})
            self.db._create_conversation(
                id=cid,
                username=str(query.message.from_user.username),
                kind="users",
                results=convo["results"],
            )
            reply_message, reply_markup = self._prepare_response_users(
                cid,
                convo["results"],
                0,
                5,
                len(convo["results"]),
            )
            context.bot.edit_message_text(
                chat_id=query.message.chat.id,
                message_id=query.message.message_id,
                text=f"{self._xlate('removed_user', user=uid)} {reply_message}",
                reply_markup=reply_markup,
            )
        except Exception as e:
            logger.error(f"Error removing all access for user id [{uid}]: {e}")
            query.message.reply_text(
                self._xlate("unknown_error_removing_user", user=uid)
            )

    def make_admin(self, query, context, convo, uid, cid):
        try:
            self.db._update_admin_access(uid, "1")
            convo.update({"results": self.db._get_users()})
            self.db._create_conversation(
                id=cid,
                username=str(query.message.from_user.username),
                kind="users",
                results=convo["results"],
            )
            reply_message, reply_markup = self._prepare_response_users(
                cid,
                convo["results"],
                0,
                5,
                len(convo["results"]),
            )
            context.bot.edit_message_text(
                chat_id=query.message.chat.id,
                message_id=query.message.message_id,
                text=f"{self._xlate('added_admin_access', user=uid)} {reply_message}",
                reply_markup=reply_markup,
            )
        except Exception as e:
            logger.error(f"Error adding admin access for user id [{uid}]: {e}")
            query.message.reply_text(
                self._xlate("unknown_error_adding_admin", user=uid)
            )

    def remove_admin(self, query, context, convo, uid, cid):
        try:
            self.db._update_admin_access(uid, "")
            convo.update({"results": self.db._get_users()})
            self.db._create_conversation(
                id=cid,
                username=str(query.message.from_user.username),
                kind="users",
                results=convo["results"],
            )
            reply_message, reply_markup = self._prepare_response_users(
                cid,
                convo["results"],
                0,
                5,
                len(convo["results"]),
            )
            context.bot.edit_message_text(
                chat_id=query.message.chat.id,
                message_id=query.message.message_id,
                text=f"{self._xlate('removed_admin_access', user=uid)} {reply_message}",
                reply_markup=reply_markup,
            )
        except Exception as e:
            logger.error(
                f"Error removing admin access for user id [{uid}]: {e}")
            query.message.reply_text(
                self._xlate("unknown_error_removing_admin", user=uid)
            )
        query.answer()


@click.command("buttlarr")
def cli():
    logger.info("Initializing buttlarr database")
    db = Database()
    logger.info("Initializing buttlarr service")
    tgr = Buttlarr(db, TELEGRAM_TOKEN, SERVICES)
    logger.info("Starting telegram listener")
    tgr.run()


if __name__ == "__main__":
    cli()
