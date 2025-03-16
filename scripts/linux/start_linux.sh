#!/usr/bin/env bash

source "$(dirname "$0")/common_linux.sh"
find_repo_root
open_venv

# Finally start bot
echo " |> Starting butlarr"
python -m butlarr
