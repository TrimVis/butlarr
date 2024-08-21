import importlib
from loguru import logger

from . import CONFIG

APIS = CONFIG["apis"]
SERVICES = []


# Keep the namespace clean
def _load_services():
    # Two step approach, due to addons requiering all services to be loaded beforehand
    named_services = {}
    for service in CONFIG["services"]:
        try:
            service_module = importlib.import_module(f"butlarr.services.{service['type'].lower()}")
            ServiceConstructor = getattr(service_module, service["type"])
        except Exception:
            assert False, "Could not find a module for that service"

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
            for addon_service in SERVICES:
                if addon_service.name == addon.get("service_name"):
                    if addon_service.arr_variant in service.supported_addons:
                        addons.append(addon_service)
                        logger.info(f"Addon {addon_service.name} loaded")
                    else:
                        assert False, f"Unsupported addon service type {addon.get('type')}!"
                        return False
        service.addons = addons
        logger.debug(f"{service.name} service loaded Addons: {str(service.addons)}")

_load_services()