from .secrets import APIS

from ..services.radarr import Radarr
from ..services.sonarr import Sonarr

SERVICES = [
    Radarr(
        commands=["movie"],
        api_host=APIS.get("movie")[0],
        api_key=APIS.get("movie")[1],
    ),
    Sonarr(
        commands=["series"],
        api_host=APIS.get("series")[0],
        api_key=APIS.get("series")[1],
    ),
    Sonarr(
        commands=["anime"],
        api_host=APIS.get("anime")[0],
        api_key=APIS.get("anime")[1],
    ),
]
