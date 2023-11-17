from .radarr import Radarr
from .database import Database

TELEGRAM_TOKEN = "asdf"
SERVICES = [
    Radarr(
        commands=["series"],
        api_host="http://thinkpad-media:7878/",
        api_key="99b57eecfa644021bc4cc59dc7edbb94",
    )
]
DB = Database()
START_COMMANDS = ["/start"]
HELP_COMMANDS = ["/help"]
