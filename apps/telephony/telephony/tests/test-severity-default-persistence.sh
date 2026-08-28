#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FIXTURE_FILE="${APP_ROOT}/fixtures/client_script.json"
NODE_BIN="${NODE_BIN:-$(command -v node || true)}"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

[[ -f "$FIXTURE_FILE" ]] ||
  fail "missing Client Script fixture: $FIXTURE_FILE"

[[ -n "$NODE_BIN" && -x "$NODE_BIN" ]] ||
  fail "node is required for Severity default persistence regression tests"

"$NODE_BIN" - "$FIXTURE_FILE" <<'JS'
const fs = require("fs");
const vm = require("vm");

const fixturePath = process.argv[2];

const fixture = JSON.parse(
  fs.readFileSync(fixturePath, "utf8"),
);

const clientScript = fixture.find(
  (row) =>
    row.doctype === "Client Script" &&
    row.dt === "HD Ticket" &&
    row.name === "Clear Customer and filter List" &&
    row.enabled === 1,
);

if (!clientScript) {
  console.error(
    "FAIL: missing enabled HD Ticket Client Script " +
      '"Clear Customer and filter List"',
  );
  process.exit(1);
}

let handlers = null;

const frappe = {
  ui: {
    form: {
      on(doctype, registeredHandlers) {
        if (doctype === "HD Ticket") {
          handlers = registeredHandlers;
        }
      },
    },
  },
};

const context = {
  frappe,
  console,
  Promise,
  setTimeout,
  clearTimeout,
};

vm.runInNewContext(
  clientScript.script,
  context,
  {
    filename: "Clear Customer and filter List",
  },
);

if (!handlers || typeof handlers.refresh !== "function") {
  console.error(
    "FAIL: HD Ticket refresh handler was not registered",
  );
  process.exit(1);
}

const failures = [];

function fail(message) {
  failures.push(message);
}

function makeForm({ isNew }) {
  const setValueCalls = [];

  const frm = {
    doc: {
      custom_customer: "Boschendal",
      custom_site_group: "Boschendal",
      custom_fault_category: "Buildings",
      custom_service_area: "Other",
      custom_severity: "",
      custom_site: null,
      custom_fault_asset: null,
    },

    is_new() {
      return isNew;
    },

    set_query() {},

    set_value(fieldname, value) {
      setValueCalls.push({
        fieldname,
        value,
      });

      frm.doc[fieldname] = value;

      return Promise.resolve();
    },

    toggle_display() {},
    toggle_reqd() {},
    toggle_enable() {},
    refresh_field() {},

    layout: {
      refresh_dependency() {},
    },
  };

  return {
    frm,
    setValueCalls,
  };
}

async function run() {
  /*
   * Passive refresh of an existing ticket must not manufacture
   * Severity data or dirty the form.
   */
  const existing = makeForm({
    isNew: false,
  });

  await handlers.refresh(existing.frm);

  console.log(
    "EXISTING_REFRESH_SEVERITY=" +
      JSON.stringify(existing.frm.doc.custom_severity),
  );

  const existingSeverityWrites =
    existing.setValueCalls.filter(
      (call) =>
        call.fieldname === "custom_severity",
    );

  console.log(
    "EXISTING_REFRESH_SEVERITY_WRITES=" +
      existingSeverityWrites.length,
  );

  if (existing.frm.doc.custom_severity !== "") {
    fail(
      "existing ticket refresh must preserve blank Severity",
    );
  }

  if (existingSeverityWrites.length !== 0) {
    fail(
      "existing ticket refresh must not write Severity",
    );
  }

  /*
   * The existing pilot UX default remains valid for a genuinely
   * new ticket that already has a Campus.
   */
  const fresh = makeForm({
    isNew: true,
  });

  await handlers.refresh(fresh.frm);

  console.log(
    "NEW_TICKET_REFRESH_SEVERITY=" +
      JSON.stringify(fresh.frm.doc.custom_severity),
  );

  if (fresh.frm.doc.custom_severity !== "Sev3") {
    fail(
      "new ticket with Campus must retain the Sev3 default",
    );
  }

  if (failures.length) {
    for (const failure of failures) {
      console.error(`FAIL: ${failure}`);
    }

    process.exit(1);
  }

  console.log(
    "SEVERITY_EXISTING_REFRESH_PERSISTENCE=PASS",
  );

  console.log(
    "SEVERITY_NEW_TICKET_DEFAULT=PASS",
  );

  console.log(
    "SEVERITY_DEFAULT_PERSISTENCE_REGRESSION=PASS",
  );
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
JS
