from ..radarr import Radarr
from .secrets import API_KEYS

SERVICES = [
    Radarr(
        commands=["series"],
        api_host="http://thinkpad-media:7878/",
        api_key=API_KEYS[0],
    )
]
