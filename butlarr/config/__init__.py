import yaml
import os

# Import config
CONFIG_FILE = os.getenv("BUTLARR_CONFIG_FILE") or "config.yaml"
with open(CONFIG_FILE, "r") as config_file:
    CONFIG = yaml.safe_load(config_file)
