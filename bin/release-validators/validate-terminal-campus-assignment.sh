#!/usr/bin/env bash

set -euo pipefail

cd /home/frappe/frappe-bench

./env/bin/python <<'PY'
from types import SimpleNamespace
from unittest.mock import patch

from telephony import telectro_assign_sync as assign_sync
from telephony import telectro_site_guard as site_guard


class TicketDoc(dict):
    __getattr__ = dict.get


class AttrDict(dict):
    __getattr__ = dict.get


class QuietLogger:
    def info(self, *args, **kwargs):
        pass


class AssignFrappeStub:
    def logger(self, *args, **kwargs):
        return QuietLogger()

    def throw(self, message):
        raise RuntimeError(message)


def require(condition, message):
    if not condition:
        raise SystemExit(
            "TERMINAL_CAMPUS_ASSIGNMENT_RELEASE_VALIDATION_ERROR: "
            f"{message}"
        )


print("=== Canonical terminal Campus contract ===")

terminal_doc = TicketDoc(
    name="VALIDATE-TERMINAL-CAMPUS",
    ticket_type="Faults",
    custom_fault_category="",
    custom_fault_asset="",
    custom_site_group="EL-SITE-001",
    custom_site="",
    custom_request_source="Customer",
    raised_by="",
)

terminal_row = AttrDict(
    {
        "is_group": 1,
        "parent_location": "Pilot Sites",
        "custom_customer_visibility": "Customer-safe",
        "custom_ticket_selectability": "Selectable",
    }
)

site_frappe_terminal = SimpleNamespace(
    db=SimpleNamespace(
        get_value=lambda *args, **kwargs: terminal_row
    )
)

with patch.object(
    site_guard,
    "frappe",
    site_frappe_terminal,
):
    require(
        site_guard._is_ticket_selectable_terminal_campus(
            terminal_doc
        )
        is True,
        (
            "canonical site guard did not recognize "
            "a valid terminal Campus"
        ),
    )

print("TERMINAL_CAMPUS_SITE_GUARD=PASS")


print()
print("=== Non-terminal Campus contract ===")

non_terminal_doc = TicketDoc(
    name="VALIDATE-NON-TERMINAL-GROUP",
    ticket_type="Faults",
    custom_fault_category="",
    custom_fault_asset="",
    custom_site_group="Boschendal",
    custom_site="",
    custom_request_source="Customer",
    raised_by="",
)

non_terminal_row = AttrDict(
    {
        "is_group": 1,
        "parent_location": "Pilot Sites",
        "custom_customer_visibility": None,
        "custom_ticket_selectability": None,
    }
)

site_frappe_non_terminal = SimpleNamespace(
    db=SimpleNamespace(
        get_value=lambda *args, **kwargs: non_terminal_row
    )
)

with patch.object(
    site_guard,
    "frappe",
    site_frappe_non_terminal,
):
    require(
        site_guard._is_ticket_selectable_terminal_campus(
            non_terminal_doc
        )
        is False,
        (
            "canonical site guard incorrectly recognized "
            "a non-terminal group"
        ),
    )

print("NON_TERMINAL_SITE_GUARD=PASS")


print()
print("=== Assignment validator integration ===")

require(
    assign_sync._is_ticket_selectable_terminal_campus
    is site_guard._is_ticket_selectable_terminal_campus,
    (
        "assignment validator is not using the canonical "
        "terminal-Campus helper"
    ),
)

assign_frappe = AssignFrappeStub()

with (
    patch.object(
        assign_sync,
        "frappe",
        assign_frappe,
    ),
    patch.object(
        assign_sync,
        "_is_ticket_selectable_terminal_campus",
        return_value=True,
    ) as terminal_helper,
):
    assign_sync._validate_site_group_and_leaf(
        terminal_doc
    )

    terminal_helper.assert_called_once_with(
        terminal_doc
    )

print(
    "TERMINAL_CAMPUS_WITHOUT_SITE_LEAF=PASS"
)


error = None

with (
    patch.object(
        assign_sync,
        "frappe",
        assign_frappe,
    ),
    patch.object(
        assign_sync,
        "_is_ticket_selectable_terminal_campus",
        return_value=False,
    ) as non_terminal_helper,
):
    try:
        assign_sync._validate_site_group_and_leaf(
            non_terminal_doc
        )
    except RuntimeError as exc:
        error = exc

    non_terminal_helper.assert_called_once_with(
        non_terminal_doc
    )

require(
    error is not None,
    (
        "non-terminal group unexpectedly accepted "
        "without Site Location"
    ),
)

require(
    "Please select a Site Location" in str(error),
    (
        "non-terminal group failed with unexpected "
        f"validation message: {error}"
    ),
)

print(
    "NON_TERMINAL_GROUP_SITE_LEAF_REQUIREMENT=PASS"
)

print()
print(
    "TERMINAL_CAMPUS_ASSIGNMENT_VALIDATION=PASS"
)
PY
