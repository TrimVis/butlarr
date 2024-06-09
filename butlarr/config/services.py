from . import CONFIG
from ..services.radarr import Radarr
from ..services.sonarr import Sonarr

APIS = CONFIG["apis"]
SERVICES = []

for service in CONFIG["services"]:
    service_type = service["type"]
    commands = service["commands"]
    api_config = APIS[service["api"]]

    if service_type == "Radarr":
        SERVICES.append(
            Radarr(
                commands=commands,
                api_host=api_config["api_host"],
                api_key=api_config["api_key"]
            )
        )
    elif service_type == "Sonarr":
        SERVICES.append(
            Sonarr(
                commands=commands,
                api_host=api_config["api_host"],
                api_key=api_config["api_key"]
            )
        )
    else:
        assert False, "Unsupported service type!"
