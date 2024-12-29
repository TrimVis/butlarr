from typing import List, Any
from functools import wraps

from . import ArrService


class Addon(ArrService):
    supported_services = []

    def __init__(self):
        super().__init__()

    def addon_buttons(self, service, state):
        raise NotImplementedError


ADDON_PLACEHOLDER = object()


def addon_buttons(func):
    def inject_addon_buttons(buttons: List[Any], addon_buttons):
        assert buttons.count(ADDON_PLACEHOLDER) >= 1, \
            "Exactly one 'ADDON_PLACEHOLDER' is required"

        split_id = buttons.index(ADDON_PLACEHOLDER)
        return [
            *buttons[:split_id],
            *addon_buttons,
            *buttons[split_id + 1:]
        ]

    @wraps(func)
    def wrapped_func(*args, **kwargs):
        buttons = func(*args, **kwargs)

        addon_buttons = []
        for addon in args[0].addons:
            addon_buttons.append(
                addon.addon_buttons(args[0], args[1]))

        return inject_addon_buttons(buttons, addon_buttons)

    return wrapped_func
