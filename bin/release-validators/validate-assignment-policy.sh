#!/usr/bin/env bash

set -euo pipefail

cd /home/frappe/frappe-bench

./env/bin/python <<'PY'
import inspect
import json
import sys
import unittest

from pathlib import Path
from unittest import mock

import frappe

from telephony import assignment_policy
from telephony.ftelephony.doctype.telectro_assignment_policy import (
    telectro_assignment_policy as policy_controller,
)
from telephony.tests.test_telectro_round_robin import (
    TestContextualAssignmentPolicyAfterInsert,
)
from telephony.tests.test_telectro_reassign_on_update import (
    TestAssignmentPolicyRoutingTransitions,
)


def require(condition, message):
    if not condition:
        raise SystemExit(
            "ASSIGNMENT_POLICY_VALIDATION_ERROR: "
            + message
        )


print("=== Assignment Policy DocType contract ===")

doctype_path = Path(
    "apps/telephony/telephony/ftelephony/doctype/"
    "telectro_assignment_policy/"
    "telectro_assignment_policy.json"
)

require(
    doctype_path.is_file(),
    "Assignment Policy DocType JSON is missing",
)

doctype = json.loads(
    doctype_path.read_text(encoding="utf-8")
)

require(
    doctype.get("name") == "TELECTRO Assignment Policy",
    "Unexpected Assignment Policy DocType identity",
)

require(
    doctype.get("module") == "FTelephony",
    "Unexpected Assignment Policy module",
)

require(
    doctype.get("istable") == 0,
    "Assignment Policy must be a standalone DocType",
)

fields = {
    row["fieldname"]: row
    for row in doctype["fields"]
}

require(
    len(fields) == len(doctype["fields"]),
    "Duplicate Assignment Policy fieldnames",
)

expected_fields = {
    "coverage_scope": {
        "fieldtype": "Select",
        "reqd": 1,
        "options": (
            "Customer/Campus\nCustomer\nCampus\nDefault"
        ),
    },
    "customer": {
        "fieldtype": "Link",
        "options": "Customer",
    },
    "campus": {
        "fieldtype": "Link",
        "options": "Location",
    },
    "service_area": {
        "fieldtype": "Data",
        "reqd": 1,
    },
    "assignment_mode": {
        "fieldtype": "Select",
        "reqd": 1,
        "options": "Round Robin\nTrue Pool",
    },
    "enabled": {
        "fieldtype": "Check",
        "default": "1",
    },
}

for fieldname, expected in expected_fields.items():
    require(
        fieldname in fields,
        f"Missing Assignment Policy field: {fieldname}",
    )

    for property_name, expected_value in expected.items():
        actual = fields[fieldname].get(property_name)

        require(
            actual == expected_value,
            (
                f"Invalid {fieldname}.{property_name}: "
                f"{actual!r}; expected {expected_value!r}"
            ),
        )

require(
    assignment_policy.POLICY_DOCTYPE
    == "TELECTRO Assignment Policy",
    "Resolver references an unexpected DocType",
)

require(
    assignment_policy.ROUND_ROBIN == "Round Robin",
    "Incorrect Round Robin mode constant",
)

require(
    assignment_policy.TRUE_POOL == "True Pool",
    "Incorrect True Pool mode constant",
)

require(
    policy_controller.VALID_SCOPES
    == {
        "Customer/Campus",
        "Customer",
        "Campus",
        "Default",
    },
    "Controller scope contract differs from DocType",
)

require(
    policy_controller.VALID_ASSIGNMENT_MODES
    == {"Round Robin", "True Pool"},
    "Controller assignment modes differ from DocType",
)

print("ASSIGNMENT_POLICY_DOCTYPE_CONTRACT=PASS")


print()
print("=== Customer-specific regression scenarios ===")

emerald_source = inspect.getsource(
    TestContextualAssignmentPolicyAfterInsert
    .test_emerald_life_cctv_true_pool_suppresses_automatic_assignment
)

