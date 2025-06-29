# Butlarr
>
> Your personal butler for all your *arr* needs & services

## Why use Butlarr

*Butlarr* is a telegram bot that allows multiple people to interact with *arr* instances.
It allows the addition and management of movies, series, and more.

*Butlarr* has been created with hackability and base compatibility in mind.
If you have a service that behaves logically the same as Sonarr or Radarr, it will be compatible with *Butlarr*.
Even if it is not compatible, it is relatively simple to extend the existing code base for various other services.

## Features

### Search

Search for media using `/movie <search term>`, `/series <search term>` or any other configured command

![image](https://github.com/TrimVis/butlarr/assets/29759576/089bb19a-01d6-4d89-bc92-f42128200bf0)

### Library Management

Manage search results from inside telegram.
Change the quality profile, assign/remove tags, etc.

![image](https://github.com/TrimVis/butlarr/assets/29759576/9bb30521-ba02-4045-9e1a-06e425d64ce7)

### Queue

For Sonarr and Radarr, there is native support to display the queue and its download progress.
To use it, you can use the `queue` subcommand.

E.g., if you configured Sonarr on the `series` command, use:

```bash
/series queue
```

## Basic Usage

After following the [Setup](#setup) and [Configuration](#configuration), ensure the bot is running.
Open the telegram chat to the bot and authorize yourself using your previously set `AUTH_PASSWORD`:

```bash
/auth <A_SECURE_PASSWORD>
```

Show a basic help page using `/help`
To add a movie, for example, you could send `/movie Alvin`

![image](https://github.com/TrimVis/butlarr/assets/29759576/089bb19a-01d6-4d89-bc92-f42128200bf0)
![image](https://github.com/TrimVis/butlarr/assets/29759576/9bb30521-ba02-4045-9e1a-06e425d64ce7)

## Installation

### Setup

Butlarr can be configured a number of different ways, refere to these corresponding sections to learn more on these configuration methods:
- Interactively using the [Interactive Setup](#automatic-configuration)
- Manually using [Environment Variables](#environment-variables)
- Manually using a [Configuration File](#configuration-file)

#### Docker

##### Interactive Setup
1. Run the automatic setup: `docker run -it -e BUTLARR_INTERACTIVE_SETUP=true trimforce/butlarr:latest`
2. Start the container `docker run trimforce/butlarr:latest`

##### Environment Variables
```bash
docker run -e BUTLARR_USE_ENV_CONFIG=true -e [OTHER_VARIABLE]=[OTHER_VALUE] trimforce/butlarr:latest
```

##### Configuration File
```bash
docker run -v ./config.yaml:/app/config.yaml  trimforce/butlarr:latest 
```

#### Docker Compose

##### Interactive Setup
1. Run the automatic setup: `docker run -it -e BUTLARR_INTERACTIVE_SETUP=true trimforce/butlarr:latest`
2. Copy over/Create a new `docker-compose.yml` file with content:
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
    ```

##### Environment Variables
```yaml
services:
    butlarr:
        container_name: butlarr
        image: trimforce/butlarr:latest
        volumes:
        - ./data:/app/data
        environment:
        - BUTLARR_INTERACTIVE_SETUP=false
        - BUTLARR_USE_ENV_CONFIG=true
        - TELEGRAM_BOT_TOKEN="<YOUR_TELEGRAM_TOKEN>"
        - BUTLARR_ADMIN_PASSWORD="<SECURE_UNIQUE_PASSWORD>"
        - BUTLARR_MOD_PASSWORD="<SECURE_UNIQUE_PASSWORD>"
        - BUTLARR_USER_PASSWORD="<SECURE_UNIQUE_PASSWORD>"
        - ...
        restart: unless-stopped
```


##### Configuration File
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
```

#### Quick Local Setup

> This setup currently only supports Linux and Windows
> If you are interested in running this on any other OS, please refer to the Docker and Docker Compose instructions

##### Linux

1. First, clone the repository and cd into it

    ```bash
    git clone git@github.com:TrimVis/butlarr.git && cd butlarr
    ```

2. Run start script

    ```bash
    ./scripts/linux/start_linux.sh
    ```

This will do steps 2, 3, and 5 of the Manual Setup.


##### Windows

1. Ensure you can run scripts in powershell

    ```Powershell
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
    ```


2. First, clone the repository and cd into it

    ```Powershell
    git clone git@github.com:TrimVis/butlarr.git && cd butlarr
    ```

3. Run start script

    ```Powershell
    ./scripts/windows/start_windows.ps1
    ```

This will do steps 2, 3, and 5 of the Manual Setup.

#### Manual Setup

1. First, clone the repository and cd into it

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

4. Configure butlarr (see [Configuration](#configuration))
5. Start the service

    ```bash
    python -m butlarr
    ```

### Configuration

#### Automatic Configuration

An automatic setup helper is available. You can run it by executing the `./scripts/linux/autosetup_linux.sh` or `/scripts/windows/autosetup_windows.ps1` file from the repository directory.

If you are working with docker, use: `docker run -it -e BUTLARR_INTERACTIVE_SETUP=true trimforce/butlarr:latest`

#### Manual Configuration

There are two ways to manually configure *Bazarr*, either use a `config.yaml` file for configuration, or alternatively configure your instance via environment variables.

##### Configuration File
After cloning the repository and `cd`ing into the repository, create a new file at `config.yaml`.
Paste and adapt the template [templates/config.yaml](./templates/config.yaml)

##### Environment Variables
Ensure that the `BUTLARR_USE_ENV_CONFIG` environment variable is set to either `true` or `1`.
For a detailed description on how services are configured using environment variables, refer to the [env config template](./templates/config.env).

##### Roles
There are 3 unique roles available: admin, mod, and user.
A user can only add movies but cannot remove or edit existing entries.
A mod can do both of these.
A admin will have all possible permissions, currently this is equivalent to the mod user.
The `auth_passwords` should be unique, if they are not the user will always be upgraded to the highest possible role.

### Systemd service

Create a new file under `/etc/systemd/user` (recommended: `/etc/systemd/user/butlarr.service`)
The new file should have the following content (you have to adapt the `REPO_PATH`):

```ini
[Unit]
Description      = Butlarr Telegram Bot for Arr Service Management
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
