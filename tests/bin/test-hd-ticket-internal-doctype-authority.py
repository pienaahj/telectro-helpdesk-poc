#!/usr/bin/env python3
"""Standalone policy test; mocks Frappe, no DB or running services required."""
import importlib.util
import sys
import types
from pathlib import Path

assert len(sys.argv) == 2, "Provide the realtime_ticket_authorization.py path"
path = Path(sys.argv[1])
state = {
    "user": "ops.test@local.test", "enabled": True,
    "user_type": "System User", "roles": ["TELECTRO-POC Role - Tech"],
    "read": True,
}

class PermissionError_(Exception):
    pass

frappe = types.ModuleType("frappe")
frappe.PermissionError = PermissionError_
frappe.session = types.SimpleNamespace()
frappe.whitelist = lambda: (lambda func: func)

class DB:
    def get_value(self, doctype, user, fields, as_dict=False):
        assert doctype == "User" and fields == ["enabled", "user_type"] and as_dict
        assert user == state["user"]
        if state.get("missing_account"):
            return None
        return types.SimpleNamespace(
            enabled=state["enabled"], user_type=state["user_type"]
        )

frappe.db = DB()
frappe.get_roles = lambda user: state["roles"] if user == state["user"] else []
def permission(doctype, ptype):
    assert (doctype, ptype) == ("HD Ticket", "read")
    return state["read"]
frappe.has_permission = permission
sys.modules["frappe"] = frappe
telephony = types.ModuleType("telephony")
telephony.__path__ = []
privacy = types.ModuleType("telephony.customer_communication_privacy")
privacy.get_current_actor_access = lambda name: {
    "actor_kind": "internal", "ticket_read_allowed": True
}
sys.modules["telephony"] = telephony
sys.modules["telephony.customer_communication_privacy"] = privacy

spec = importlib.util.spec_from_file_location("tested_realtime_ticket_authorization", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

cases = [
    ("Ops Tech allowed", {}, True),
    ("Coordinator Ops allowed", {"roles": ["TELECTRO-POC Role - Coordinator Ops"]}, True),
    ("Supervisor Governance allowed", {"roles": ["TELECTRO-POC Role - Supervisor Governance"]}, True),
    ("Partner System User denied despite general read", {"roles": ["TELECTRO-POC Role - Partner"]}, False),
    ("Partner Creator denied", {"roles": ["TELECTRO-POC Role - Partner Creator"]}, False),
    ("Partner plus Tech is still denied", {"roles": ["TELECTRO-POC Role - Partner", "TELECTRO-POC Role - Tech"]}, False),
    ("Partner Creator plus Coordinator is still denied", {"roles": ["TELECTRO-POC Role - Partner Creator", "TELECTRO-POC Role - Coordinator Ops"]}, False),
    ("Generic System Manager not accepted", {"roles": ["System Manager"]}, False),
    ("Website User with Tech role denied", {"user_type": "Website User"}, False),
    ("Disabled internal account denied", {"enabled": False}, False),
    ("Removed account denied", {"missing_account": True}, False),
    ("Missing roles denied", {"roles": []}, False),
    ("Null roles denied", {"roles": None}, False),
    ("Revoked HD Ticket read denied", {"read": False}, False),
    ("Guest denied", {"user": "Guest"}, False),
    ("No principal denied", {"user": None}, False),
]

for idx, (label, changes, expected) in enumerate(cases, 1):
    state.clear()
    state.update({"user": "ops.test@local.test", "enabled": True,
        "user_type": "System User", "roles": ["TELECTRO-POC Role - Tech"],
        "read": True})
    state.update(changes)
    frappe.session.user = state["user"]
    try:
        result = module.require_internal_hd_ticket_doctype_realtime_access()
    except PermissionError_:
        allowed = False
    else:
        assert result is True
        allowed = True
    assert allowed is expected, f"{label}: expected {expected}, got {allowed}"
    print(f"PASS {idx:02} {label}")

# Verify the separate existing ticket policy still allows internal ticket access.
state.update(user="ops.test@local.test")
frappe.session.user = state["user"]
assert module.require_ticket_realtime_access("941", "native_doc") is True
print("C3_245_EXISTING_TICKET_POLICY=PASS")
print(f"C3_245_PYTHON_DOCTYPE_AUTHORITY_TESTS={len(cases)}/{len(cases)} PASS")
