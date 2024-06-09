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

#### Docker

1. Configure butlarr (see *Configuration* for manual configuration)

    ```bash
    docker run -it -e BUTLARR_INTERACTIVE_SETUP=true trimforce/butlarr:latest
    ```

2. Run the container

    ```bash
    docker run trimforce/butlarr:latest
    ```

#### Docker Compose

1. Configure butlarr (see *Configuration* for manual configuration)

    ```bash
    docker run -it -e BUTLARR_INTERACTIVE_SETUP=true trimforce/butlarr:latest
    ```

2. Copy over/Create a new `docker-compose.yml` file, with content:

    ```yaml
    services:
        butlarr:
            container_name: butlarr
            image: trimforce/butlarr:latest
            volumes:
            - ./data:/app/data
            - ./config.yaml:/app/config.yaml
            environment:
            - BUTLARR_CONFIG_FILE=./config.yaml
            - BUTLARR_INTERACTIVE_SETUP=false
            restart: unless-stopped
            network_mode: host
    ```

#### Quick Local Setup

> This setup currently only supports linux
> If you are interested in running this on any other OS, please refer to the Docker and Docker Compose instructions

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

If you are working with docker, use:

```bash
docker run -it -e BUTLARR_INTERACTIVE_SETUP=true trimforce/butlarr:latest
```

#### Manual Configuration

After cloning the repository and `cd`ing into the repository, create a new file at `config.yaml`.
Paste and adapt the following template `templates/config.yaml`:

```yaml
telegram: 
  token: "<YOUR_TELEGRAM_TOKEN>"

auth_passwords:
  admin: "<SECURE_UNIQUE_PASSWORD>"
  mod: "<SECURE_UNIQUE_PASSWORD>"
  user: "<SECURE_UNIQUE_PASSWORD>"

apis:
  movie:
    api_host: "<HOST_API_0>"
    api_key: "<API_KEY_0>"
  series:
    api_host: "<HOST_API_1>"
    api_key: "<API_KEY_1>"

services:
  - type: "Radarr"
    commands: ["movie"]
    api: "movie"
  - type: "Sonarr"
    commands: ["series"]
    api: "series"
```

There are 3 unique roles available: admin, mod and user.
A user can only add movies, but not remove or edit existing entries.
A mod can do both of these.
A admin will have all possible permissions, currently this is equivalent to the mod user.
The `auth_passwords` should be unique, if they are not the user will always be upgraded to the highest possible role.

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

- [ ] Create a pip package
- [ ] Add more permission levels

> Developed by TrimVis.
