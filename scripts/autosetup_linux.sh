#!/usr/bin/env bash

source venv/bin/activate &> /dev/null

if [ $? == 1 ]
then
    echo " |> venv not set up. Creating one & installing dependencies"
    if command -v python &> /dev/null
    then
        python -m venv venv
    elif command -v python3 &> /dev/null
    then
        python3 -m venv venv
    else
        echo " |> ERROR: No python executable found."
        echo " |> ERROR: Please install python to continue setup."
        echo " |> Exiting..."
        exit 1
    fi
    source venv/bin/activate
    pip install -r requirements.txt;

    printf " |> \n |> \n |> \n"
fi

echo " |> Starting butlarr autosetup"
python -m butlarr.autosetup


