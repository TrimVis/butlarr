from dataclasses import dataclass
from loguru import logger
from enum import Enum
from typing import List, Tuple, Optional, Any
import requests
from ..tg_handler import TelegramHandler
from ..session_database import SessionDatabase


def find_first(elems, check, fallback=0):
    try:
        result = next(e for e in elems if check(e))
    except:
        result = None
    finally:
        if not result:
            return elems[fallback]
        return result


class Action(Enum):
    GET = "get"
    POST = "post"
    DELETE = "delete"


class ArrVariants(Enum):
    UNSUPPORTED = None
    RADARR = "movie"
    SONARR = "series"


class ArrService(TelegramHandler):
    name: str
    api_url: str
    api_key: str
    api_version: str
    api_variant = ArrVariants.UNSUPPORTED

    root_folders: List[str] = []
    session_db: SessionDatabase = SessionDatabase()

    def _post(self, endpoint, params={}):
        return requests.post(
            f"{self.api_url}/{endpoint}", params={"apikey": self.api_key}, json=params
        )

    def _get(self, endpoint, params={}):
        return requests.get(
            f"{self.api_url}/{endpoint}", params={"apikey": self.api_key, **params}
        )

    def _delete(self, endpoint, params={}):
        return requests.delete(
            f"{self.api_url}/{endpoint}", params={"apikey": self.api_key, **params}
        )

    def request(self, endpoint: str, *, action=Action.GET, params={}, fallback=None):
        r = None
        if action == Action.GET:
            r = self._get(endpoint, params)
        elif action == Action.POST:
            r = self._post(endpoint, params)
        elif action == Action.DELETE:
            r = self._delete(endpoint, params)

        if not r:
            return fallback

        if action != Action.DELETE:
            return r.json()
        return r

    def detect_api(self, api_host):
        status = None
        # Detect version and api_url
        try:
            self.api_url = f"{api_host.rstrip('/')}/api/v3"
            status = self.request("system/status")
            if not status:
                self.api_url = f"{api_host.rstrip('/')}/api"
                status = self.request("system/status")
                assert not status, "By default only v3 ArrServices are supported"
        finally:
            if status is None:
                logger.error(
                    "Could not reach compatible api. Is the service down? Is your API key correct?"
                )
                exit(1)
            assert (
                status
            ), "Could not reach compatible api. Is the service down? Is your API key correct?"
            api_version = status.get("version", "")
            assert api_version, "Could not find compatible api."
            return api_version

    def get_queue_item(self, id: int):
        return self.request(
            f"queue/{id}",
            params=params,
            fallback=[],
        )

    def get_queue(self, page: int = None, page_size: int = None):
        params = {}
        if page != None:
            params["page"] = page
        if page_size != None:
            params["page_size"] = page_size
        return self.request(
            "queue",
            params=params,
            fallback=[],
        )

    def get_queue_details(self, movie_id: int = None, include_movie: bool = None):
        params = {}
        if movie_id:
            params["movieId"] = movie_id
        if include_movie != None:
            params["includeMovie"] = include_movie
        return self.request(
            "queue",
            params=params,
            fallback=[],
        )

    def get_queue_detail(self, id: int):
        return self.request(
            f"queue/details/{id}",
            params={},
            fallback=[],
        )

    def lookup(self, term: str = None):
        if not self.arr_variant:
            return NotImplementedError(
                "Unsupported Arr variant. You have to implement your own search"
            )
        if not term:
            return []

        return self.request(
            f"{self.arr_variant.value}/lookup",
            params={"term": term},
            fallback=[],
        )

    def add(
        self,
        *,
        item=None,
        root_folder_path: str = "",
        quality_profile_id: str = "",
        language_profile_id: str = "",
        min_availability="released",
        tags: List[str] = [],
        monitored=True,
        options={},
    ):
        assert item, "Missing required arg! You need to provide a item!"

        return self.request(
            self.arr_variant.value,
            action=Action.POST,
            params={
                **item,
                "qualityProfileId": quality_profile_id,
                "languageProfileId": language_profile_id,
                "rootFolderPath": root_folder_path,
                "tags": tags,
                "monitored": monitored,
                "minimumAvailability": min_availability,
                **options,
            },
        )

    def remove(self, *, id=None):
        assert id, "Missing required arg! You need to provide a id!"
        return self.request(
            f"{self.arr_variant.value}/{id}",
            action=Action.DELETE,
        )

    def get_root_folders(self) -> List[str]:
        return self.request("rootfolder", fallback=[])

    def get_root_folder(self, id: str) -> List[str]:
        return self.request(f"rootfolder/{id}", fallback={})

    def get_tags(self):
        return self.request("tag", fallback=[])

    def get_tag(self, id: str):
        return self.request(f"tag/{id}", fallback={})

    def add_tag(self, label):
        return self.request(
            "tag", action=Action.POST, params={"label": label}, fallback={}
        )

    def get_quality_profiles(self):
        return self.request("qualityprofile", fallback=[])

    def get_quality_profile(self, id):
        return self.request(f"qualityprofile/{id}", fallback={})

    def get_language_profiles(self):
        return self.request("languageprofile", fallback=[])

    def get_language_profile(self, id):
        return self.request(f"languageprofile/{id}", fallback={})