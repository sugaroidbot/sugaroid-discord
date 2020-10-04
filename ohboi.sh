#!/bin/bash

# script to run sugaroid automatically and reload it
set -e

sginit="$(which python3) discord_bot.py"

until "$sginit"; do
    echo "Respawning sugaroid bot"
    sleep 1
done
