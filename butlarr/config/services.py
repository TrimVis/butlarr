from . import CONFIG
from ..services.radarr import Radarr
from ..services.sonarr import Sonarr

APIS = CONFIG["apis"]
SERVICES = []

for service in CONFIG["services"]:
    service_type = service["type"]
    commands = service["commands"]
    api_config = APIS[service["api"]]

    subtitles = service.get("subtitles")
    if subtitles:
        subtitles["api"] = APIS[subtitles["api"]]
        
    if service_type == "Radarr":
        radarr = Radarr(
                    commands=commands,
                    api_host=api_config["api_host"],
                    api_key=api_config["api_key"],
                    subtitles=subtitles
                )
                
        SERVICES.append(radarr)
        if subtitles:
            SERVICES.append(radarr.subtitles)
            
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
