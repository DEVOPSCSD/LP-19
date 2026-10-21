#!/bin/sh
set -e

# If no arguments provided, launch the Flask web application on 0.0.0.0:5000
if [ $# -eq 0 ]; then
    exec python -m src.web_app
fi

# If first argument starts with a dash (e.g. --help, --backup, --source), forward to CLI
if [ "${1#-}" != "$1" ]; then
    exec python src/main.py "$@"
fi

# Otherwise execute the passed command (e.g. python, pytest, sh)
exec "$@"