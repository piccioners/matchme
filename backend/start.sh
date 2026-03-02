#!/usr/bin/env sh
set -e

PORT_TO_USE="${PORT:-8080}"
exec gunicorn --bind "0.0.0.0:${PORT_TO_USE}" wsgi:app
