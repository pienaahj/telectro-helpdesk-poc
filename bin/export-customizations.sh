#!/usr/bin/env bash
set -euo pipefail
source .env.local
mkdir -p config/customizations
# example: export Ticket (Helpdesk) and Customer/Asset
./bin/bench.sh --site "$SITE_NAME" export-customizations "Ticket" "Customer" "Asset"
# exported JSONs land in sites/<site>/custom  → copy them into config/customizations manually
echo "Copy JSONs from sites/$SITE_NAME/custom to config/customizations and commit."
