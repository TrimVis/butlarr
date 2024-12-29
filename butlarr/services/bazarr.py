from loguru import logger
from typing import Optional, List, Any, Literal
from dataclasses import dataclass, replace

from . import ArrService, ArrVariant, Action, ServiceContent
from .addon import Addon
from ..tg_handler import callback, handler
from ..tg_handler.message import (
    Response,
    repaint,
)
from ..tg_handler.auth import (
    authorized, AuthLevels, get_auth_level_from_message
)
from ..tg_handler.session_state import (
    sessionState,
)
from ..tg_handler.keyboard import Button, keyboard


@dataclass(frozen=True)
class State:
    items: List[Any]
    index: int
    arr_variant: ArrVariant
    media_id: int
    menu: Optional[
        Literal["list"] | Literal["download"]
    ]
    parent: Any


@handler
class Bazarr(Addon):
    def __init__(
        self,
        commands: List[ArrService],
        api_host: str,
        api_key: str,
        name: str,
    ):
        if len(commands) != 0:
            logger.error(
                "Bazarr can only be used as an addon." +
                " Ignoring the 'commands' provided"
            )
            commands = []
        super().__init__()

        self.api_key = api_key
        self.name = name
        self.commands = commands

        self.api_version = self.detect_api(api_host)
        self.service_content = ServiceContent.SUBTITLES
        self.arr_variant = ArrVariant.BAZARR

        self.supported_services = [ArrVariant.RADARR, ArrVariant.SONARR]

    @keyboard
    def keyboard(self, state: State, allow_edit=False):
        row_navigation = []
        rows_menu = []
        rows_action = []

        parent = state.parent

        if state.menu == 'list':
            if len(state.items) > 0:
                row_navigation = [Button("=== Subtitles ===", "noop")]
            else:
                row_navigation = [Button("=== No subtitles found ===", "noop")]

            current_index = 0
            for item in state.items:
                description = f"[Score: {item['score']}]"
                description += f" {item['release_info'][0]}"
                description = description[0:1024]
                rows_menu.append(
                    [
                        Button(
                            description,
                            self.get_clbk("download", state.index),
                        ),
                    ]
                )
                current_index = current_index + 1
                if current_index >= 5:
                    break

        if state.menu == 'success':
            row_navigation = [Button("Subtitle downloaded!", "noop")]

        if parent.menu:
            # Back to menu defined on "addon_buttons" function
            rows_action.append(
                [Button("🔙 Back", parent.service.get_clbk(parent.menu))])
        elif parent.state.menu:
            # Back to current parent menu
            rows_action.append(
                [Button("🔙 Back", parent.service.get_clbk(parent.state.menu))])
        elif state.menu:
            # back to current addon menu (not used yet)
            rows_action.append([Button("🔙 Back", self.get_clbk(state.menu))])

        return [row_navigation, *rows_menu, *rows_action]

    # NOTE: Overwrite needed, as api_version will not be detected otherwise
    def detect_api(self, api_host):
        status = None
        # Detect version and api_url
        try:
            self.api_url = f"{api_host.rstrip('/')}/api"
            status = self.request("system/status")
        except Exception:
            pass

        if not status:
            logger.error(
                f"Could not reach compatible api. Is the service ({
                    self.api_url}) down? Is your API key correct?"
            )
            exit(1)
        api_version = status.get("data", {}).get("bazarr_version", "")
        assert api_version, "Could not find compatible api."
        return api_version

    def search(self, arr_variant, id):
        if arr_variant == ArrVariant.RADARR:
            status = self.request('providers/movies',
                                  params={'radarrid': id}, fallback=[])
            return status.get('data') if len(status) > 0 else status
        if arr_variant == ArrVariant.SONARR:
            status = self.request('providers/episodes',
                                  params={'episodeid': id}, fallback=[])
            return status.get('data') if len(status) > 0 else status
        else:
            assert False, "Bazarr integration not Implemented"

    def download(
        self,
        service,
        id,
        item=None,
        options={},
    ):
        assert item, "Missing required arg! You need to provide a item!"

        if service == ArrVariant.RADARR:

            method = 'providers/movies'
            params = {
                "radarrid": id,
                "hi": item.get('hearing_impaired'),
                "forced": item.get('forced'),
                "original_format": item.get('original_format'),
                "provider": item.get('provider'),
                "subtitle": item.get('subtitle'),
                **options
            }

        elif service == ArrVariant.SONARR:

            method = 'providers/episodes'
            params = {
                "seriesid": item.get('id'),
                "episodeid": id,
                "hi": item.get('hearing_impaired'),
                "forced": item.get('forced'),
                "original_format": item.get('original_format'),
                "provider": item.get('provider'),
                "subtitle": item.get('subtitle'),
                **options
            }

        else:
            logger.error(
                f"Bazarr integration with service {service} is Not Implemented"
            )
            return False

        return self.request(
            method,
            action=Action.POST,
            params=params,
            raw=True
        )

    def create_message(
            self, state: State, full_redraw=False, allow_edit=False
    ):
        if not state.items:
            keyboard_markup = self.keyboard(state, allow_edit=allow_edit)

            return Response(
                caption='',
                reply_markup=keyboard_markup,
                state=state,
            )

        parent = state.parent

        media_item = parent.state.items[parent.state.index]

        if ArrVariant(parent.service.arr_variant) == ArrVariant.SONARR:
            reply_message = parent.service.episode_caption(media_item)
        else:
            reply_message = parent.service.get_media_caption(media_item)

        keyboard_markup = self.keyboard(state, allow_edit=allow_edit)

        return Response(
            caption=reply_message,
            reply_markup=keyboard_markup,
            state=state,
        )

    @repaint
    @sessionState(init=True)
    @callback(cmds=["list"])
    @authorized(min_auth_level=AuthLevels.USER)
    async def clbk_list(self, update, context, args, **kwargs):
        parent = kwargs.get('parent')

        media_item = parent.state.items[parent.state.index]
        media_id = media_item["id"] or args[1]

        arr_variant = parent.service.arr_variant

        items = self.search(arr_variant=arr_variant, id=media_id)

        state = State(
            items=items,
            index=0,
            arr_variant=arr_variant,
            media_id=media_id,
            menu="list",
            parent=parent
        )

        auth_level = get_auth_level_from_message(self.db, update)
        allow_edit = auth_level >= AuthLevels.USER.value
        return self.create_message(
            state, full_redraw=False, allow_edit=allow_edit
        )

    @repaint
    @callback(cmds=["download"])
    @sessionState(clear=True)
    @authorized(min_auth_level=AuthLevels.USER)
    async def clbk_add(self, update, context, args, state):

        logger.debug(f"Return to menu {state.parent.state.menu}")

        state = replace(
            state,
            index=0,
            menu="success",
        )

        result = self.download(
            id=state.media_id,
            service=state.arr_variant,
            item=state.items[state.index]
        )

        if result.status_code < 200 \
                or result.status_code > 299:
            return Response(
                caption=f"Something went wrong... {result.content}"
            )

        return self.create_message(state, full_redraw=False)

    def addon_buttons(self, service, state):
        item = state.items[state.index]

        if ArrVariant(service.arr_variant) == ArrVariant.RADARR:
            return self.radarr_integration(service, state, item)
        elif ArrVariant(service.arr_variant) == ArrVariant.SONARR:
            return self.sonarr_integration(service, state, item)

        raise NotImplementedError(
            f'{service.arr_variant} integration not implemented')

    def radarr_integration(self, service, state, item, **kwargs):
        downloaded = True if "movieFile" in item else False

        if downloaded and state.menu == "add":
            movieId = item.get("id")

            return [
                Button(
                    "🔍 Search for Subtitles",
                    self.get_clbk("list", movieId)
                ),
            ]

        return []

    def sonarr_integration(self, service, state, item, **kwargs):
        in_library = "id" in item and item["id"]

        if in_library and state.menu == "episode":
            episodeId = item['selectedEpisodeId']
            episode = service.get_episode(episodeId)
            downloaded = True if episode['hasFile'] else False

            if downloaded:
                return [
                    Button(
                        "🔍 Search for Subtitles",
                        self.get_clbk("list", episodeId)
                    ),
                ]
        elif in_library:
            return [
                Button(
                    "🔍 Search for Subtitles",
                    service.get_clbk("season_list")
                ),
            ]

        return []
