"""Focused tests for the private Supervisor reporting grant boundary."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import frappe

from telephony import supervisor_reporting_grant as grants
from telephony.ftelephony.doctype.telectro_supervisor_reporting_grant.telectro_supervisor_reporting_grant import (
    TELECTROSupervisorReportingGrant,
)
from telephony.time_booking_identity import TechnicianBookingIdentity, TechnicianIdentityError


SUPERVISOR = "supervisor@example.test"
IDENTITY = TechnicianBookingIdentity("tech@example.test", "EMP-1", "Company")
NOW = datetime(2026, 11, 23, 10)
GRANT_ERROR = grants.SupervisorReportingGrantError


class TestSupervisorReportingGrant(unittest.TestCase):
    def setUp(self):
        self.rows = {}
        self.savepoints = {}
        self.session = SimpleNamespace(user="Administrator")
        self.roles = {SUPERVISOR: {grants.SUPERVISOR_ROLE}}
        self.enabled = True
        self.role_disabled = 0
        self.identity = IDENTITY
        self.restrictions = {}
        self.now = NOW
        self.sequence = 0
        self.fail_after_write = False
        self.subject = frappe._dict(name=IDENTITY.employee, user_id=IDENTITY.user, company=IDENTITY.company)
        fake = SimpleNamespace(
            session=self.session, get_all=self.get_all, get_doc=self.get_doc,
            UniqueValidationError=frappe.UniqueValidationError, DoesNotExistError=frappe.DoesNotExistError,
            db=SimpleNamespace(get_value=self.get_value),
        )
        db = SimpleNamespace(
            savepoint=lambda name: self.savepoints.update({name: deepcopy(self.rows)}),
            release_savepoint=self.savepoints.pop,
            rollback=self.rollback,
        )
        for item in (
            patch.object(grants, "frappe", fake),
            patch.object(frappe, "db", db, create=True),
            patch.object(grants, "now_datetime", lambda: self.now),
            patch.object(grants, "_resolve_technician_identity", self.resolve_technician),
            patch.object(grants, "get_user_permissions", lambda user: self.restrictions),
        ):
            item.start()
            self.addCleanup(item.stop)

    def rollback(self, save_point):
        self.rows = self.savepoints[save_point]

    def resolve_technician(self, user):
        if self.identity is None or self.identity.user != user:
            raise TechnicianIdentityError()
        return self.identity

    def get_value(self, doctype, name, fields, **kwargs):
        if doctype == "User" and name in self.roles:
            return frappe._dict(name=name, enabled=int(self.enabled), user_type="System User")
        if doctype == "Role" and name == grants.SUPERVISOR_ROLE:
            return frappe._dict(name=name, disabled=self.role_disabled)
        if doctype == "Employee" and name == self.subject.name:
            self.assertTrue(kwargs["for_update"])
            return self.subject

    def get_all(self, doctype, *, filters, **kwargs):
        if doctype == "Has Role":
            return list(self.roles.get(filters["parent"], ()))
        self.assertEqual(doctype, grants.DOCTYPE)
        self.assertEqual(filters["revoked_at"], ["is", "not set"])
        return [
            row.copy() for row in self.rows.values()
            if row.supervisor_user == filters["supervisor_user"] and row.revoked_at is None
        ]

    def get_doc(self, arg, name=None, **kwargs):
        if isinstance(arg, str):
            self.assertEqual(arg, grants.DOCTYPE)
            self.assertTrue(kwargs["for_update"])
            if name not in self.rows:
                raise frappe.DoesNotExistError
            data = self.rows[name].copy()
        else:
            data = frappe._dict(arg)
        doc = frappe._dict(data)
        doc.insert = lambda *, ignore_permissions: self.write(doc, insert=True, elevated=ignore_permissions)
        doc.save = lambda *, ignore_permissions: self.write(doc, insert=False, elevated=ignore_permissions)
        return doc

    def write(self, doc, *, insert, elevated):
        self.assertTrue(elevated)
        grants.validate_supervisor_reporting_grant(doc, None if insert else self.rows[doc.name])
        if insert:
            if any(row.active_key == doc.active_key for row in self.rows.values()):
                raise frappe.UniqueValidationError
            self.sequence += 1
            doc.name = str(self.sequence)
        self.rows[doc.name] = frappe._dict({key: value for key, value in doc.items() if key not in ("insert", "save")})
        if self.fail_after_write:
            raise RuntimeError("Injected post-write failure")

    def create(self, **values):
        return grants.create_supervisor_reporting_grant(**({
            "supervisor_user": SUPERVISOR, "employee": IDENTITY.employee, "reason": "Approved roster",
        } | values))

    def resolve_scope(self):
        with patch.object(self.session, "user", SUPERVISOR):
            return grants.resolve_supervisor_reporting_scope()

    def test_create_uses_authoritative_mapping_and_audit_metadata(self):
        name = self.create()
        row = self.rows[name]
        self.assertEqual((row.supervisor_user, row.employee, row.technician_user, row.company),
                         (SUPERVISOR, IDENTITY.employee, IDENTITY.user, IDENTITY.company))
        self.assertEqual((row.granted_at, row.granted_by, row.grant_reason), (NOW, "Administrator", "Approved roster"))
        self.assertEqual(self.resolve_scope(), {IDENTITY})

    def test_historical_scope_revocation_and_regrant(self):
        first = self.create()
        # The current scope applies to matching tuples regardless of the booking day.
        historical = (NOW - timedelta(days=100), IDENTITY)
        self.assertIn(historical[1], self.resolve_scope())
        self.now += timedelta(seconds=1)
        grants.revoke_supervisor_reporting_grant(grant_name=first, reason="Removed from roster")
        old = self.rows[first]
        self.assertEqual((old.revoked_at, old.revoked_by, old.revocation_reason, old.active_key),
                         (self.now, "Administrator", "Removed from roster", None))
        self.assertNotIn(historical[1], self.resolve_scope())
        second = self.create()
        self.assertNotEqual(second, first)
        self.assertEqual(self.rows[first], old)
        self.assertIn(historical[1], self.resolve_scope())
        with self.assertRaises(GRANT_ERROR):
            grants.revoke_supervisor_reporting_grant(grant_name=first, reason="Already revoked")

    def test_scope_requires_governance_and_active_grant(self):
        self.assertEqual(self.resolve_scope(), frozenset())
        self.create()
        self.role_disabled = 1
        with self.assertRaises(GRANT_ERROR):
            self.resolve_scope()
        self.role_disabled = 0
        self.enabled = False
        with self.assertRaises(GRANT_ERROR):
            self.resolve_scope()
        self.enabled = True
        self.roles[SUPERVISOR] = {"TELECTRO-POC Role - Coordinator Ops"}
        with self.assertRaises(GRANT_ERROR):
            self.resolve_scope()
        self.roles[SUPERVISOR].add(grants.SUPERVISOR_ROLE)
        self.roles[SUPERVISOR].add("Customer")
        with self.assertRaises(GRANT_ERROR):
            self.resolve_scope()

    def test_missing_or_changed_employee_mapping_never_inherits_access(self):
        current = self.create()
        for mapping in (
            TechnicianBookingIdentity("new@example.test", IDENTITY.employee, IDENTITY.company),
            TechnicianBookingIdentity(IDENTITY.user, "EMP-2", IDENTITY.company),
            TechnicianBookingIdentity(IDENTITY.user, IDENTITY.employee, "Other Company"),
            None,
        ):
            with self.subTest(mapping=mapping):
                self.identity = mapping
                self.assertEqual(self.resolve_scope(), frozenset())
                with self.assertRaises(GRANT_ERROR):
                    self.create()
        grants.revoke_supervisor_reporting_grant(grant_name=current, reason="Mapping no longer valid")

    def test_native_company_and_employee_restrictions_independently_narrow_scope(self):
        self.create()
        for doctype, context in (("Company", "Timesheet"), ("Company", "Employee"), ("Employee", "Employee"),
                                 ("Employee", None)):
            with self.subTest(doctype=doctype, context=context):
                self.restrictions = {doctype: [{"doc": "other", "applicable_for": context}]}
                self.assertEqual(self.resolve_scope(), frozenset())
        self.restrictions = {"Company": [{"doc": "other", "applicable_for": "Sales Invoice"}]}
        self.assertEqual(self.resolve_scope(), {IDENTITY})
        self.restrictions = None
        with self.assertRaises(GRANT_ERROR):
            self.resolve_scope()

    def test_duplicate_is_denied_and_active_key_stays_bound_to_employee_scope(self):
        first = self.create()
        with self.assertRaises(GRANT_ERROR):
            self.create()
        self.assertEqual(set(self.rows), {first})
        row = self.rows[first]
        same_scope = row.copy()
        same_scope["technician_user"] = "remapped@example.test"
        self.assertEqual(grants._active_key(row), grants._active_key(same_scope))
        schema = Path(__file__).parents[1] / "ftelephony/doctype/telectro_supervisor_reporting_grant"
        model = json.loads((schema / "telectro_supervisor_reporting_grant.json").read_text())
        key = next(field for field in model["fields"] if field["fieldname"] == "active_key")
        self.assertEqual((model["engine"], key["unique"], key.get("reqd")), ("InnoDB", 1, None))
        self.assertEqual(model["permissions"], [])

    def test_create_and_revoke_roll_back_after_post_write_failure(self):
        self.fail_after_write = True
        with self.assertRaisesRegex(RuntimeError, "post-write"):
            self.create()
        self.assertEqual(self.rows, {})
        self.assertIsNone(grants._transition.get())
        self.fail_after_write = False
        name = self.create()
        self.fail_after_write = True
        with self.assertRaisesRegex(RuntimeError, "post-write"):
            grants.revoke_supervisor_reporting_grant(grant_name=name, reason="Close")
        self.assertIsNone(self.rows[name].revoked_at)
        self.assertEqual(self.resolve_scope(), {IDENTITY})
        self.assertEqual(self.savepoints, {})

    def test_unauthorized_operations_and_direct_controller_edits_are_denied(self):
        name = self.create()
        for user in (SUPERVISOR, IDENTITY.user, "system-manager@example.test"):
            with self.subTest(user=user), patch.object(self.session, "user", user):
                with self.assertRaises(GRANT_ERROR):
                    self.create()
                with self.assertRaises(GRANT_ERROR):
                    grants.revoke_supervisor_reporting_grant(grant_name=name, reason="No")
        with self.assertRaises(GRANT_ERROR):
            self.create(reason=" ")
        with self.assertRaises(GRANT_ERROR):
            grants.revoke_supervisor_reporting_grant(grant_name=name, reason="")
        doc = self.rows[name].copy()
        with self.assertRaises(GRANT_ERROR):
            grants.validate_supervisor_reporting_grant(doc, self.rows[name])
        for method, args in (("validate_share", (None,)), ("before_rename", ("old", "new")), ("on_trash", ())):
            with self.assertRaises(GRANT_ERROR):
                getattr(TELECTROSupervisorReportingGrant, method)(None, *args)

    def test_transition_cannot_rewrite_scope_or_active_key(self):
        name = self.create()
        prior = self.rows[name]
        doc = frappe._dict(prior | {
            "company": "Other", "active_key": None, "revoked_by": "Administrator",
            "revoked_at": NOW + timedelta(seconds=1), "revocation_reason": "Remove",
        })
        token = grants._transition.set((doc, False))
        try:
            with self.assertRaises(GRANT_ERROR):
                grants.validate_supervisor_reporting_grant(doc, prior)
        finally:
            grants._transition.reset(token)
        self.rows[name].active_key = "corrupt"
        with self.assertRaises(GRANT_ERROR):
            self.resolve_scope()


@unittest.skipUnless(
    os.environ.get("TELECTRO_GRANT_TEST_DEV") == "1",
    "Run explicitly in the DEV backend sites directory",
)
class TestSupervisorReportingGrantMariaDB(unittest.TestCase):
    def setUp(self):
        frappe.init(site="frontend", sites_path=".")
        frappe.connect()
        self.addCleanup(self._close_connection)
        supervisors = frappe.get_all(
            "Has Role", filters={"parenttype": "User", "role": grants.SUPERVISOR_ROLE},
            pluck="parent",
        )
        technicians = frappe.get_all(
            "Has Role", filters={"parenttype": "User", "role": "TELECTRO-POC Role - Tech"},
            pluck="parent",
        )
        for supervisor in supervisors:
            try:
                grants._require_supervisor(supervisor)
            except GRANT_ERROR:
                continue
            for user in technicians:
                try:
                    identity = grants._resolve_technician_identity(user)
                except TechnicianIdentityError:
                    continue
                scope = dict(supervisor_user=supervisor, employee=identity.employee, company=identity.company)
                if not frappe.db.exists(grants.DOCTYPE, scope):
                    self.scope = scope
                    return
        self.skipTest("No unused eligible grant scope in DEV")

    @staticmethod
    def _close_connection():
        frappe.db.rollback()
        frappe.destroy()

    def _create(self):
        return grants.create_supervisor_reporting_grant(
            supervisor_user=self.scope["supervisor_user"], employee=self.scope["employee"],
            reason="DEV transactional concurrency verification",
        )

    def test_native_unique_index_and_competing_creates(self):
        index = frappe.db.sql(
            "SHOW INDEX FROM `tabTELECTRO Supervisor Reporting Grant` WHERE Column_name = 'active_key'",
            as_dict=True,
        )
        self.assertEqual([(row.Non_unique, row.Null) for row in index], [(0, "YES")])
        original = self._create()
        with self.assertRaises(GRANT_ERROR):
            self._create()  # MariaDB rejects a second active key in the same transaction.

        def compete():
            frappe.init(site="frontend", sites_path=".")
            frappe.connect()
            try:
                frappe.db.sql("SET SESSION innodb_lock_wait_timeout = 1")
                return self._create()
            finally:
                self._close_connection()

        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.assertRaises(frappe.QueryTimeoutError):
                pool.submit(compete).result(timeout=10)
            self.assertTrue(frappe.db.exists(grants.DOCTYPE, original))
            frappe.db.rollback()
            self.assertNotEqual(pool.submit(compete).result(timeout=10), original)
        self.assertFalse(frappe.db.exists(grants.DOCTYPE, self.scope))
