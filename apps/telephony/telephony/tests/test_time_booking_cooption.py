"""No-site proof of the private worker-grant foundation."""

import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

from telephony.time_booking_cooption import (
    BookingCooptionError, DOCTYPE, _active_grant, _active_key,
    _grant_after_authorization, _require_recipient_identity, _revoke_after_authorization,
)
from telephony.time_booking_identity import TechnicianBookingIdentity


USER = "tech@example.com"
TICKET = "HD-001"
IDENTITY = TechnicianBookingIdentity(USER, "EMP-001", "Company A")


class FakeGrant(dict):
    def __init__(self, store, values):
        super().__init__(values)
        self.store = store
        self.name = values.get("name")

    def __setattr__(self, key, value):
        if key in ("store", "name"):
            object.__setattr__(self, key, value)
        else:
            self[key] = value

    def insert(self, **kwargs):
        self.name = f"GRANT-{len(self.store) + 1}"
        self["name"] = self.name
        self.store.append(self)

    def save(self, **kwargs):
        pass


class TestCooptionFoundation(unittest.TestCase):
    def setUp(self):
        self.rows = []
        self.locked = []
        self.db = types.SimpleNamespace(sql=self.sql)
        self.unique_error = type("UniqueValidationError", (Exception,), {})
        self.frappe = types.SimpleNamespace(db=self.db, get_all=self.get_all,
            get_doc=self.get_doc, UniqueValidationError=self.unique_error,
            utils=types.SimpleNamespace(now_datetime=lambda: "2026-11-17 10:00:00"))
        self.module_patch = patch.dict(sys.modules, {"frappe": self.frappe, "frappe.utils": self.frappe.utils})
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)
        self.identity_patch = patch("telephony.time_booking_cooption._require_recipient_identity", return_value=IDENTITY)
        self.identity_patch.start()
        self.addCleanup(self.identity_patch.stop)

    def sql(self, query, value, **kwargs):
        self.locked.append((query, value))
        if "tabHD Ticket" in query:
            return [{"name": value}]
        self.assertIn("FOR UPDATE", query)
        self.assertIn("tabTELECTRO Ticket Worker Grant", query)
        return [dict(row) for row in self.rows if row.get("active_key") == value]

    def get_all(self, doctype, **kwargs):
        self.assertEqual(doctype, DOCTYPE)
        key = kwargs["filters"]["active_key"]
        return [dict(row) for row in self.rows if row.get("active_key") == key]

    def get_doc(self, *args):
        if isinstance(args[0], dict):
            return FakeGrant(self.rows, args[0])
        return next(row for row in self.rows if row.name == args[1])

    def test_ticket_lock_precedes_identity_and_current_grant_read(self):
        events = []
        def sql(query, value, **kwargs):
            events.append("ticket" if "tabHD Ticket" in query else "grant")
            return self.sql(query, value, **kwargs)
        def identity(user):
            events.append("identity")
            return IDENTITY
        with patch.object(self.db, "sql", side_effect=sql), patch(
            "telephony.time_booking_cooption._require_recipient_identity", side_effect=identity
        ):
            _grant_after_authorization(ticket=TICKET, user=USER, issuer="issuer", reason="work")
        self.assertEqual(events, ["ticket", "identity", "grant"])

    def test_concurrent_interleaving_sees_committed_grant_after_ticket_lock(self):
        original_sql = self.db.sql
        first = _grant_after_authorization(ticket=TICKET, user=USER, issuer="issuer", reason="work")
        self.rows.clear()
        def resumed_sql(query, value, **kwargs):
            if "tabHD Ticket" in query:
                self.rows.append(FakeGrant(self.rows, {
                    "name": first, "ticket": TICKET, "technician_user": USER,
                    "employee": IDENTITY.employee, "company": IDENTITY.company,
                    "state": "Active", "active_key": _active_key(TICKET, USER), "revoked_at": None,
                }))
            return original_sql(query, value, **kwargs)
        with patch.object(self.db, "sql", side_effect=resumed_sql):
            second = _grant_after_authorization(ticket=TICKET, user=USER, issuer="issuer", reason="work")
        self.assertEqual(second, first)
        self.assertEqual(len(self.rows), 1)

    def test_revocation_locks_ticket_before_current_grant_read(self):
        _grant_after_authorization(ticket=TICKET, user=USER, issuer="issuer", reason="work")
        self.locked.clear()
        _revoke_after_authorization(ticket=TICKET, user=USER, revoker="issuer", reason="done")
        self.assertEqual(len(self.locked), 2)
        self.assertIn("tabHD Ticket", self.locked[0][0])
        self.assertIn("tabTELECTRO Ticket Worker Grant", self.locked[1][0])
        self.assertTrue(all("FOR UPDATE" in query for query, _ in self.locked))

    def test_unique_collision_fails_closed_and_preserves_cause(self):
        error = self.unique_error("active key collision")
        with patch.object(FakeGrant, "insert", side_effect=error):
            with self.assertRaises(BookingCooptionError) as caught:
                _grant_after_authorization(ticket=TICKET, user=USER, issuer="issuer", reason="work")
        self.assertIs(caught.exception.__cause__, error)
        self.assertEqual(self.rows, [])

    def test_unrelated_insert_failure_propagates(self):
        error = RuntimeError("database unavailable")
        with patch.object(FakeGrant, "insert", side_effect=error):
            with self.assertRaises(RuntimeError) as caught:
                _grant_after_authorization(ticket=TICKET, user=USER, issuer="issuer", reason="work")
        self.assertIs(caught.exception, error)

    def test_schema_has_unique_active_key_and_private_permissions(self):
        path = Path(__file__).resolve().parents[1] / "ftelephony/doctype/telectro_ticket_worker_grant/telectro_ticket_worker_grant.json"
        schema = json.loads(path.read_text())
        fields = {field["fieldname"]: field for field in schema["fields"]}
        self.assertEqual(schema["permissions"], [])
        self.assertEqual(schema["engine"], "InnoDB")
        self.assertEqual(fields["active_key"]["unique"], 1)
        self.assertEqual(fields["ticket"]["options"], "HD Ticket")
        self.assertEqual(fields["company"]["options"], "Company")

    def test_active_key_is_unambiguous_and_rejects_blank(self):
        self.assertNotEqual(_active_key("ab", "c"), _active_key("a", "bc"))
        with self.assertRaises(BookingCooptionError):
            _active_key("", USER)

    def test_lookup_ignores_ordinary_share_and_requires_matching_identity(self):
        self.assertIsNone(_active_grant(TICKET, IDENTITY))
        name = _grant_after_authorization(ticket=TICKET, user=USER, issuer="issuer", reason="work")
        self.assertEqual(_active_grant(TICKET, IDENTITY), name)
        with self.assertRaises(BookingCooptionError):
            _active_grant(TICKET, TechnicianBookingIdentity(USER, "other", "Company A"))

    def test_repeat_grant_is_idempotent_under_ticket_lock(self):
        args = dict(ticket=TICKET, user=USER, issuer="issuer", reason="work")
        first = _grant_after_authorization(**args)
        second = _grant_after_authorization(**args)
        self.assertEqual(first, second)
        self.assertEqual(len(self.rows), 1)
        self.assertEqual(len(self.locked), 4)
        self.assertTrue(all("FOR UPDATE" in query for query, _ in self.locked))

    def test_revoke_retains_episode_and_regrant_creates_new_one(self):
        args = dict(ticket=TICKET, user=USER, issuer="issuer", reason="work")
        first = _grant_after_authorization(**args)
        self.assertEqual(_revoke_after_authorization(ticket=TICKET, user=USER, revoker="issuer", reason="done"), first)
        self.assertIsNone(_active_grant(TICKET, IDENTITY))
        self.assertIsNone(self.rows[0]["active_key"])
        self.assertEqual(self.rows[0]["state"], "Revoked")
        second = _grant_after_authorization(**args)
        self.assertNotEqual(first, second)
        self.assertEqual(len(self.rows), 2)

    def test_malformed_active_row_denied(self):
        _grant_after_authorization(ticket=TICKET, user=USER, issuer="issuer", reason="work")
        self.rows[0]["company"] = "foreign"
        with self.assertRaises(BookingCooptionError):
            _active_grant(TICKET, IDENTITY)

    def test_recipient_resolution_rejects_partner_role(self):
        self.identity_patch.stop()
        self.db.get_value = lambda doctype, name, fields, **kwargs: {"name": name, "enabled": 1, "user_type": "System User"}
        self.frappe.get_all = lambda doctype, **kwargs: ["TELECTRO-POC Role - Tech", "TELECTRO-POC Role - Partner"]
        fake_privacy = types.SimpleNamespace(classify_actor_roles=lambda roles: "unknown")
        with patch.dict(sys.modules, {"telephony.customer_communication_privacy": fake_privacy}):
            with self.assertRaises(BookingCooptionError):
                _require_recipient_identity(USER)

    def test_no_hardcoded_company_or_docshare_authority(self):
        source = (Path(__file__).resolve().parents[1] / "time_booking_cooption.py").read_text()
        self.assertNotIn("DocShare", source.split("def _active_grant")[1])
        self.assertNotIn("Company A", source)
