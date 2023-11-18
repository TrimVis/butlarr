from .radarr import Radarr

TELEGRAM_TOKEN = "6543834997:AAG7q5TknnpzzGYdYwjqCpTIf_oiXE9ATE0"
SERVICES = [
    Radarr(
        commands=["series"],
        api_host="http://thinkpad-media:7878/",
        api_key="99b57eecfa644021bc4cc59dc7edbb94",
    )
]
START_COMMANDS = ["/start"]
HELP_COMMANDS = ["/help"]
