import importlib
from loguru import logger

from . import CONFIG

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
            "commands": service["commands"],
            "api_host": api_config["api_host"],
            "api_key": api_config["api_key"],
            "name": service.get("name", service["commands"][0])
        }

        SERVICES.append(ServiceConstructor(**args))
        service_addons.append(service.get("addons", []))

    for (service, addons) in zip(SERVICES, service_addons):
        if not addons:
            continue

        logger.info(f"Injecting addons for '{service.name}'")
        service.inject_addons([
            s
            for s in SERVICES
            if s.name in addons
        ])


_load_services()
