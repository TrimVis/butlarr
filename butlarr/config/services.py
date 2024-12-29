import importlib
from loguru import logger

from . import CONFIG
from ..services.addon import Addon

APIS = CONFIG["apis"]
SERVICES = []


def _constructor(service_type):
    try:
        service_module = importlib.import_module(
            f"butlarr.services.{service_type.lower()}")
        return getattr(service_module, service_type)
    except Exception:
        assert False, f"Could not find a module for service {service_type}"

# Keep the namespace clean


def _load_services():
    service_addons = []
    for service in CONFIG["services"]:

        ServiceConstructor = _constructor(service["type"])

        api_config = APIS[service["api"]]

        args = {
            "commands": service.get("commands", []),
            "api_host": api_config["api_host"],
            "api_key": api_config["api_key"],
            "name": service.get("name", None)
        }

        assert args["name"], f"Missing 'name' field for '{service['type']}'"

        SERVICES.append(ServiceConstructor(**args))
        service_addons.append(service.get("addons", []))

    for (service, addons) in zip(SERVICES, service_addons):
        if not addons:
            continue

        logger.info(f"Injecting addons for '{service.name}'")
        addon_services = [
            s
            for s in SERVICES
            if s.name in addons
        ]
        for addon in addon_services:
            assert isinstance(addon, Addon), \
                "The addon wrapper can only be used with addons"
        service.inject_addons(addon_services)


_load_services()
