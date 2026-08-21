#!/usr/bin/env bash

set -euo pipefail

cd /home/frappe/frappe-bench

./env/bin/python <<'PY'
import inspect
import json
from pathlib import Path

from telephony import partner_identity
from telephony import permissions
from telephony import telectro_assign_sync as assign_sync
from telephony import telectro_reassign_on_update as reassign
from telephony import telectro_round_robin as round_robin


TELEPHONY_ROOT = Path("apps/telephony/telephony")
REPORT_ROOT = TELEPHONY_ROOT / "ftelephony/report"


def require(condition, message):
    if not condition:
        raise SystemExit(
            f"PARTNER_RELEASE_VALIDATION_ERROR: {message}"
        )


def load_json(path):
    return json.loads(path.read_text())


def field_map(doc):
    return {
        row["fieldname"]: row
        for row in doc.get("fields", [])
    }


def assert_values(row, expected, context):
    for key, expected_value in expected.items():
        observed = row.get(key)

        require(
            observed == expected_value,
            (
                f"{context}: {key} expected "
                f"{expected_value!r}, observed {observed!r}"
            ),
        )


print("=== Partner capability-role contract ===")

expected_partner_roles = {
    "TELECTRO-POC Role - Partner",
    "TELECTRO-POC Role - Partner Creator",
}

observed_identity_roles = set(
    partner_identity.PARTNER_ROLES
)
observed_permission_roles = set(
    permissions.PARTNER_ROLES
)

print(
    "PARTNER_IDENTITY_ROLES=",
    sorted(observed_identity_roles),
)
print(
    "PARTNER_PERMISSION_ROLES=",
    sorted(observed_permission_roles),
)

require(
    observed_identity_roles == expected_partner_roles,
    "partner_identity PARTNER_ROLES changed",
)

require(
    observed_permission_roles == expected_partner_roles,
    "permissions PARTNER_ROLES changed",
)

print("PARTNER_ROLE_CONTRACT=PASS")


print()
print("=== Partner DocType contract ===")

partner_path = (
    TELEPHONY_ROOT
    / "ftelephony/doctype/telectro_partner/"
      "telectro_partner.json"
)

member_path = (
    TELEPHONY_ROOT
    / "ftelephony/doctype/telectro_partner_member/"
      "telectro_partner_member.json"
)

partner = load_json(partner_path)
member = load_json(member_path)

require(
    partner.get("name") == "TELECTRO Partner",
    "unexpected Partner DocType name",
)
require(
    partner.get("istable") == 0,
    "TELECTRO Partner must be a parent DocType",
)
require(
    partner.get("autoname") == "field:partner_name",
    "TELECTRO Partner autoname changed",
)
require(
    partner.get("field_order") == [
        "partner_name",
        "enabled",
        "default_dispatch_user",
        "members",
        "notes",
    ],
    "TELECTRO Partner field order changed",
)

partner_fields = field_map(partner)

assert_values(
    partner_fields["partner_name"],
    {
        "fieldtype": "Data",
        "reqd": 1,
        "unique": 1,
    },
    "TELECTRO Partner.partner_name",
)

assert_values(
    partner_fields["enabled"],
    {
        "fieldtype": "Check",
        "default": "1",
    },
    "TELECTRO Partner.enabled",
)

assert_values(
    partner_fields["default_dispatch_user"],
    {
        "fieldtype": "Link",
        "options": "User",
    },
    "TELECTRO Partner.default_dispatch_user",
)

assert_values(
    partner_fields["members"],
    {
        "fieldtype": "Table",
        "options": "TELECTRO Partner Member",
    },
    "TELECTRO Partner.members",
)

permission_roles = {
    row.get("role")
    for row in partner.get("permissions", [])
}

require(
    permission_roles == {
        "System Manager",
        "Pilot Admin",
        "TELECTRO-POC Role - Supervisor Governance",
        "TELECTRO-POC Role - Coordinator Ops",
    },
    "TELECTRO Partner permission-role set changed",
)

require(
    member.get("name") == "TELECTRO Partner Member",
    "unexpected Partner Member DocType name",
)
require(
    member.get("istable") == 1,
    "TELECTRO Partner Member must be a child table",
)
require(
    member.get("field_order") == [
        "user",
        "enabled",
    ],
    "TELECTRO Partner Member field order changed",
)

member_fields = field_map(member)

assert_values(
    member_fields["user"],
    {
        "fieldtype": "Link",
        "options": "User",
        "reqd": 1,
    },
    "TELECTRO Partner Member.user",
)

assert_values(
    member_fields["enabled"],
    {
        "fieldtype": "Check",
        "default": "1",
    },
    "TELECTRO Partner Member.enabled",
)

print("PARTNER_DOCTYPE_CONTRACT=PASS")


