from . import CONFIG
from ..services.radarr import Radarr
from ..services.sonarr import Sonarr
from ..services.bazarr import Bazarr

APIS = CONFIG["apis"]
SERVICES = []

for service in CONFIG["services"]:
    name = service.get("name")
    service_type = service["type"]
    commands = service["commands"]
    api_config = APIS[service["api"]]
    addons = service.get("addons", [])
        
    if service_type == "Radarr":               
        SERVICES.append(
            Radarr(
                commands=commands,
                api_host=api_config["api_host"],
                api_key=api_config["api_key"],
                name=name,
                addons=addons
            )
        )

    elif service_type == "Sonarr":
        SERVICES.append(
            Sonarr(
                commands=commands,
                api_host=api_config["api_host"],
                api_key=api_config["api_key"],
                name=name,
                addons=addons
            )
        )

    elif service_type == "Bazarr":
        SERVICES.append(
            Bazarr(
                commands=commands,
                api_host=api_config["api_host"],
                api_key=api_config["api_key"],
                name=name,
                addons=addons
            )
        )

    else:
        assert False, f"Unsupported service type {service_type}!"

for service in SERVICES:
    if len(service.addons) > 0:
        service.load_addons()
