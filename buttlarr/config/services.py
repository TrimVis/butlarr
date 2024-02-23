from .secrets import API_KEYS, API_HOSTS

from ..services.radarr import Radarr
from ..services.sonarr import Sonarr

SERVICES = [
    Radarr(
        commands=["movie"],
        api_host=API_HOSTS[0],
        api_key=API_KEYS[0],
    ),
    Sonarr(
        commands=["series"],
        api_host=API_HOSTS[1],
        api_key=API_KEYS[1],
    ),
    Sonarr(
        commands=["anime"],
        api_host=API_HOSTS[2],
        api_key=API_KEYS[2],
    )
]
