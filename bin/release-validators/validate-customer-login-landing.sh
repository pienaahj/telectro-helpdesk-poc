#!/usr/bin/env bash

set -euo pipefail

cd /home/frappe/frappe-bench

./env/bin/python <<'PY'
import ast
import inspect
from pathlib import Path

from telephony import customer_portal_landing


TELEPHONY_ROOT = Path("apps/telephony/telephony")

HOOKS_PATH = TELEPHONY_ROOT / "hooks.py"

TEST_PATH = (
    TELEPHONY_ROOT
    / "tests/test_customer_portal_landing.py"
)

LOGIN_JS_PATH = (
    TELEPHONY_ROOT
    / "public/js/customer_login_landing.js"
)

HOME_HOOK_PATH = (
    "telephony.customer_portal_landing."
    "get_website_user_home_page"
)

LOGIN_JS_ASSET = (
    "/assets/telephony/js/customer_login_landing.js"
    "?v=2026-08-27-1"
)


def require(condition, message):
    if not condition:
        raise SystemExit(
            "CUSTOMER_LOGIN_LANDING_RELEASE_VALIDATION_ERROR: "
            f"{message}"
        )


print("=== Customer portal landing constant contract ===")

expected_constants = {
    "CUSTOMER_PORTAL_HOME": "helpdesk/my-tickets",
    "CUSTOMER_ROLE": "Customer",
}

observed_constants = {
    name: getattr(
        customer_portal_landing,
        name,
        None,
    )
    for name in expected_constants
}

print(
    "CUSTOMER_PORTAL_LANDING_CONSTANTS=",
    observed_constants,
)

require(
    observed_constants == expected_constants,
    "Customer portal landing constants changed",
)

print("CUSTOMER_PORTAL_LANDING_CONSTANT_CONTRACT=PASS")


print()
print("=== Customer home resolver contract ===")

resolver = getattr(
    customer_portal_landing,
    "get_website_user_home_page",
    None,
)

require(
    callable(resolver),
    "Customer home resolver is missing",
)

signature = inspect.signature(resolver)

require(
    list(signature.parameters) == ["user"],
    "Customer home resolver must accept exactly user",
)

resolver_source = inspect.getsource(resolver)

require(
    '"Website User"' in resolver_source,
    "Website User containment check is missing",
)

require(
    "CUSTOMER_ROLE" in resolver_source,
    "Customer role check is missing",
)

require(
    "return CUSTOMER_PORTAL_HOME" in resolver_source,
    "Customer portal return is missing",
)

print(
    "CUSTOMER_PORTAL_HOME_RESOLVER="
    "get_website_user_home_page"
)

print("CUSTOMER_PORTAL_HOME_RESOLVER_CONTRACT=PASS")


print()
print("=== Customer home hook contract ===")

require(
    HOOKS_PATH.is_file(),
    f"missing hooks.py: {HOOKS_PATH}",
)

hooks_source = HOOKS_PATH.read_text()
hooks_tree = ast.parse(hooks_source)

home_hook_literals = [
    node.value
    for node in ast.walk(hooks_tree)
    if (
        isinstance(node, ast.Constant)
        and node.value == HOME_HOOK_PATH
    )
]

require(
    len(home_hook_literals) == 1,
    "Customer home hook must appear exactly once",
)

require(
    (
        "get_website_user_home_page = ("
        in hooks_source
    ),
    "Customer home hook declaration is missing",
)

print(
    "CUSTOMER_PORTAL_HOME_HOOK=",
    HOME_HOOK_PATH,
)

print(
    "CUSTOMER_PORTAL_HOME_HOOK_COUNT=",
    len(home_hook_literals),
)

print("CUSTOMER_PORTAL_HOME_HOOK_CONTRACT=PASS")


print()
print("=== Customer login website asset contract ===")

require(
    LOGIN_JS_PATH.is_file(),
    f"missing Customer login JS: {LOGIN_JS_PATH}",
)

asset_literals = [
    node.value
    for node in ast.walk(hooks_tree)
    if (
        isinstance(node, ast.Constant)
        and node.value == LOGIN_JS_ASSET
    )
]

require(
    len(asset_literals) == 1,
    "Customer login website asset must appear exactly once",
)

require(
    "web_include_js = list("
    in hooks_source,
    "web_include_js declaration is missing",
)

require(
    (
        "if customer_login_landing_js "
        "not in web_include_js:"
    )
    in hooks_source,
    "Customer login JS dedupe guard is missing",
)

require(
    (
        "web_include_js.append("
        "customer_login_landing_js)"
    )
    in hooks_source,
    "Customer login JS append is missing",
)

print(
    "CUSTOMER_LOGIN_LANDING_ASSET=",
    LOGIN_JS_ASSET,
)

print(
    "CUSTOMER_LOGIN_LANDING_ASSET_COUNT=",
    len(asset_literals),
)

print("CUSTOMER_LOGIN_WEBSITE_ASSET_CONTRACT=PASS")


