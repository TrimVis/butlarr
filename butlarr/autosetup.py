from dataclasses import dataclass
from typing import List
import re
import os

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
    n = 0
    cdir = "."
    for n in range(10):
        if ".git" in os.listdir(cdir):
            break
        cdir = f"../{cdir}"
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

    return Service(["/" + cmd], service[0].upper() + service[1:], service, url, api_key)


def create_services_py(services, write_out=True, base_path="."):
    imports = "\n".join(["from ..services.radarr import Radarr" for s in services])
    services = "\n".join(
        [
            f"""{s.class_name}(
        commands=["{s.commands[0]}"],
        api_host=APIS.get("{s.commands[0]}")[0],
        api_key=APIS.get("{s.commands[0]}")[1],
    ),"""
            for s in services
        ]
    )
    content = f"""from .secrets import APIS

{imports}

SERVICES = [
    {services}
]
"""

    if write_out:
        with open(f"{base_path}/butlarr/config/services.py", "w+") as f:
            f.writelines(content)
    return content


def create_secrets_py(
    telegram_token, auth_password, services, write_out=True, base_path="."
):
    apis = "\n".join(
        [f'"{s.commands[0]}": ("{s.url}", "{s.api_key}"),' for s in services]
    )
    content = f"""TELEGRAM_TOKEN = \"{telegram_token}\"
AUTH_PASSWORD = \"{auth_password}\"

APIS = {{
    {apis}
}}
"""
    if write_out:
        with open(f"{base_path}/butlarr/config/secrets.py", "w+") as f:
            f.writelines(content)
    return content


def main():
    base_path = detect_base_path()

    telegram_token = input("Your telegram bot token:  ")
    auth_password = input("Your authentication password (/auth <PW>):  ")

    print("Adding new services...")
    new_services = []
    while s := service_setup(hide_done=not len(new_services)):
        new_services.append(s)

    print(
        "If you continue, your inputs will be written out. The current config files will be overwritten!"
    )
    print(
        f"Make sure to back up {base_path}/config/secrets.py and {base_path}/config/services.py if you want to keep them."
    )
    if input("Do you want to continue? (y/n)  ").strip().lower() != "y":
        print("Exiting setup. Did not write any config files.")
        print()
        print()

        print(f"{base_path}/butlarr/config/secrets.py content would have been:")
        print(
            create_secrets_py(
                telegram_token,
                auth_password,
                new_services,
                write_out=False,
                base_path=base_path,
            )
        )
        print()
        print(f"{base_path}/butlarr/config/services.py content would have been:")
        print(create_services_py(new_services, write_out=False, base_path=base_path))
        exit(0)

    print(f"Creating {base_path}/butlarr/config/secrets.py...")
    create_secrets_py(telegram_token, auth_password, new_services, base_path=base_path)
    print(f"Creating {base_path}/butlarr/config/services.py...")
    create_services_py(new_services, base_path=base_path)
    print("All config files have been succesfully created. Your bot should be setup.")
    print("You can start the bot by using one of the start scripts:")
    for f in os.listdir(f"{base_path}/scripts"):
        if f.startswith("start_"):
            print(f" - {base_path}/scripts/{f}")


if __name__ == "__main__":
    main()
