from .secrets import APIS

from ..services.radarr import Radarr

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
]