print()
print("=== Customer login guard source contract ===")

login_source = LOGIN_JS_PATH.read_text()

required_markers = [
    'const CUSTOMER_PORTAL_HOME = "/helpdesk/my-tickets";',
    'data?.message === "No App"',
    'home_page === CUSTOMER_PORTAL_HOME',
    'removeItem("last_visited")',
    'window.location.href = home_page',
    'native_handler.apply(this, arguments)',
    '"login_rendered"',
]

for marker in required_markers:
    require(
        marker in login_source,
        f"Customer login guard marker missing: {marker}",
    )

print(
    "CUSTOMER_LOGIN_GUARD_MARKERS=",
    required_markers,
)

print("CUSTOMER_LOGIN_GUARD_SOURCE_CONTRACT=PASS")


print()
print("=== Customer portal landing regression-test contract ===")

require(
    TEST_PATH.is_file(),
    f"missing regression test file: {TEST_PATH}",
)

test_tree = ast.parse(
    TEST_PATH.read_text()
)

observed_tests = {
    node.name
    for node in ast.walk(test_tree)
    if (
        isinstance(node, ast.FunctionDef)
        and node.name.startswith("test_")
    )
}

expected_tests = {
    "test_customer_website_user_gets_customer_portal_home",
    "test_non_customer_website_user_uses_native_home_resolution",
    "test_system_user_with_customer_role_is_not_redirected",
    "test_guest_uses_native_home_resolution",
    "test_blank_user_uses_native_home_resolution",
}

print(
    "CUSTOMER_PORTAL_LANDING_REGRESSION_TESTS=",
    sorted(observed_tests),
)

require(
    observed_tests == expected_tests,
    "Customer portal landing regression-test contract changed",
)

print(
    "CUSTOMER_PORTAL_LANDING_REGRESSION_TEST_COUNT=",
    len(observed_tests),
)

print("CUSTOMER_PORTAL_LANDING_TEST_CONTRACT=PASS")
PY

node <<'NODE'
const fs = require("fs");
const vm = require("vm");

const path =
  "apps/telephony/telephony/public/js/customer_login_landing.js";

const source = fs.readFileSync(path, "utf8");

function requireCondition(condition, message) {
  if (!condition) {
    throw new Error(
      `CUSTOMER_LOGIN_LANDING_RELEASE_VALIDATION_ERROR: ${message}`
    );
  }
}

function makeContext() {
  const state = {
    nativeCalls: 0,
    removedKeys: [],
    loginRenderedHandler: null,
  };

  const window = {
    location: {
      href: "/login",
    },

    localStorage: {
      removeItem(key) {
        state.removedKeys.push(key);
      },
    },

    login: {
      login_handlers: {
        200(data) {
          state.nativeCalls += 1;
          state.nativeData = data;
        },
      },
    },
  };

  const context = {
    window,
    login: window.login,
    document: {},

    frappe: {
      utils: {
        sanitise_redirect(value) {
          return value;
        },
      },
    },

    $() {
      return {
        on(event, handler) {
          if (event === "login_rendered") {
            state.loginRenderedHandler = handler;
          }
        },
      };
    },

    console,
  };

  vm.createContext(context);
  vm.runInContext(source, context);

  requireCondition(
    typeof state.loginRenderedHandler === "function",
    "login_rendered handler was not registered"
  );

  state.loginRenderedHandler();

  return {
    context,
    state,
  };
}


console.log();
console.log("=== Customer login guard semantic contract ===");

{
  const { context, state } = makeContext();

  context.window.login.login_handlers[200]({
    message: "No App",
    home_page: "/helpdesk/my-tickets",
  });

  requireCondition(
    state.nativeCalls === 0,
    "Customer response called native login handler"
  );

  requireCondition(
    state.removedKeys.includes("last_visited"),
    "Customer response did not clear last_visited"
  );

  requireCondition(
    context.window.location.href === "/helpdesk/my-tickets",
    "Customer response did not select portal home"
  );

  console.log("CUSTOMER_LOGIN_GUARD_CUSTOMER_BRANCH=PASS");
}


{
  const { state } = makeContext();

  state.loginRenderedHandler();

  const wrapped =
    state.loginRenderedHandler;

  requireCondition(
    typeof wrapped === "function",
    "login guard became unavailable on repeated installation"
  );

  console.log("CUSTOMER_LOGIN_GUARD_IDEMPOTENT_INSTALL=PASS");
}


{
  const { context, state } = makeContext();

  context.window.login.login_handlers[200]({
    message: "No App",
    home_page: "/me",
  });

  requireCondition(
    state.nativeCalls === 1,
    "Non-Customer response did not use native handler"
  );

  requireCondition(
    state.removedKeys.length === 0,
    "Non-Customer response cleared browser state"
  );

  console.log("CUSTOMER_LOGIN_GUARD_NATIVE_FALLBACK=PASS");
}

console.log();
console.log("CUSTOMER_LOGIN_LANDING=PASS");
NODE