print()
print("=== Partner custom-field fixture contract ===")

custom_field_path = (
    TELEPHONY_ROOT / "fixtures/custom_field.json"
)

custom_fields = load_json(custom_field_path)

custom_field_names = [
    row.get("name")
    for row in custom_fields
]

require(
    len(custom_field_names)
    == len(set(custom_field_names)),
    "duplicate Custom Field fixture identities detected",
)

custom_field_by_name = {
    row["name"]: row
    for row in custom_fields
}

request_partner = custom_field_by_name.get(
    "HD Ticket-custom_request_partner"
)
fulfilment_partner = custom_field_by_name.get(
    "HD Ticket-custom_fulfilment_partner"
)
severity = custom_field_by_name.get(
    "HD Ticket-custom_severity"
)

require(
    request_partner is not None,
    "Request Partner custom field missing",
)
require(
    fulfilment_partner is not None,
    "Fulfilment Partner custom field missing",
)
require(
    severity is not None,
    "Severity custom field missing",
)

assert_values(
    request_partner,
    {
        "dt": "HD Ticket",
        "fieldname": "custom_request_partner",
        "label": "Request Partner",
        "fieldtype": "Link",
        "options": "TELECTRO Partner",
        "insert_after": "custom_request_source",
        "depends_on":
            'eval:doc.custom_request_source == "Partner"',
    },
    "HD Ticket.custom_request_partner",
)

assert_values(
    fulfilment_partner,
    {
        "dt": "HD Ticket",
        "fieldname": "custom_fulfilment_partner",
        "label": "Fulfilment Partner",
        "fieldtype": "Link",
        "options": "TELECTRO Partner",
        "insert_after": "custom_fulfilment_party",
        "depends_on":
            'eval:doc.custom_fulfilment_party == "Partner"',
    },
    "HD Ticket.custom_fulfilment_partner",
)

require(
    severity.get("insert_after")
    == "custom_fulfilment_partner",
    "Severity field must follow Fulfilment Partner",
)

print(
    "CUSTOM_FIELD_FIXTURE_COUNT=",
    len(custom_fields),
)
print("PARTNER_CUSTOM_FIELD_CONTRACT=PASS")


print()
print("=== Partner report-fixture role contract ===")

report_fixture_path = (
    TELEPHONY_ROOT / "fixtures/report.json"
)

reports = load_json(report_fixture_path)

report_names = [
    row.get("name") or row.get("report_name")
    for row in reports
]

require(
    len(report_names) == len(set(report_names)),
    "duplicate Report fixture identities detected",
)

require(
    len(reports) == 26,
    "unexpected Report fixture count",
)

report_by_name = {
    row.get("name") or row.get("report_name"): row
    for row in reports
}

expected_internal_roles = {
    "Pilot Admin",
    "System Manager",
    "TELECTRO-POC Coordinator Role",
    "TELECTRO-POC Ops Role",
    "TELECTRO-POC Role - Coordinator Ops",
    "TELECTRO-POC Role - Supervisor Governance",
}

for report_name in [
    "New Partner Tickets",
    "Partner Acceptance Rework Queue",
    "Partner Workflow War Room",
]:
    report = report_by_name.get(report_name)

    require(
        report is not None,
        f"Report fixture missing: {report_name}",
    )

    assert_values(
        report,
        {
            "report_type": "Script Report",
            "ref_doctype": "HD Ticket",
            "is_standard": "Yes",
        },
        report_name,
    )

    observed_roles = {
        row.get("role")
        for row in report.get("roles", [])
    }

    require(
        observed_roles == expected_internal_roles,
        f"{report_name} role set changed",
    )

print(
    "REPORT_FIXTURE_COUNT=",
    len(reports),
)
print("PARTNER_REPORT_FIXTURE_ROLE_CONTRACT=PASS")


print()
print("=== Partner identity and containment contract ===")

dispatch_source = inspect.getsource(
    partner_identity.resolve_partner_dispatch_user
)

for token in [
    "TELECTRO Partner",
    "default_dispatch_user",
    "TELECTRO Partner Member",
    "enabled",
    "User",
    "PARTNER_ROLES",
]:
    require(
        token in dispatch_source,
        (
            "resolve_partner_dispatch_user missing "
            f"required semantic token: {token}"
        ),
    )

name_resolution_source = inspect.getsource(
    partner_identity.resolve_partner_name_for_user
)

for token in [
    "get_enabled_partner_names_for_user",
    "requested_partner",
    "allowed_partners",
    "len(partner_names) == 1",
]:
    require(
        token in name_resolution_source,
        (
            "resolve_partner_name_for_user missing "
            f"required semantic token: {token}"
        ),
    )

ticket_partner_source = inspect.getsource(
    partner_identity.get_partner_names_for_ticket
)

