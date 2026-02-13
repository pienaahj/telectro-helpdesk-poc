#!/usr/bin/env bash
set -euo pipefail
source .env.local
# bare-bones data import using built-in importer is easier via UI,
# but here's an example using bench execute for quick seeds if you want:
./bin/bench.sh --site "$SITE_NAME" execute frappe.core.doctype.data_import.data_import.import_file --kwargs "{'doctype':'Customer','file_path':'/home/frappe/frappe-bench/sites/$SITE_NAME/private/files/customers.csv','submit_after_import':0,'mute_emails':1}"
