from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional, Any
import requests
from .tg_handler import TelegramHandler
from .session_database import SessionDatabase


class Action(Enum):
    GET = "get"
    POST = "post"


class ArrService(TelegramHandler):
    name: str
    api_url: str
    api_key: str
    api_version: str

    root_folders: List[str]
    session_db: SessionDatabase

    def _post(self, endpoint, params={}):
        return requests.post(
            f"{self.api_url}/{endpoint}", params={"apikey": self.api_key}, json=params
        )

    def _get(self, endpoint, params={}):
        return requests.get(
            f"{self.api_url}/{endpoint}", params={"apikey": self.api_key, **params}
        )

    def request(self, endpoint: str, *, action=Action.GET, params={}, fallback=None):
        r = (
            self._get(endpoint, params)
            if action == Action.GET
            else self._post(endpoint, params)
        )
        if not r:
            return fallback

        return r.json()
