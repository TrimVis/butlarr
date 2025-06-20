#!/usr/bin/env bash

find_repo_root() {
    # Detect the repository root folder
    MAX_DEPTH=3
    while [[ $MAX_DEPTH -gt 0 ]]; do
        NO_HITS=$(find "." -maxdepth 1 -type d -name ".git" | wc -l)
        if [[ $NO_HITS -gt 0 ]]; then
            break
        fi
        cd ..
        ((MAX_DEPTH--))
    done
    echo " |> Found repository root at: $PWD"

    if [[ $MAX_DEPTH -lt 0 ]]; then
        echo " |> ERROR: Could not find repository directory."
        echo " |> ERROR: Make sure to run this from within the repository."
        echo " |> Exiting..."
        exit 1
    fi
}

open_venv() {
    # Open venv (or set everything up in case it doesn't exist)
    source venv/bin/activate &>/dev/null
    if [ $? == 1 ]; then
        echo " |> venv not set up. Creating one & installing dependencies"
        if command -v python &>/dev/null; then
            python -m venv venv
        elif command -v python3 &>/dev/null; then
            python3 -m venv venv
        else
            echo " |> ERROR: No python executable found."
            echo " |> ERROR: Please install python to continue setup."
            echo " |> Exiting..."
            exit 1
        fi
        source "venv/bin/activate"
        pip install -r "requirements.txt"

        printf " |> \n |> \n |> \n"
    fi
}
