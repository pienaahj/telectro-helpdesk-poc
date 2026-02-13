#!/usr/bin/env bash
set -euo pipefail
source .env.local
./bin/bench.sh --site "$SITE_NAME" migrate
