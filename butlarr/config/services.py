import importlib
from loguru import logger

from . import CONFIG

APIS = CONFIG["apis"]
SERVICES = []

def _constructor(service_type):
    try:
        service_module = importlib.import_module(f"butlarr.services.{service_type.lower()}")
        return getattr(service_module, service_type)
    except Exception:
        assert False, f"Could not find a module for service {service_type}"

# Keep the namespace clean
def _load_services():
    # Two step approach, due to addons requiering all services to be loaded beforehand
    named_services = {}
    for service in CONFIG["services"]:

        ServiceConstructor = _constructor(service["type"])

        api_config = APIS[service["api"]]
        service_name = service.get("name")

        args = {
            "name": service_name,
            "commands": service["commands"],
            "api_host": api_config["api_host"],
            "api_key": api_config["api_key"],
            "addons": service.get("addons", []),
        }

        service = ServiceConstructor(**args)
        SERVICES.append(service)

        if service_name:
            assert service_name not in named_services, "Different services have been named the same!"
            named_services[service_name] = service
    
    for service in SERVICES:
        logger.info(f"Loading {service.name} addons")
        addons = []
        for addon in service.addons:
            addon_service = named_services[addon["service_name"]]
            if service.arr_variant in (addon_service.supported_services):
                addons.append(addon_service)
                logger.info(f"Addon {addon_service.name} loaded")
            else:
                assert False, f"Unsupported addon service type {service.arr_variant}!"

        service.addons = addons
        logger.debug(f"{service.name} service loaded Addons: {str(service.addons)}")

_load_services()