boschendal_source = inspect.getsource(
    TestContextualAssignmentPolicyAfterInsert
    .test_boschendal_cctv_round_robin_assigns_covered_team_member
)

transition_source = inspect.getsource(
    TestAssignmentPolicyRoutingTransitions
    .test_leaving_true_pool_enters_contextual_round_robin
)

require(
    'custom_customer="Emerald Life"' in emerald_source,
    "Emerald Life True Pool test has incorrect Customer",
)

require(
    '"coverage_scope": "Customer"' in emerald_source,
    "Emerald Life True Pool test has incorrect scope",
)

require(
    '"assignment_mode": "True Pool"' in emerald_source,
    "Emerald Life test does not specify True Pool",
)

require(
    'custom_customer="Boschendal"' in boschendal_source,
    "Boschendal after-insert test has incorrect Customer",
)

require(
    'custom_site_group="Boschendal"' in boschendal_source,
    "Boschendal after-insert test has incorrect Campus",
)

require(
    '"coverage_scope": "Customer/Campus"'
    in boschendal_source,
    "Boschendal after-insert test has incorrect scope",
)

require(
    '"assignment_mode": "Round Robin"'
    in boschendal_source,
    "Boschendal test does not specify Round Robin",
)

require(
    'custom_customer="Emerald Life"' in transition_source,
    "True Pool transition has incorrect source Customer",
)

require(
    'custom_customer="Boschendal"' in transition_source,
    "True Pool transition has incorrect destination Customer",
)

require(
    'custom_site_group="Boschendal"' in transition_source,
    "True Pool transition has incorrect destination Campus",
)

require(
    "Customer B" not in boschendal_source
    and "Customer B" not in transition_source,
    "Obsolete test Customer identity remains",
)

print("ASSIGNMENT_POLICY_CUSTOMER_SCENARIOS=PASS")


print()
print("=== Assignment Policy focused runtime regressions ===")

test_targets = [
    "telephony.tests.test_assignment_policy",
    "telephony.tests.test_assignment_policy_controller",
    (
        "telephony.tests.test_telectro_round_robin."
        "TestContextualAssignmentPolicyAfterInsert"
    ),
    (
        "telephony.tests.test_telectro_reassign_on_update."
        "TestAssignmentPolicyRoutingTransitions"
    ),
    "telephony.tests.test_partner_creator_admin_guard",
    (
        "telephony.tests.test_telectro_round_robin."
        "TestPartnerFulfilmentAfterInsert"
    ),
    (
        "telephony.tests.test_telectro_reassign_on_update."
        "TestPartnerFulfilmentReassignment"
    ),
    (
        "telephony.tests.test_telectro_reassign_on_update."
        "TestDirectOwnerReassignment"
    ),
]

loader = unittest.TestLoader()

suite = loader.loadTestsFromNames(test_targets)

expected_test_count = 35

require(
    suite.countTestCases() == expected_test_count,
    (
        "Unexpected focused regression-test count: "
        f"{suite.countTestCases()}; "
        f"expected {expected_test_count}"
    ),
)

# The Phase 5 candidate container has no production database.
# Supply a mock Frappe database so these isolated tests can
# execute without accessing a site or performing database writes.
with mock.patch.object(
    frappe,
    "db",
    new=mock.Mock(),
    create=True,
):
    result = unittest.TextTestRunner(
        stream=sys.stdout,
        verbosity=1,
    ).run(suite)

require(
    result.wasSuccessful(),
    "Assignment Policy focused regressions failed",
)

require(
    result.testsRun == expected_test_count,
    "Not all focused Assignment Policy tests executed",
)

print(
    "ASSIGNMENT_POLICY_REGRESSION_TEST_COUNT="
    f"{result.testsRun}"
)

print("ASSIGNMENT_POLICY_REGRESSIONS=PASS")


print()
print("ASSIGNMENT_POLICY_SEMANTIC_VALIDATION=PASS")
PY
