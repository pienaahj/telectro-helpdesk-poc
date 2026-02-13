#!/usr/bin/env bash
set -euo pipefail

docker compose -f compose.yaml restart backend websocket queue-long queue-short scheduler frontend
