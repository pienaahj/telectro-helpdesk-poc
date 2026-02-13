#!/usr/bin/env bash
set -euo pipefail
./bin/bench.sh get-app erpnext --branch "$ERPNEXT_TAG"
./bin/bench.sh --site "$SITE_NAME" install-app erpnext
# Helpdesk
./bin/bench.sh get-app helpdesk --branch main
./bin/bench.sh --site "$SITE_NAME" install-app helpdesk
./bin/bench.sh migrate
