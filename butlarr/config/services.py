import importlib
from loguru import logger

from . import CONFIG
from ..services.addon import Addon

APIS = CONFIG["apis"]
SERVICES = []


def find_service_by_name(service_name):
    for s in SERVICES:
        if s.name == service_name:
            return s

    raise IndexError("Such a service does not exist")


def _constructor(service_type):
    try:
        service_module = importlib.import_module(
            f"butlarr.services.{service_type.lower()}")
        return getattr(service_module, service_type)
    except Exception:
        assert False, f"Could not find a module for service {service_type}"

# Keep the namespace clean


# TODO: Add proper validation for all fields and api
def _load_services():
    service_addons = []
    for service in CONFIG["services"]:
        # FIXME: "name" can not be a required argument for bw compat
        assert "name" in service, f"Missing 'name' field for '{
            service['type']}'"
        #  assert "commands" in service, f"Missing 'commands' field for '{
        #      service['type']}'"

        ServiceConstructor = _constructor(service["type"])

        api_config = APIS[service["api"]]

        args = {
            "commands": service.get("commands", []),
            "api_host": api_config["api_host"],
            "api_key": api_config["api_key"],
            "name": service["name"]
        }

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
