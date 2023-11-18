from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional, Any
import requests
from .telegram_handler import TelegramHandler

KeyListType = Optional[List[Tuple[str, Optional[Any]]]]


class Action(Enum):
    GET = 'get',
    POST = 'post',


def ensure_keys(obj, keys):
    return {key: obj.get(key, default_value) for (key, default_value) in keys}


@dataclass(frozen=True)
class Endpoints:
    status: str
    root_folders: str
    profiles: str
    search: str
    add: str
    tag: str
    add_tag: str


@dataclass(frozen=True)
class EndpointKeys:
    status: KeyListType = None
    root_folders: KeyListType = None
    profiles: KeyListType = None
    search: KeyListType = None
    add: KeyListType = None
    tag: KeyListType = None
    add_tag: KeyListType = None


class ArrService(TelegramHandler):
    name: str
    api_url: str
    api_key: str
    api_version: str

    endpoints: Endpoints
    preserved_keys: EndpointKeys
    root_folders: List[str]

    def _post(self, endpoint, params={}):
        return requests.post(
            f"{self.api_url}/{endpoint}",
            params={'apikey': self.api_key},
            json=params
        )

    def _get(self, endpoint, params={}):
        return requests.get(
            f"{self.api_url}/{endpoint}",
            params={'apikey': self.api_key, **params}
        )

    def _interact(self, action: Action, key: str, params={}, fallback=None):
        endpoint = getattr(self.endpoints, key)
        preserved_keys = getattr(self.preserved_keys, key)
        r = (
            self._get(endpoint, params) if action == Action.GET
            else self._post(endpoint, params)
        )
        if not r:
            return fallback

        result = r.json()
        if not preserved_keys:
            return result
        if isinstance(result, list):
            return [ensure_keys(e, preserved_keys) for e in result]
        return ensure_keys(result, preserved_keys)

    def _get_endpoint(self, key: str, params={}, fallback=None):
        return self._interact(Action.GET, key, params, fallback)

    def _post_endpoint(self, key: str, params={}, fallback=None):
        return self._interact(Action.POST, key, params, fallback)
