#!/usr/bin/env bash
set -euo pipefail

# Bring everything up first
./bin/up.sh

# Install helpdesk + telephony (and do the node/yarn PATH fixes, build, restart, ping check)
./bin/helpdesk-install.sh
