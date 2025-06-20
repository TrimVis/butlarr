#!/usr/bin/env bash

source "$(dirname "$0")/common_linux.sh"
find_repo_root
open_venv

echo " |> Starting butlarr autosetup"
python -m butlarr.autosetup


