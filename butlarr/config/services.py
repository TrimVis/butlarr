import importlib

from . import CONFIG

APIS = CONFIG["apis"]
SERVICES = []

for service in CONFIG["services"]:
    try:
        service_module = importlib.import_module(f"butlarr.services.{service['type'].lower()}")
        ServiceConstructor = getattr(service_module, service["type"])
    except Exception:
        assert False, "Could not find a module for that service"

    api_config = APIS[service["api"]]
    args = {
        "name": service.get("name"),
        "commands": service["commands"],
        "api_host": api_config["api_host"],
        "api_key": api_config["api_key"],
        "addons": service.get("addons", [])
    }

    SERVICES.append(ServiceConstructor(**args))

for service in SERVICES:
    if len(service.addons) > 0:
        service.load_addons()