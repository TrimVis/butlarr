from loguru import logger
from typing import Optional, List, Any, Literal
from dataclasses import dataclass, replace

from . import ArrService, ArrVariant, Action, ServiceContent, find_first
from .ext import ExtArrService, QueueState, Addon, AddonState
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
class State(AddonState):
    items: List[Any]
    index: int
    arrvariant: ArrVariant
    media_id: int
    subtitle: str
    menu: Optional[
        Literal["list"] | Literal["download"]
    ]


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
        if state.sstate.menu:
            rows_action.append([Button("🔙 Go Back", state.service.get_clbk(state.return_to_menu))])
        elif state.menu:
            rows_action.append([Button("🔙 Back", self.get_clbk("goto"))])
        else:
            rows_action.append([Button("❌ Cancel", self.get_clbk("cancel"))])

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
    
    
    def search(self, arrvariant, id):
        if arrvariant == ArrVariant.RADARR:
            status = self.request('providers/movies', params={'radarrid': id}, fallback=[])
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
            
            params = {
                "radarrid": id, 
                "hi": item.get('hearing_impaired'), 
                "forced": item.get('forced'),
                "original_format": item.get('original_format'),
                "provider": item.get('provider'),
                "subtitle": item.get('subtitle'),
                **options
            }

            return self.request(
                'providers/movies',
                action=Action.POST,
                params=params,
                raw=True
            )
        else:
            logger.error(
                f"Bazarr integration with service {service} is Not Implemented"
            )
            return False

    
    def create_message(self, state: State, full_redraw=False, allow_edit=False):
        if not state.items:
            keyboard_markup = self.keyboard(state, allow_edit=allow_edit)

            return Response(
                caption='',
                reply_markup=keyboard_markup,
                state=state,
            )

        item = state.items[state.index]

        keyboard_markup = self.keyboard(state, allow_edit=allow_edit)

        return Response(
            caption='',
            reply_markup=keyboard_markup,
            state=state,
        )


    @repaint
    @callback(
        cmds=[
            "goto"
            "list"
            "download"
        ]
    )
    @sessionState()
    @authorized(min_auth_level=AuthLevels.USER)
    async def clbk_update(self, update, context, args, state):

        logger.error("clbk_update")

        auth_level = get_auth_level_from_message(self.db, update)
        allow_edit = auth_level >= AuthLevels.MOD.value
        # Prevent any changes from being made if in library and permission level below MOD
        if args[0] in ["download"]:
            item = state.items[state.index]
            if "id" in item and item["id"] and not allow_edit:
                # Don't do anything, illegal operation
                return self.create_message(state, allow_edit=False)

        full_redraw = False
        if args[0] == "goto":
            if len(args) > 1:
                idx = int(args[1])
                item = state.items[idx]
                state = replace(
                    state,
                    index=idx,
                    menu=None,
                )
                full_redraw = True
            else:
                state = replace(state, menu=None)

        if args[0] == "download":
            if len(args) > 1:
                idx = int(args[1])
                item = state.items[idx]
                state = replace(
                    state,
                    index=idx,
                    subtitle=item.get('release_info')[0],
                    menu="download",
                )
                full_redraw = True
            else:
                state = replace(state, menu="download")

        if args[0] == "list":
            state = replace(
                    state,
                    index=0,
                    menu="success",
                )
        return self.create_message(
            state, full_redraw=full_redraw, allow_edit=allow_edit
        )

    
    @repaint
    @command(default=True)
    @sessionState(init=True)
    @callback(cmds=["list"])
    @authorized(min_auth_level=AuthLevels.USER)
    async def clbk_list(self, update, context, args):

        media_id = args[1]
        arrvariant = self.current_service.arr_variant
        sstate = self.current_service_state
        
        items = self.search(arrvariant=arrvariant, id=media_id)  

        state = State(
            items=items,
            index=0,
            arrvariant=arrvariant,
            media_id=media_id,
            subtitle='',
            menu="list",
            service=self.current_service,
            sstate=self.current_service_state,
            return_to_menu=self.return_to_menu
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

        logger.debug(f"Return to menu {state.return_to_menu}")

        state = replace(
                    state,
                    index=0,
                    menu="success",
                )

        result = self.download(
            id = state.media_id,
            service=state.arrvariant,
            item=state.items[state.index]
        )

        if result.status_code < 200 \
        or result.status_code > 299:
            return Response(caption=f"Something went wrong... {result.content}")
        
        return self.create_message(state, full_redraw=False)


    @callback(cmds=["cancel"])
    @sessionState(clear=True)
    @authorized(min_auth_level=AuthLevels.USER)
    async def clbk_cancel(self, update, context, args, state):
        return Response(caption="Subtitle Search canceled!")
    
    @Addon.setAddon
    def addon_buttons(self, state=None, **kwargs):
        sstate = kwargs.get('sstate')
        item = sstate.items[sstate.index]
        downloaded = True if "movieFile" in item else False
        subtitle = f"({state.subtitle})" if state else ''

        buttons = []
        if sstate.menu == "add" and downloaded:
            buttons.append(
                Button(
                    f"Subtitles {subtitle}",
                    self.get_clbk("list", item.get("id"))
                ),
            )
        return buttons
