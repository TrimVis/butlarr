# Butlarr
>
> Your personal butler for all your *arr* needs & services

## Why use Butlarr

*Butlarr* is a telegram bot that allows the interaction of multiple people with *arr* instances.
It allows the addition and managment of movies, series, and more to come.

*Butlarr* has been created with hackability and base-compatibility in mind.
If you have a service that behaves logically the same as Sonarr or Radarr it will be compatible with *Butlarr*.
Even if it is not compatible, it is relatively simple to extend the exesting code base for various other services.

## Features

### Search

Search for media using `/movie <search term>`, `/series <search term>` or any other configured command

![image](https://github.com/TrimVis/butlarr/assets/29759576/089bb19a-01d6-4d89-bc92-f42128200bf0)

### Library Management

Manage search results from inside telegram.
Change the quality profile, assign/remove tags, etc.

![image](https://github.com/TrimVis/butlarr/assets/29759576/9bb30521-ba02-4045-9e1a-06e425d64ce7)

### Queue

For sonarr and radarr there is native support to display the queue and it's download progress.
To use it you can use the `queue` subcommand.

E.g. if you configured sonarr on the `series` command, use:

```bash
/series queue
```

## Basic Usage

After following the *Setup* and *Configuration*, ensure that the bot is running.
If not you can start it using: `python -m butlarr` from the repository directory.
Open the telegram chat to the bot and authorize yourself using your previously set `AUTH_PASSWORD`:

```bash
/auth <A_SECURE_PASSWORD>
```

Show a basic help page using `/help`
To add a movie for example, you could send `/movie Alvin`

![image](https://github.com/TrimVis/butlarr/assets/29759576/089bb19a-01d6-4d89-bc92-f42128200bf0)
![image](https://github.com/TrimVis/butlarr/assets/29759576/9bb30521-ba02-4045-9e1a-06e425d64ce7)

## Installation

### Setup

#### Quick Setup

1. First clone the repository and cd into it

    ```bash
    git clone git@github.com:TrimVis/butlarr.git && cd butlarr
    ```

2. Run start script

    ```bash
    ./scripts/start_linux.sh
    ```

This will do steps 2, 3 and 5 of the Manual Setup.

#### Manual Setup

1. First clone the repository and cd into it

    ```bash
    git clone git@github.com:TrimVis/butlarr.git && cd butlarr
    ```

2. (Optional) Create a new venv & source it

    ```bash
    python -m venv venv && source venv/bin/activate
    ```

3. Install dependencies

    ```bash
    python -m venv venv && source venv/bin/activate
    ```

4. Configure butlarr (see *Configuration*)
5. Start the service

```bash
python -m butlarr
```

### Configuration

#### Automatic Configuration

There is an automatic setup helper available. You can run it by executing the `./scripts/autosetup_linux.sh` file from the repository directory.

#### Manual Configuration

After cloning the repository and `cd`ing into the repository, create a new file at `butlarr/config/secrets.py`.
Paste and adapt the following template `secrets.py`:

```python
TELEGRAM_TOKEN = "<YOUR_TELEGRAM_TOKEN>"
AUTH_PASSWORD = "<A_SECURE_PASSWORD>"

APIS = {
    "movie": ("http://localhost:7878/", "<RADARR_API_KEY>"),
    "series": ("http://localhost:8989/", "<SONARR_API_KEY>"),
}
```

You will also have to add service instances, create a new file at `butlarr/config/services.py`.
Paste and adapt the following template `services.py`:

```python
from .secrets import APIS

from ..services.radarr import Radarr 
from ..services.sonarr import Sonarr

SERVICES = [
    Radarr(
        commands=["movie"],
        api_host=APIS.get("movie")[0],
        api_key=APIS.get("movie")[1],
    ),
    Sonarr(
        commands=["series"],
        api_host=APIS.get("series")[0],
        api_key=APIS.get("series")[1],
    ),
]
```

### Systemd service

Create a new file under `/etc/systemd/user` (recommended: `/etc/systemd/user/butlarr.service`)
The new file should have following content (you have to adapt the `REPO_PATH`):

```ini
[Unit]
Description      = Butlarr Telegram Bot for Arr Service Managment
After            = network.target
After            = systemd-user-sessions.service
After            = network-online.target

[Service]
Type              = simple
WorkingDirectory  = <REPO_PATH>
ExecStart         = /bin/bash -c 'source venv/bin/activate; python -m butlarr'
ExecReload        = /bin/kill -s HUP $MAINPID
KillMode          = mixed
TimeoutStopSec    = 300
Restart           = always
RestartSec        = 60
SyslogIdentifier  = butlar

[Install]
WantedBy         = multi-user.target
```

You can find a template at: `templates/butlarr.service`

Start it using: `systemctl --user start butlarr`
Enable it to start on reboots using: `systemctl --user enable butlarr`

## Open TODOs

- [ ] Create docker instructions
- [ ] Create a pip package