for token in [
    "custom_request_source",
    "custom_request_partner",
    "custom_fulfilment_party",
    "custom_fulfilment_partner",
    '"Partner"',
]:
    require(
        token in ticket_partner_source,
        (
            "ticket Partner identity missing "
            f"required semantic token: {token}"
        ),
    )

ticket_membership_source = inspect.getsource(
    partner_identity.user_has_partner_ticket_membership
)

for token in [
    "get_partner_names_for_ticket",
    "get_enabled_partner_names_for_user",
]:
    require(
        token in ticket_membership_source,
        (
            "ticket membership missing "
            f"required semantic token: {token}"
        ),
    )

permission_source = inspect.getsource(
    permissions.get_partner_ticket_report_condition
)

for token in [
    "get_enabled_partner_names_for_user",
    "custom_request_source",
    "custom_request_partner",
    "custom_fulfilment_party",
    "custom_fulfilment_partner",
    '"1 = 0"',
]:
    require(
        token in permission_source,
        (
            "Partner report containment missing "
            f"required semantic token: {token}"
        ),
    )

partner_create_source = (
    TELEPHONY_ROOT / "partner_create.py"
).read_text()

for token in [
    "resolve_partner_name_for_user(",
    "user_has_partner_ticket_membership(",
    "custom_request_partner",
    "custom_fulfilment_partner",
]:
    require(
        token in partner_create_source,
        (
            "Partner workflow source missing "
            f"required semantic token: {token}"
        ),
    )

print("PARTNER_IDENTITY_CONTAINMENT_CONTRACT=PASS")


print()
print("=== Partner dispatch contract ===")

require(
    assign_sync.resolve_partner_dispatch_user
    is partner_identity.resolve_partner_dispatch_user,
    "assignment sync is not bound to Partner dispatch resolver",
)

require(
    reassign.resolve_partner_dispatch_user
    is partner_identity.resolve_partner_dispatch_user,
    "reassignment is not bound to Partner dispatch resolver",
)

require(
    round_robin.resolve_partner_dispatch_user
    is partner_identity.resolve_partner_dispatch_user,
    "round-robin is not bound to Partner dispatch resolver",
)

require(
    "custom_fulfilment_partner"
    in reassign.ROUTING_FIELDS,
    "Fulfilment Partner is not routing relevant",
)

assign_source = inspect.getsource(
    assign_sync._resolve_partner_assignment_user
)

reassign_source = inspect.getsource(
    reassign.reassign_if_routing_changed
)

round_robin_source = inspect.getsource(
    round_robin.assign_after_insert
)

for context, source in [
    ("assignment sync", assign_source),
    ("reassignment", reassign_source),
    ("round-robin", round_robin_source),
]:
    require(
        "resolve_partner_dispatch_user" in source,
        f"{context} does not consume Partner dispatch resolver",
    )

for path in [
    TELEPHONY_ROOT / "telectro_assign_sync.py",
    TELEPHONY_ROOT / "telectro_reassign_on_update.py",
    TELEPHONY_ROOT / "telectro_round_robin.py",
]:
    require(
        "partner@local.test"
        not in path.read_text(),
        f"legacy Partner dispatch identity remains in {path}",
    )

print(
    "PARTNER_ROUTING_FIELDS_HAS_FULFILMENT_PARTNER=YES"
)
print("PARTNER_DISPATCH_CONTRACT=PASS")


print()
print("=== Partner report semantic contract ===")

supervisor_path = (
    REPORT_ROOT
    / "supervisor_team_snapshot/"
      "supervisor_team_snapshot.py"
)

first_response_path = (
    REPORT_ROOT
    / "first_response_missed/"
      "first_response_missed.py"
)

supervisor_source = supervisor_path.read_text()
first_response_source = first_response_path.read_text()

require(
    (
        "COALESCE(h.custom_fulfilment_party, '') "
        "!= 'Partner'"
    )
    in supervisor_source,
    "Supervisor Team Snapshot Partner exclusion changed",
)

require(
    (
        "COALESCE(custom_fulfilment_party, '') "
        "= 'Partner'"
    )
    in first_response_source,
    "First Response Missed Partner bucket changed",
)

legacy_report_hits = []

for path in sorted(REPORT_ROOT.rglob("*.py")):
    if "partner@local.test" in path.read_text():
        legacy_report_hits.append(str(path))

require(
    not legacy_report_hits,
    (
        "legacy Partner identity remains in active reports: "
        + ", ".join(legacy_report_hits)
    ),
)

print(
    "ACTIVE_REPORT_LEGACY_PARTNER_IDENTITY_COUNT=",
    len(legacy_report_hits),
)
print("PARTNER_REPORT_SEMANTICS=PASS")


print()
print("PARTNER_ORGANISATION_RELEASE_VALIDATION=PASS")
PY
