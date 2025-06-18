#!/usr/bin/env bash

set -a
# Source the env file (default to .env)
source "${1:-.env}"

# Open venv
source "$(dirname "$0")/common_linux.sh"
find_repo_root
open_venv

# Finally start bot
echo " |> Starting butlarr"
python -m butlarr

