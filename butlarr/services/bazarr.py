from loguru import logger
from typing import Optional, List, Any, Literal
from dataclasses import dataclass, replace

from . import ArrService, ArrVariant, Action, ServiceContent, find_first
from .ext import ExtArrService, QueueState, Addon, ParentState
from ..tg_handler import command, callback, handler
from ..tg_handler.message import (
    Response,
    repaint,
    clear,
)
from ..tg_handler.auth import authorized, AuthLevels, get_auth_level_from_message
from ..tg_handler.session_state import (
    sessionState,
    default_session_state_key_fn,
)
from ..tg_handler.keyboard import Button, keyboard


@dataclass(frozen=True)
class State():
    items: List[Any]
    index: int
    arr_variant: ArrVariant
    media_id: int
    menu: Optional[
        Literal["list"] | Literal["download"]
    ]
    parent: Optional[ParentState]


@handler
class Bazarr(ExtArrService, ArrService, Addon):
    def __init__(
        self,
        commands: List[str],
        api_host: str,
        api_key: str,
        name: str = None,
        addons: List[ArrService] = []
    ):
        self.commands = commands
        self.api_key = api_key
        
        self.api_version = self.detect_api(api_host)
        self.service_content = ServiceContent.SUBTITLES
        self.arr_variant = ArrVariant.BAZARR

        self.name = name
        self.supported_addons = []
        self.addons = addons
        
    
    @keyboard
    def keyboard(self, state: State, allow_edit=False):

        row_navigation = []
        rows_menu = []
        rows_action = []

        parent = state.parent.service
        parent_menu = state.parent.menu
        parent_state = state.parent.state
        
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
                if current_index >= 5: break
        
        if state.menu == 'success':
            row_navigation = [Button("Subtitle downloaded!", "noop")]
        if parent_menu:
            rows_action.append([Button("🔙 Back", parent.get_clbk(parent_menu))])
        elif parent_state.menu:
            rows_action.append([Button("🔙 Back", parent.get_clbk(parent_state.menu))])
        

        return [row_navigation, *rows_menu, *rows_action]


    def detect_api(self, api_host):
        status = None
        # Detect version and api_url
        try:
            self.api_url = f"{api_host.rstrip('/')}/api"
            status = self.request("system/status")
        finally:
            if status is None:
                logger.error(
                    "Could not reach compatible api. Is the service down? Is your API key correct?"
                )
                exit(1)
            assert (
                status
            ), "Could not reach compatible api. Is the service down? Is your API key correct?"
            api_version = status.get("data", {}).get("bazarr_version", "")
            assert api_version, "Could not find compatible api."
            return api_version
    
    
    def search(self, arr_variant, id):
        if arr_variant == ArrVariant.RADARR:
            status = self.request('providers/movies', params={'radarrid': id}, fallback=[])
            return status.get('data') if len(status) > 0 else status
        if arr_variant == ArrVariant.SONARR:
            status = self.request('providers/episodes', params={'episodeid': id}, fallback=[])
            return status.get('data') if len(status) > 0 else status
        else:
            assert False, f"Bazarr integration not Implemented"

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

    
    def create_message(self, state: State, full_redraw=False, allow_edit=False):
        if not state.items:
            keyboard_markup = self.keyboard(state, allow_edit=allow_edit)

            return Response(
                caption='',
                reply_markup=keyboard_markup,
                state=state,
            )
        
        item = state.items[state.index]

        parent_service = state.parent.service
        parent_state = state.parent.state
        media_item = parent_state.items[parent_state.index]

        if ArrVariant(parent_service.arr_variant) == ArrVariant.SONARR:
            reply_message = parent_service.episode_caption(media_item)
        else:
            reply_message = parent_service.media_caption(media_item)

        keyboard_markup = self.keyboard(state, allow_edit=allow_edit)

        return Response(
            caption=reply_message,
            reply_markup=keyboard_markup,
            state=state,
        )

    @command(default=True)
    @command(cmds=[("help", "", "Shows only the bazarr help page")])
    async def cmd_help(self, update, context, args):
        return await ExtArrService.cmd_help(self, update, context, args)

    @repaint
    @sessionState(init=True)
    @callback(cmds=["list"])
    @authorized(min_auth_level=AuthLevels.USER)
    @Addon.load
    async def clbk_list(self, update, context, args, **kwargs):

        media_id = args[1]
        arr_variant = self.service.arr_variant
        parent_state = self.state
        
        items = self.search(arr_variant=arr_variant, id=media_id)  

        state = State(
            items=items,
            index=0,
            arr_variant=arr_variant,
            media_id=media_id,
            menu="list",
            parent=kwargs.get('parent')
        )

        self.session_db.add_session_entry(
            default_session_state_key_fn(self, update), state
        )

        auth_level = get_auth_level_from_message(self.db, update)
        allow_edit = auth_level >= AuthLevels.USER.value
        return self.create_message(state, full_redraw=False, allow_edit=allow_edit)

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
            id = state.media_id,
            service=state.arr_variant,
            item=state.items[state.index]
        )

        if result.status_code < 200 \
        or result.status_code > 299:
            return Response(caption=f"Something went wrong... {result.content}")
        
        return self.create_message(state, full_redraw=False)
    
    @Addon.config
    def addon_buttons(self, **kwargs):
        parent_state = self.state
        item = parent_state.items[parent_state.index]
        in_library = "id" in item and item["id"]

        buttons = []
        if ArrVariant(self.service.arr_variant) == ArrVariant.RADARR:
            downloaded = True if "movieFile" in item else False

            if parent_state.menu == "add" and downloaded:
                movieId = item.get("id")
                
                buttons.append(
                    Button(
                        f"Search for subtitles",
                        self.get_clbk("list", movieId)
                    ),
                )

        elif ArrVariant(self.service.arr_variant) == ArrVariant.SONARR:

            if parent_state.menu == "add" and in_library:
                buttons.append(
                    Button(
                        f"Get Subtitles",
                        self.service.get_clbk("seasons")
                    ),
                )

            elif parent_state.menu == "episode" and in_library:

                episodeId = item['selectedEpisodeId']
                episode = self.service.get_episode(episodeId)
                downloaded = True if episode['hasFile'] else False

                if downloaded:
                    buttons.append(
                        Button(
                            f"Search for subtitles",
                            self.get_clbk("list", episodeId)
                        ),
                    )
        
        return buttons
