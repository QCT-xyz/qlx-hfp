#!/usr/bin/env sh
set -e
: "${PORT:=8080}"
exec uvicorn src.service_app:app --host 0.0.0.0 --port "${PORT}"
