#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

GUARD_FILE="${APP_ROOT}/public/js/partner_route_guard.js"
HOOKS_FILE="${APP_ROOT}/hooks.py"
NODE_BIN="${NODE_BIN:-$(command -v node || true)}"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

[[ -f "$GUARD_FILE" ]] ||
  fail "missing Partner route guard: $GUARD_FILE"

[[ -f "$HOOKS_FILE" ]] ||
  fail "missing hooks file: $HOOKS_FILE"

[[ -n "$NODE_BIN" && -x "$NODE_BIN" ]] ||
  fail "node is required for Partner route guard regression tests"

"$NODE_BIN" --check "$GUARD_FILE"

"$NODE_BIN" - "$GUARD_FILE" <<'JS'
const fs = require("fs");
const vm = require("vm");

const guardPath = process.argv[2];
const source = fs.readFileSync(guardPath, "utf8");

const PARTNER_ROLES = [
  "TELECTRO-POC Role - Partner",
  "TELECTRO-POC Role - Partner Creator",
];

const failures = [];

function fail(message) {
  failures.push(message);
}

function runGuard({
  pathname,
  roles = PARTNER_ROLES,
  user = "pilot.partner@telectro.co.za",
  currentRoute = [],
}) {
  const routeCalls = [];
  const alerts = [];

  const frappe = {
    user_roles: roles,
    session: {
      user,
    },
    boot: {},
    router: {
      current_route: currentRoute,
    },
    set_route(...args) {
      routeCalls.push(args);
    },
    show_alert(value) {
      alerts.push(value);
    },
  };

  const window = {
    frappe,
    location: {
      pathname,
      hash: "",
      href: pathname,
    },
    setTimeout() {},
    setInterval() {},
  };

  const document = {
    readyState: "complete",
    body: {},
    addEventListener() {},
    querySelectorAll() {
      return [];
    },
  };

  class MutationObserver {
    observe() {}
  }

  const context = {
    window,
    document,
    frappe,
    MutationObserver,
    __: (value) => value,
    console,
  };

  vm.runInNewContext(
    source,
    context,
    {
      filename: guardPath,
    },
  );

  return {
    routeCalls,
    alerts,
    href: window.location.href,
  };
}

function expectRoute(pathname, expectedRoute) {
  const result = runGuard({ pathname });

  const actual = JSON.stringify(result.routeCalls);
  const expected = JSON.stringify([expectedRoute]);

  if (actual !== expected) {
    fail(
      `${pathname}: expected route ${expected}, received ${actual}`,
    );
  }
}

function expectNoRoute(pathname, options = {}) {
  const result = runGuard({
    pathname,
    ...options,
  });

  if (result.routeCalls.length !== 0) {
    fail(
      `${pathname}: expected no redirect, received ` +
        JSON.stringify(result.routeCalls),
    );
  }
}

/*
 * Raw/internal HD Ticket surfaces must never remain available
 * to a Partner user.
 */
expectRoute(
  "/app/hd-ticket",
  ["telectro-poc-partner"],
);

expectRoute(
  "/app/hd-ticket/view/list",
  ["telectro-poc-partner"],
);

expectRoute(
  "/app/hd-ticket/new-hd-ticket-regression",
  ["telectro-poc-partner"],
);

/*
 * A specific HD Ticket URL remains useful because notifications
 * and internal links may contain it. Partner users must be sent
 * to the Partner-safe ticket page instead of the raw form.
 */
expectRoute(
  "/app/hd-ticket/12",
  ["partner-ticket", "12"],
);

/*
 * Route-control prefixes must not accidentally contain ordinary
 * HD Ticket names that merely begin with the same characters.
 */
expectRoute(
  "/app/hd-ticket/view123",
  ["partner-ticket", "view123"],
);

expectRoute(
  "/app/hd-ticket/new-hd-ticketed",
  ["partner-ticket", "new-hd-ticketed"],
);

/*
 * Approved Partner surfaces must remain available.
 */
expectNoRoute("/app/partner-request");

expectNoRoute("/app/partner-ticket/12");

/*
 * Internal bypass users must not be constrained by the Partner
 * route guard even if they also hold a Partner capability role.
 */
expectNoRoute(
  "/app/hd-ticket",
  {
    roles: [
      "TELECTRO-POC Role - Partner",
      "System Manager",
    ],
    user: "internal.test@example.com",
  },
);

if (failures.length) {
  for (const failure of failures) {
    console.error(`FAIL: ${failure}`);
  }

  process.exit(1);
}

console.log("PARTNER_ROUTE_GUARD_BEHAVIOUR=PASS");
JS

grep -Fq \
  '/assets/telephony/js/partner_route_guard.js?v=2026-08-24-1' \
  "$HOOKS_FILE" ||
  fail "Partner route guard asset cache version was not advanced"

printf '%s\n' \
  'PARTNER_ROUTE_GUARD_ASSET_VERSION=PASS' \
  'PARTNER_ROUTE_GUARD_REGRESSION=PASS'
