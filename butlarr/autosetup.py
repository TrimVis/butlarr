from dataclasses import dataclass
from typing import List
from pprint import pprint
import re
import os
import yaml

CONFIG_FILE_LOCATION = os.getenv("BUTLARR_CONFIG_FILE")

SERVICES = [
    "done",
    "sonarr",
    "radarr",
]


@dataclass(frozen=True)
class Service:
    commands: List[str]
    class_name: str
    class_file: str
    url: str
    api_key: str


def detect_base_path():
    found = False
    cdir = "."
    for _ in range(10):
        if ".git" in os.listdir(cdir):
            found = True
            break
        cdir = f"../{cdir}"
    if not found:
        return "."
    return cdir.removesuffix("/.")


def check_cmd(text):
    url_regex = r"^/?(\S*)$"
    matches = re.findall(url_regex, text)
    if matches:
        return matches[0]
    return None


def check_url(text):
    url_regex = r"(https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}(\.[a-z]{2,4})?(:\d+)?\b([-a-zA-Z0-9@:%_\+.~#?&//=]*))"
    matches = re.findall(url_regex, text)
    if matches:
        return matches[0][0]
    return None


def service_setup(hide_done=False):
    print("What kind of service would you like to setup?")
    print("Options:")
    for i, s in list(enumerate(SERVICES))[(1 if hide_done else 0) :]:
        print(f" {i} - {s}")

    service = None
    while not service:
        try:
            service_id = int(
                input(f"Input your selection [{'1' if hide_done else '0'}-2]:  ")
            )
            service = SERVICES[service_id]
            if service == "done":
                if not hide_done:
                    return None
                else:
                    service = None
        except Exception:
            pass

    print("Input the url under which the service's api is reachable.")
    print("(e.g. http://localhost:8080, http://192.168.178.1:7878)")
    url = None
    while not (url := check_url(input("URL:  ").strip())):
        print("Your input is not a valid url")
    assert url, "No URL found"

    print("Input the service's api key below")
    api_key = input("API Key:  ").strip()

    print("Input the telegram command that this service should react to:")
    print("(e.g. /series, /movies")
    while not (cmd := check_cmd(input("Command:  ").strip())):
        print(
            "Your input is not a valid command. No whitespace inside a command allowed"
        )
    assert cmd, "No command found"

    return Service([cmd], service[0].upper() + service[1:], service, url, api_key)


def create_config_yaml(
    services,
    telegram_token,
    admin_auth_password,
    mod_auth_password,
    user_auth_password,
    config_file=None,
):
    config = {
        "telegram": {"token": telegram_token},
        "auth_passwords": {
            "admin": admin_auth_password,
            "mod": admin_auth_password,
            "user": admin_auth_password,
        },
        "apis": {
            s.commands[0]: {"api_host": s.url, "api_key": s.api_key} for s in services
        },
        "services": [
            {
                "type": s.class_name,
                "commands": s.commands,
                "api": s.commands[0],
            }
            for s in services
        ],
    }

    if config_file:
        with open(config_file, "w+") as f:
            yaml.safe_dump(config, f)
    return yaml.safe_dump(config)


def main():
    base_path = detect_base_path()
    config_file = CONFIG_FILE_LOCATION or f"{base_path}/config.yaml"

    telegram_token = input("Your telegram bot token:  ")
    print("You will now set various authentication passwords (/auth <PW>)")
    user_auth_password = input("User role, can only add entries:  ")
    while True:
        mod_auth_password = input("Mod role, can add and edit entries:  ")
        if user_auth_password != mod_auth_password:
            break
        print("All passwords have to be unique! Please try again.")
    while True:
        admin_auth_password = input("Admin role, can do anything:  ")
        if mod_auth_password != admin_auth_password:
            break
        print("All passwords have to be unique! Please try again.")

    print("Adding new services...")
    new_services = []
    while s := service_setup(hide_done=not len(new_services)):
        new_services.append(s)

    print(
        "If you continue, your inputs will be written out. The current config file will be overwritten!"
    )
    print(f"Make sure to back up {config_file} if you want to keep them.")
    if input("Do you want to continue? (y/n)  ").strip().lower() != "y":
        print("Exiting setup. Did not write any config files.")
        print()
        print()

        print(f"'{config_file}' content would have been:")
        pprint(
            create_config_yaml(
                new_services,
                telegram_token,
                admin_auth_password,
                mod_auth_password,
                user_auth_password,
            )
        )
        exit(0)

    print(f"Creating '{config_file}'...")
    create_config_yaml(
        new_services,
        telegram_token,
        admin_auth_password,
        mod_auth_password,
        user_auth_password,
        config_file=config_file,
    )

    print("All config files have been succesfully created. Your bot should be setup.")
    print("You can start the bot by using one of the start scripts:")
    for f in os.listdir(f"{base_path}/scripts"):
        if f.startswith("start_"):
            print(f" - {base_path}/scripts/{f}")


if __name__ == "__main__":
    main()
