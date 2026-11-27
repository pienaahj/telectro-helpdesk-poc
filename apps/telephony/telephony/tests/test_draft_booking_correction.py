import copy
import json
import types
import unittest
from unittest.mock import Mock, call, patch

from frappe import QueryDeadlockError, QueryTimeoutError
from werkzeug.wrappers import Request

from telephony.tests.test_time_booking_correction_audit import snapshot
from telephony.api import booking_correction as api, time_booking
from telephony.tests.test_time_booking_correction_audit import snapshot
from telephony.tests.test_time_booking_post import Reference, customer_mapping_sql
REAL_GUARD = api._guard

from telephony.time_booking_identity import TechnicianBookingIdentity
from telephony.time_booking_ownership import BookingOwnershipError


class Doc:
    def __init__(self, state):
        self.state = state
        self.time_logs = state["time_logs"]
        self.save = Mock()
        self.delete = Mock()
        self.check_permission = Mock()
        self.flags = types.SimpleNamespace(ignore_permissions=None)

    @property
    def docstatus(self):
        return self.state["docstatus"]

    def as_dict(self):
        return self.state


class TestDraftCorrection(unittest.TestCase):
    def setUp(self):
        self.state = snapshot()
        self.state["modified"] = "2026-11-17T12:00:00"
        self.doc = Doc(self.state)
        self.identity = TechnicianBookingIdentity("tech@example.com", "EMP-1", "Company A")
        self.audit_row = None
        self.f = types.SimpleNamespace(
            db=types.SimpleNamespace(sql=self.sql), get_doc=Mock(return_value=self.doc))
        self.patches = [patch.object(api, "frappe", self.f),
                        patch.object(api, "_guard", return_value=self.identity),
                        patch.object(api, "prepare_attribution", return_value={}),
                        patch.object(api, "TelectroBookingTimesheet", Doc),
                        patch.object(api, "record_correction_event", side_effect=self.record)]
        for p in self.patches:
            p.start(); self.addCleanup(p.stop)

    def sql(self, query, value, **kw):
        self.assertIn("FOR UPDATE", query)
        if "tabTimesheet" in query: return [{"name": "TS-1"}]
        return [self.audit_row] if self.audit_row else []

    def record(self, **kwargs):
        self.recorded = copy.deepcopy(kwargs)
        return "AUDIT-1"

    def call(self, **kw):
        args = dict(name="TS-1", event_id="event", reason="repair entry",
                    action="Draft Withdrawal", expected_modified="2026-11-17T12:00:00")
        args.update(kw)
        token = api._active_booking.set(True)
        try:
            return api._execute(**args)
        finally:
            api._active_booking.reset(token)

    def test_withdraw_snapshots_before_native_delete(self):
        self.assertEqual(self.call(), {"timesheet": "TS-1", "audit": "AUDIT-1"})
        self.assertEqual(self.recorded["before"]["name"], "TS-1")
        self.assertEqual(self.recorded["before"]["time_logs"][0]["name"], "ROW-1")
        self.doc.delete.assert_called_once_with()

    def test_correction_updates_one_row_and_records_before_after(self):
        self.call(action="Draft Correction", values={"description": "Corrected"})
        self.doc.save.assert_called_once_with()
        self.doc.delete.assert_not_called()
        self.assertEqual(self.recorded["before"]["time_logs"][0]["description"], "Repair")
        self.assertEqual(self.recorded["after"]["time_logs"][0]["description"], "Corrected")
        self.assertEqual(len(self.doc.time_logs), 1)

    def test_denies_foreign_unmanaged_and_non_draft(self):
        for field, value in (("user", "foreign"), ("docstatus", 1), ("docstatus", 2),
                             ("custom_telectro_booking_origin", "")):
            original = self.state[field]; self.state[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(PermissionError): self.call()
            self.state[field] = original
        self.doc.delete.assert_not_called()

    def test_owned_withdrawal_uses_scoped_native_permission(self):
        self.doc.check_permission.side_effect = PermissionError(
            "general Timesheet access denied"
        )

        def verify_delete_scope():
            self.assertIs(self.doc.flags.ignore_permissions, True)

        self.doc.delete.side_effect = verify_delete_scope

        result = self.call()

        self.assertEqual(
            result,
            {"timesheet": "TS-1", "audit": "AUDIT-1"},
        )
        self.doc.check_permission.assert_not_called()
        self.doc.delete.assert_called_once_with()
        self.assertIsNone(self.doc.flags.ignore_permissions)

    def test_owned_correction_uses_scoped_native_permission(self):
        self.doc.check_permission.side_effect = PermissionError(
            "general Timesheet access denied"
        )

        def verify_save_scope():
            self.assertIs(self.doc.flags.ignore_permissions, True)

        self.doc.save.side_effect = verify_save_scope

        result = self.call(
            action="Draft Correction",
            values={"description": "Corrected"},
        )

        self.assertEqual(
            result,
            {"timesheet": "TS-1", "audit": "AUDIT-1"},
        )
        self.doc.check_permission.assert_not_called()
        self.doc.save.assert_called_once_with()
        self.assertIsNone(self.doc.flags.ignore_permissions)

    def test_inherited_permission_elevation_is_rejected(self):
        self.doc.flags.ignore_permissions = True

        with self.assertRaises(BookingOwnershipError):
            self.call()

        self.doc.save.assert_not_called()
        self.doc.delete.assert_not_called()
        self.assertIs(self.doc.flags.ignore_permissions, True)

    def test_audit_failure_prevents_withdrawal(self):
        with patch.object(api, "record_correction_event", side_effect=RuntimeError("audit")):
            with self.assertRaises(RuntimeError): self.call()
        self.doc.delete.assert_not_called()

    def test_native_save_and_delete_failures_escape(self):
        self.doc.save.side_effect = RuntimeError("save")
        with self.assertRaises(RuntimeError):
            self.call(action="Draft Correction", values={"description": "New"})
        self.assertIsNone(self.doc.flags.ignore_permissions)

        self.doc.delete.side_effect = RuntimeError("delete")
        with self.assertRaises(RuntimeError): self.call()
        self.assertIsNone(self.doc.flags.ignore_permissions)

    def test_retry_returns_same_event_without_mutation(self):
        import json
        from telephony.time_booking_correction_audit import _snapshot
        self.audit_row = dict(name="AUDIT-1", actor=self.identity.user,
            action="Draft Withdrawal", reason="repair entry", original_timesheet="TS-1",
            before_snapshot=_snapshot(self.state), after_snapshot=None)
        self.assertEqual(self.call()["audit"], "AUDIT-1")
        self.doc.delete.assert_not_called()
        with self.assertRaises(BookingOwnershipError): self.call(reason="different")

    def test_required_reason(self):
        with self.assertRaises(api.BookingInputError): self.call(reason=" ")
        self.doc.delete.assert_not_called()

    def test_withdraw_endpoint_failure_rolls_back_request(self):
        import sys
        import frappe
        rollback = Mock()
        local = types.SimpleNamespace(
            request=types.SimpleNamespace(method="POST", path="/api/method/" + api.PREFIX + "withdraw_draft_booking"),
            form_dict=types.SimpleNamespace(cmd=api.PREFIX + "withdraw_draft_booking"),
            db=types.SimpleNamespace(rollback=rollback))
        fake = types.SimpleNamespace(local=local, session=types.SimpleNamespace(user=self.identity.user))
        with patch.dict(sys.modules, {"frappe": fake}), patch.object(api, "_execute", side_effect=RuntimeError("failure")):
            with self.assertRaises(RuntimeError):
                api.withdraw_draft_booking.__wrapped__(timesheet_name="TS-1", event_id="event", reason="reason")
        rollback.assert_called_once()

    def test_http_get_denied(self):
        import sys
        local = types.SimpleNamespace(request=types.SimpleNamespace(method="GET"),
                                      form_dict=types.SimpleNamespace(cmd="wrong"))
        fake = types.SimpleNamespace(local=local, session=types.SimpleNamespace(user=self.identity.user))
        with patch.dict(sys.modules, {"frappe": fake}):
            with self.assertRaises(PermissionError):
                api.withdraw_draft_booking.__wrapped__(timesheet_name="TS-1", event_id="event", reason="reason")

    def test_stale_revision_blocks_correction_and_withdrawal(self):
        self.state["modified"] = "2026-11-17T12:01:00"
        for values in (None, {"description": "Stale"}):
            with self.assertRaises(BookingOwnershipError): self.call(values=values)
        self.doc.save.assert_not_called()
        self.doc.delete.assert_not_called()
        self.assertFalse(hasattr(self, "recorded"))

    def test_missing_revision_is_denied(self):
        with self.assertRaises(BookingOwnershipError): self.call(expected_modified=None)
        self.doc.delete.assert_not_called()

    def test_retry_accepts_persisted_six_decimal_hours(self):
        from datetime import datetime
        from telephony.time_booking_correction_audit import _snapshot

        before = copy.deepcopy(self.state)
        after = copy.deepcopy(before)

        after["time_logs"][0].update({
            "from_time": "2026-11-18T19:00:00",
            "to_time": "2026-11-18T19:20:00",
            "hours": 0.333333,
            "description": "20-minute corrected entry",
        })

        self.audit_row = dict(
            name="AUDIT-1",
            actor=self.identity.user,
            action="Draft Correction",
            reason="repair entry",
            original_timesheet="TS-1",
            before_snapshot=_snapshot(before),
            after_snapshot=_snapshot(after),
        )

        values = {
            "from_time": datetime(2026, 11, 18, 19, 0),
            "to_time": datetime(2026, 11, 18, 19, 20),
            "hours": 20 / 60,
            "description": "20-minute corrected entry",
        }

        result = self.call(
            action="Draft Correction",
            values=values,
        )

        self.assertEqual(
            result,
            {"timesheet": "TS-1", "audit": "AUDIT-1"},
        )

        self.doc.save.assert_not_called()
        self.doc.delete.assert_not_called()

        with self.assertRaises(BookingOwnershipError):
            self.call(
                action="Draft Correction",
                values={**values, "hours": 19 / 60},
            )

        self.doc.save.assert_not_called()
        self.doc.delete.assert_not_called()

    def test_correction_retry_and_conflicting_replacement(self):
        from telephony.time_booking_correction_audit import _snapshot
        before = copy.deepcopy(self.state)
        after = copy.deepcopy(before)
        after["time_logs"][0]["description"] = "Corrected"
        self.audit_row = dict(name="AUDIT-1", actor=self.identity.user,
            action="Draft Correction", reason="repair entry", original_timesheet="TS-1",
            before_snapshot=_snapshot(before), after_snapshot=_snapshot(after))
        self.assertEqual(self.call(action="Draft Correction", values={"description": "Corrected"})["audit"], "AUDIT-1")
        with self.assertRaises(BookingOwnershipError):
            self.call(action="Draft Correction", values={"description": "Other"})
        with self.assertRaises(BookingOwnershipError): self.call()
        self.doc.save.assert_not_called()
        self.doc.delete.assert_not_called()

    def test_deleted_target_cannot_be_corrected(self):
        self.f.db.sql = lambda query, value, **kw: []
        with self.assertRaises(BookingOwnershipError):
            self.call(action="Draft Correction", values={"description": "New"})
        self.doc.save.assert_not_called()

    def test_lock_precedes_event_and_current_document_read(self):
        queries = []
        original = self.sql
        def sql(query, value, **kw):
            queries.append(query)
            return original(query, value, **kw)
        self.f.db.sql = sql
        self.call()
        self.assertIn("tabTimesheet", queries[0])
        self.assertIn("tabTELECTRO Booking Correction Audit", queries[1])
        self.f.get_doc.assert_called_once_with("Timesheet", "TS-1", for_update=True)

    def endpoint(self, correction=True, **updates):
        import sys
        from datetime import datetime
        from telephony.api import time_booking
        name = "correct_draft_booking" if correction else "withdraw_draft_booking"
        command = api.PREFIX + name
        before = copy.deepcopy(self.state)
        had_record = hasattr(self, "recorded")
        def rollback():
            self.state.clear(); self.state.update(copy.deepcopy(before))
            self.doc.time_logs = self.state["time_logs"]
            if not had_record and hasattr(self, "recorded"): del self.recorded
        rb = Mock(side_effect=rollback)
        self.f.local = types.SimpleNamespace(
            request=types.SimpleNamespace(method="POST", path="/api/method/" + command),
            form_dict=types.SimpleNamespace(cmd=command),
            db=types.SimpleNamespace(rollback=rb))
        self.f.session = types.SimpleNamespace(user=self.identity.user)
        self.f.utils = types.SimpleNamespace(now_datetime=lambda: datetime(2026, 11, 17, 14))
        args = dict(timesheet_name="TS-1", event_id="event", reason="reason",
                    expected_modified="2026-11-17T12:00:00")
        if correction:
            args.update(
                work_context="Helpdesk",
                from_time="2026-11-16 09:00:00",
                duration_minutes=60,
                description="Corrected",
                activity_type="Repair & Maintenance",
                ticket_name="T",
                service_area=None,
                work_location="Remote",
                work_origin="Direct / Ad-hoc",
                external_reference=None,
                other_origin_description=None,
                emergency=0,
            )
        args.update(updates)
        try:
            with patch.dict(sys.modules, {"frappe": self.f}), patch.object(time_booking, "frappe", self.f):
                return getattr(api, name).__wrapped__(**args)
        finally:
            self.rollback = rb

    def test_activation_rejections_for_both_endpoints(self):
        for correction in (True, False):
            for mode in ("disabled", "incomplete", "schema"):
                self.f.conf = {"telectro_time_booking_enabled": 0 if mode == "disabled" else 1}
                self.f.db.table_exists = Mock(return_value=mode != "schema")
                failure = api.ActivationConfigurationError() if mode == "incomplete" else None
                with patch.object(api, "_guard", side_effect=REAL_GUARD), patch.object(
                    api, "_require_activation_configuration", side_effect=failure):
                    with self.assertRaises(api.ActivationConfigurationError):
                        self.endpoint(correction=correction)
                self.doc.save.assert_not_called(); self.doc.delete.assert_not_called()
                self.assertFalse(hasattr(self, "recorded"))

    def test_invalid_replacement_inputs_leave_original_unchanged(self):
        original = copy.deepcopy(self.state)
        for updates in ({"from_time": "bad"}, {"from_time": "2026-11-16"},
                        {"duration_minutes": 0}, {"duration_minutes": -1},
                        {"duration_minutes": True}, {"description": " "},
                        {"work_context": "Unknown"}):
            with self.subTest(updates=updates):
                with self.assertRaises(ValueError): self.endpoint(**updates)
                self.assertEqual(self.state, original)
                self.doc.save.assert_not_called()
                self.assertFalse(hasattr(self, "recorded"))

    def test_correction_rejects_unapproved_activity_before_saving(self):
        original = copy.deepcopy(self.state)
        with patch.object(api, "_authorize_references"), patch.object(api, "_visible") as visible:
            with self.assertRaises(api.BookingInputError):
                self.endpoint(activity_type="Execution")

        visible.assert_not_called()
        self.doc.save.assert_not_called()
        self.assertEqual(self.state, original)
        self.assertFalse(hasattr(self, "recorded"))

    def ticket_customer_references(self):
        ticket = Reference(
            "HD Ticket", "T", customer="C", custom_customer="ERP-C",
            custom_service_area="Routing", status="Open", status_category="Open",
            creation="2026-11-15 09:00:00",
        )
        self.current_ticket = Reference("HD Ticket", "T", **ticket)
        customer = Reference("HD Customer", "C", custom_erp_customer="ERP-C")
        self.current_customer = Reference("HD Customer", "C", **customer)
        activity = Reference("Activity Type", "Repair & Maintenance")
        references = {(doc.doctype, doc.name): doc for doc in (ticket, customer, activity)}

        def get_doc(doctype, name=None, *, for_update=False):
            if isinstance(doctype, dict):
                if doctype["doctype"] == "HD Customer":
                    return self.current_customer
                self.assertEqual(doctype["doctype"], "HD Ticket")
                return self.current_ticket
            if (doctype, name) == ("Timesheet", "TS-1"):
                self.assertTrue(for_update)
                return self.doc
            self.assertFalse(for_update)
            return references[(doctype, name)]

        def get_value(doctype, name, fields, **kwargs):
            if doctype == "HD Ticket":
                self.assertEqual((name, fields), ("T", "*"))
                self.assertEqual(kwargs, {
                    "as_dict": True, "order_by": None, "for_update": True, "wait": False,
                })
                return self.current_ticket
            if doctype == "HD Customer":
                self.assertEqual((name, fields), ("C", "*"))
                self.assertEqual(kwargs, {
                    "as_dict": True, "order_by": None, "for_update": True, "wait": False,
                })
                return self.current_customer
            self.assertEqual((doctype, fields), ("Customer", "name"))
            self.assertEqual(kwargs, {"order_by": None, "for_update": True, "wait": False})
            return name

        def sql(query, value=None, **kwargs):
            if "FOR UPDATE NOWAIT" in query or "FOR UPDATE" not in query:
                return customer_mapping_sql(query, value)
            return self.sql(query, value, **kwargs)

        self.f.get_doc.side_effect = get_doc
        self.f.PermissionError = PermissionError
        self.f.DoesNotExistError = LookupError
        self.f.QueryDeadlockError = QueryDeadlockError
        self.f.QueryTimeoutError = QueryTimeoutError
        self.f.db.db_type = "mariadb"
        self.f.db.sql = Mock(side_effect=sql)
        self.f.db.get_value = Mock(side_effect=get_value)
        areas = patch.object(api, "_allowed_service_areas", return_value=("Routing",))
        areas.start()
        self.addCleanup(areas.stop)
        return ticket, customer

    def test_correction_uses_locked_ticket_customer_over_snapshot(self):
        ticket, _customer = self.ticket_customer_references()
        ticket.update(customer="OTHER", custom_customer="ERP-OTHER")
        result = self.endpoint(customer_name="C")

        self.assertEqual(result, {"timesheet": "TS-1", "audit": "AUDIT-1"})
        self.doc.save.assert_called_once_with()
        self.assertIsNone(self.recorded["before"]["time_logs"][0]["custom_hd_customer"])
        self.assertEqual(self.recorded["after"]["time_logs"][0]["custom_hd_customer"], "C")
        ticket_reads = [
            call.args for call in self.f.get_doc.call_args_list if call.args[0] == "HD Ticket"
        ]
        self.assertEqual(ticket_reads, [("HD Ticket", "T")])
        self.assertEqual(self.f.db.get_value.call_args_list, [
            call("HD Ticket", "T", "*", as_dict=True, order_by=None, for_update=True, wait=False),
            call("Customer", "ERP-C", "name", order_by=None, for_update=True, wait=False),
            call("HD Customer", "C", "*", as_dict=True, order_by=None, for_update=True, wait=False),
        ])
        self.assertEqual(self.f.db.sql.call_args_list[-2].args[1], ("ERP-C",))
        self.rollback.assert_not_called()

    def test_correction_rejects_unchanged_customer_when_new_ticket_conflicts(self):
        self.ticket_customer_references()
        original_row = self.doc.time_logs[0]
        original_row["custom_hd_customer"] = "C"
        self.current_ticket["custom_customer"] = "ERP-OTHER"
        original = copy.deepcopy(self.state)

        with self.assertRaisesRegex(
            api.BookingReferenceDenied, r"^Booking reference is unavailable\.$",
        ):
            self.endpoint(ticket_name="T", customer_name="C")

        self.assertEqual(original_row, original["time_logs"][0])
        self.assertEqual(self.state, original)
        self.doc.save.assert_not_called()
        self.doc.delete.assert_not_called()
        self.assertIsNone(self.audit_row)
        api.record_correction_event.assert_not_called()
        self.rollback.assert_called_once_with()

    def test_changed_ticket_inherits_customer_despite_stale_snapshot(self):
        ticket, _customer = self.ticket_customer_references()
        ticket["custom_customer"] = "ERP-OTHER"

        result = self.endpoint()

        self.assertEqual(result, {"timesheet": "TS-1", "audit": "AUDIT-1"})
        self.doc.save.assert_called_once_with()
        self.assertEqual(self.recorded["after"]["time_logs"][0]["custom_hd_customer"], "C")
        self.assertIsNone(self.recorded["after"]["requested_customer_name"])
        self.assertEqual(self.f.db.get_value.call_args_list, [
            call("HD Ticket", "T", "*", as_dict=True, order_by=None, for_update=True, wait=False),
            call("Customer", "ERP-C", "name", order_by=None, for_update=True, wait=False),
            call("HD Customer", "C", "*", as_dict=True, order_by=None, for_update=True, wait=False),
        ])
        self.rollback.assert_not_called()

    def test_correction_ownership_revision_and_reference_denials_precede_consistency(self):
        ticket, customer = self.ticket_customer_references()
        cases = (
            ("user", "foreign", BookingOwnershipError),
            ("modified", "2026-11-17T12:01:00", BookingOwnershipError),
            ("ticket", False, api.BookingReferenceDenied),
            ("customer", False, api.BookingReferenceDenied),
        )
        targets = {"ticket": ticket, "customer": customer}
        for field, value, error in cases:
            with self.subTest(field=field):
                change = (
                    patch.object(targets[field], "visible", value)
                    if field in targets else patch.dict(self.state, {field: value})
                )
                with (
                    change,
                    patch.object(api, "_validate_customer_consistency") as consistency,
                    self.assertRaises(error),
                ):
                    self.endpoint(customer_name="C")
                consistency.assert_not_called()
                self.rollback.assert_called_once_with()
        self.doc.save.assert_not_called()
        api.record_correction_event.assert_not_called()

    def test_committed_correction_replay_succeeds_after_customer_mapping_changes(self):
        from telephony.time_booking_correction_audit import _snapshot

        _ticket, customer = self.ticket_customer_references()
        result = self.endpoint(customer_name="C")

        self.assertEqual(self.f.db.sql.call_args_list[-2].args[1], ("ERP-C",))
        self.audit_row = dict(
            name=result["audit"], actor=self.identity.user, action=self.recorded["action"],
            reason=self.recorded["reason"], original_timesheet="TS-1",
            before_snapshot=_snapshot(self.recorded["before"]),
            after_snapshot=_snapshot(self.recorded["after"]),
        )
        stored_audit = copy.deepcopy(self.audit_row)
        stored_state = copy.deepcopy(self.state)
        stored_evidence = copy.deepcopy(self.recorded)
        customer["custom_erp_customer"] = "ERP-OTHER"
        self.current_customer["custom_erp_customer"] = "ERP-OTHER"
        self.f.get_doc.reset_mock()
        self.f.db.get_value.reset_mock()

        with patch.object(api, "_validate_customer_consistency") as consistency:
            self.assertEqual(self.endpoint(customer_name="C"), result)

        consistency.assert_not_called()
        self.f.db.get_value.assert_not_called()
        self.assertNotIn(
            ("Timesheet", "TS-1"), [call.args for call in self.f.get_doc.call_args_list],
        )
        self.doc.save.assert_called_once_with()
        api.record_correction_event.assert_called_once()
        self.assertEqual(self.state, stored_state)
        self.assertEqual(self.audit_row, stored_audit)
        self.assertEqual(self.recorded, stored_evidence)
        self.rollback.assert_not_called()

    def test_denied_replacement_references_leave_original_unchanged(self):
        for helper in ("_authorize_references", "_visible"):
            with patch.object(api, "_authorize_references"), patch.object(api, "_visible"), patch.object(
                api, helper, side_effect=PermissionError("denied")):
                with self.assertRaises(PermissionError): self.endpoint()
            self.doc.save.assert_not_called()
            self.assertFalse(hasattr(self, "recorded"))

    def test_native_and_audit_failures_restore_entire_request(self):
        self.doc.time_logs[0]["custom_hd_ticket"] = "T"
        original = copy.deepcopy(self.state)
        for failure in ("save", "audit", "delete"):
            with (
                patch.object(
                    api,
                    "_authorize_references",
                    return_value={"custom_service_area": "Routing"},
                ),
                patch.object(api, "_visible"),
                patch.object(
                    api,
                    "_allowed_service_areas",
                    return_value=("Other", "Routing", "Data Request"),
                ),
            ):
                if failure == "save": self.doc.save.side_effect = RuntimeError("overlap")
                if failure == "delete": self.doc.delete.side_effect = RuntimeError("linked")
                context = patch.object(api, "record_correction_event", side_effect=RuntimeError("audit")) if failure == "audit" else patch.object(api, "_identifier", wraps=api._identifier)
                with context:
                    with self.assertRaises(RuntimeError): self.endpoint(correction=failure != "delete")
            self.assertEqual(self.state, original)
            self.assertFalse(hasattr(self, "recorded"))
            self.rollback.assert_called_once()
            self.doc.save.side_effect = None; self.doc.delete.side_effect = None

    def test_correction_endpoint_rejects_missing_mandatory_metadata(self):
        from telephony.time_booking_metadata_policy import (
            BookingMetadataValidationError,
        )

        with (
            patch.object(
                api,
                "_authorize_references",
                return_value={"custom_service_area": "Routing"},
            ),
            patch.object(api, "_visible"),
            patch.object(
                api,
                "_allowed_service_areas",
                return_value=("Other", "Routing", "Data Request"),
            ),
        ):
            with self.assertRaises(
                BookingMetadataValidationError
            ):
                self.endpoint(
                    work_location=None,
                    work_origin=None,
                    emergency=None,
                )

        self.doc.save.assert_not_called()
        self.assertFalse(hasattr(self, "recorded"))

    def test_correction_can_keep_an_existing_blank_origin_but_cannot_clear_a_known_origin(self):
        for blank in (None, ""):
            row = {"custom_work_context": "Internal", "custom_work_origin": None}
            api._retain_blank_origin(row, {**row, "custom_work_origin": blank})
            self.assertEqual(row["custom_work_origin"], blank)

        for previous in (
            {"custom_work_context": "Internal", "custom_work_origin": "Snapfix"},
            {"custom_work_context": "Project", "custom_work_origin": None},
        ):
            with self.assertRaises(api.BookingMetadataValidationError):
                api._retain_blank_origin(
                    {"custom_work_context": "Internal", "custom_work_origin": None}, previous,
                )

    def test_correction_endpoint_accepts_valid_booking_metadata(self):
        self.doc.time_logs[0]["custom_hd_ticket"] = "T"
        with (
            patch.object(
                api,
                "_authorize_references",
                return_value={"custom_service_area": "Routing"},
            ),
            patch.object(api, "_visible"),
            patch.object(
                api,
                "_allowed_service_areas",
                return_value=("Other", "Routing", "Data Request"),
            ),
        ):
            result = self.endpoint(
                service_area=None,
                work_location="Remote",
                work_origin="Snapfix",
                external_reference="SF-123",
                other_origin_description=None,
                emergency=0,
            )

        self.assertEqual(
            result,
            {"timesheet": "TS-1", "audit": "AUDIT-1"},
        )

        self.doc.save.assert_called_once_with()

        row = self.recorded["after"]["time_logs"][0]

        expected = {
            "custom_work_context": "Helpdesk",
            "custom_service_area": "Routing",
            "custom_work_location": "Remote",
            "custom_work_origin": "Snapfix",
            "custom_external_reference": "SF-123",
            "custom_other_origin_description": None,
            "custom_emergency": 0,
        }

        for field, value in expected.items():
            with self.subTest(field=field):
                self.assertEqual(row.get(field), value)

        self.assertEqual(
            self.recorded["action"],
            "Draft Correction",
        )

    def test_correction_retry_accepts_empty_optional_metadata(self):
        from telephony.time_booking_correction_audit import _snapshot

        before = copy.deepcopy(self.state)
        after = copy.deepcopy(before)

        before["time_logs"][0].update({
            "custom_work_origin": "Direct / Ad-hoc",
            "custom_external_reference": None,
            "custom_other_origin_description": None,
        })

        after["time_logs"][0].update({
            "custom_work_origin": "Direct / Ad-hoc",
            "custom_external_reference": "",
            "custom_other_origin_description": "",
        })

        self.audit_row = dict(
            name="AUDIT-1",
            actor=self.identity.user,
            action="Draft Correction",
            reason="repair entry",
            original_timesheet="TS-1",
            before_snapshot=_snapshot(before),
            after_snapshot=_snapshot(after),
        )

        result = self.call(
            action="Draft Correction",
            values={
                "custom_work_origin": "Direct / Ad-hoc",
                "custom_external_reference": None,
                "custom_other_origin_description": None,
            },
        )

        self.assertEqual(
            result,
            {"timesheet": "TS-1", "audit": "AUDIT-1"},
        )

        # A successful retry must never repeat the mutation.
        self.doc.save.assert_not_called()
        self.doc.delete.assert_not_called()

    def test_correction_retry_rejects_changed_populated_metadata(self):
        from telephony.time_booking_correction_audit import _snapshot

        cases = (
            (
                "snapfix_reference_changed",
                "Snapfix",
                "custom_external_reference",
                "SF-456",
            ),
            (
                "snapfix_reference_cleared",
                "Snapfix",
                "custom_external_reference",
                None,
            ),
            (
                "other_description_changed",
                "Other",
                "custom_other_origin_description",
                "Different description",
            ),
            (
                "other_description_cleared",
                "Other",
                "custom_other_origin_description",
                "",
            ),
        )

        for label, origin, field, requested in cases:
            with self.subTest(case=label):
                before = copy.deepcopy(self.state)
                after = copy.deepcopy(before)

                after["time_logs"][0].update({
                    "custom_work_origin": origin,
                    "custom_external_reference": (
                        "SF-123" if origin == "Snapfix" else None
                    ),
                    "custom_other_origin_description": (
                        "Customer phone call"
                        if origin == "Other"
                        else None
                    ),
                })

                self.audit_row = dict(
                    name="AUDIT-1",
                    actor=self.identity.user,
                    action="Draft Correction",
                    reason="repair entry",
                    original_timesheet="TS-1",
                    before_snapshot=_snapshot(before),
                    after_snapshot=_snapshot(after),
                )

                with self.assertRaises(BookingOwnershipError):
                    self.call(
                        action="Draft Correction",
                        values={field: requested},
                    )

                self.doc.save.assert_not_called()
                self.doc.delete.assert_not_called()
                self.assertFalse(hasattr(self, "recorded"))

    def test_correction_retry_accepts_empty_internal_service_area(self):
        from telephony.time_booking_correction_audit import _snapshot

        before = copy.deepcopy(self.state)

        before["time_logs"][0].update({
            "custom_work_context": "Internal",
            "custom_hd_ticket": None,
            "custom_hd_customer": None,
            "project": None,
            "task": None,
            "custom_service_area": None,
        })

        after = copy.deepcopy(before)
        after["time_logs"][0]["custom_service_area"] = ""

        self.audit_row = dict(
            name="AUDIT-1",
            actor=self.identity.user,
            action="Draft Correction",
            reason="repair entry",
            original_timesheet="TS-1",
            before_snapshot=_snapshot(before),
            after_snapshot=_snapshot(after),
        )

        result = self.call(
            action="Draft Correction",
            values={"custom_service_area": None},
        )

        self.assertEqual(
            result,
            {"timesheet": "TS-1", "audit": "AUDIT-1"},
        )

        self.doc.save.assert_not_called()
        self.doc.delete.assert_not_called()

    def test_correction_retry_rejects_helpdesk_service_area_mismatch(self):
        from telephony.time_booking_correction_audit import _snapshot

        cases = (
            ("populated_area_cleared", "Routing", None),
            ("empty_helpdesk_area_not_equivalent", "", None),
        )

        for label, stored_area, requested_area in cases:
            with self.subTest(case=label):
                before = copy.deepcopy(self.state)
                after = copy.deepcopy(before)

                after["time_logs"][0].update({
                    "custom_work_context": "Helpdesk",
                    "custom_service_area": stored_area,
                })

                self.audit_row = dict(
                    name="AUDIT-1",
                    actor=self.identity.user,
                    action="Draft Correction",
                    reason="repair entry",
                    original_timesheet="TS-1",
                    before_snapshot=_snapshot(before),
                    after_snapshot=_snapshot(after),
                )

                with self.assertRaises(BookingOwnershipError):
                    self.call(
                        action="Draft Correction",
                        values={
                            "custom_service_area": requested_area,
                        },
                    )

                self.doc.save.assert_not_called()
                self.doc.delete.assert_not_called()
                self.assertFalse(hasattr(self, "recorded"))

    def test_correction_endpoint_accepts_unlisted_customer_support_identity(self):
        with (
            patch.object(
                api,
                "_authorize_references",
                return_value=None,
            ),
            patch.object(api, "_visible"),
            patch.object(
                api,
                "_allowed_service_areas",
                return_value=("Other", "Routing", "Data Request"),
            ),
        ):
            result = self.endpoint(
                work_context="Customer Support",
                ticket_name=None,
                project_name=None,
                task_name=None,
                customer_name=None,
                unlisted_customer_name="Walk-in Customer",
                service_area="Other",
                work_location="Remote",
                work_origin="Direct / Ad-hoc",
                external_reference=None,
                other_origin_description=None,
                emergency=0,
            )

        self.assertEqual(
            result,
            {"timesheet": "TS-1", "audit": "AUDIT-1"},
        )

        self.doc.save.assert_called_once_with()

        row = self.recorded["after"]["time_logs"][0]

        self.assertEqual(
            row["custom_work_context"],
            "Customer Support",
        )
        self.assertIsNone(row["custom_hd_customer"])
        self.assertEqual(
            row["custom_unlisted_customer_name"],
            "Walk-in Customer",
        )
        self.assertEqual(row["custom_service_area"], "Other")

    def test_correction_endpoint_rejects_invalid_customer_identities(self):
        from telephony.time_booking_policy import WorkContextValidationError

        cases = (
            (
                "both_identities",
                "Customer Support",
                "HD-CUST-1",
                "Walk-in Customer",
            ),
            (
                "neither_identity",
                "Customer Support",
                None,
                None,
            ),
            (
                "whitespace_only_unlisted",
                "Customer Support",
                None,
                "   ",
            ),
            (
                "unlisted_name_in_internal",
                "Internal",
                None,
                "Walk-in Customer",
            ),
        )

        for label, context, customer, unlisted in cases:
            with self.subTest(case=label):
                with (
                    patch.object(
                        api,
                        "_authorize_references",
                        return_value=None,
                    ),
                    patch.object(api, "_visible"),
                    patch.object(
                        api,
                        "_allowed_service_areas",
                        return_value=("Other", "Routing", "Data Request"),
                    ),
                ):
                    with self.assertRaises(WorkContextValidationError):
                        self.endpoint(
                            work_context=context,
                            ticket_name=None,
                            project_name=None,
                            task_name=None,
                            customer_name=customer,
                            unlisted_customer_name=unlisted,
                            service_area=(
                                None if context == "Internal" else "Other"
                            ),
                            work_location="Remote",
                            work_origin="Direct / Ad-hoc",
                            external_reference=None,
                            other_origin_description=None,
                            emergency=0,
                        )

                self.doc.save.assert_not_called()
                self.doc.delete.assert_not_called()
                self.assertFalse(hasattr(self, "recorded"))

    def test_correction_retry_accepts_empty_unlisted_customer_name(self):
        from telephony.time_booking_correction_audit import _snapshot

        before = copy.deepcopy(self.state)

        before["time_logs"][0]["custom_unlisted_customer_name"] = None

        after = copy.deepcopy(before)
        after["time_logs"][0]["custom_unlisted_customer_name"] = ""

        self.audit_row = dict(
            name="AUDIT-1",
            actor=self.identity.user,
            action="Draft Correction",
            reason="repair entry",
            original_timesheet="TS-1",
            before_snapshot=_snapshot(before),
            after_snapshot=_snapshot(after),
        )

        result = self.call(
            action="Draft Correction",
            values={
                "custom_unlisted_customer_name": None,
            },
        )

        self.assertEqual(
            result,
            {"timesheet": "TS-1", "audit": "AUDIT-1"},
        )

        self.doc.save.assert_not_called()
        self.doc.delete.assert_not_called()

    def test_correction_retry_rejects_changed_unlisted_customer_name(self):
        from telephony.time_booking_correction_audit import _snapshot

        cases = (
            ("name_changed", "Another Customer"),
            ("name_cleared_none", None),
            ("name_cleared_empty", ""),
        )

        for label, requested_name in cases:
            with self.subTest(case=label):
                before = copy.deepcopy(self.state)

                before["time_logs"][0].update({
                    "custom_work_context": "Customer Support",
                    "custom_hd_ticket": None,
                    "custom_hd_customer": None,
                    "custom_unlisted_customer_name": "Walk-in Customer",
                    "project": None,
                    "task": None,
                })

                after = copy.deepcopy(before)

                self.audit_row = dict(
                    name="AUDIT-1",
                    actor=self.identity.user,
                    action="Draft Correction",
                    reason="repair entry",
                    original_timesheet="TS-1",
                    before_snapshot=_snapshot(before),
                    after_snapshot=_snapshot(after),
                )

                with self.assertRaises(BookingOwnershipError):
                    self.call(
                        action="Draft Correction",
                        values={
                            "custom_unlisted_customer_name": requested_name,
                        },
                    )

                self.doc.save.assert_not_called()
                self.doc.delete.assert_not_called()
                self.assertFalse(hasattr(self, "recorded"))


class TestBookingHttpErrors(unittest.TestCase):
    def invoke(self, error, request=None):
        @time_booking._booking_http_errors
        def fail():
            raise error

        local = types.SimpleNamespace(request=request)
        with patch.object(time_booking, "frappe", types.SimpleNamespace(local=local, _=lambda text: text)):
            return fail()

    def test_owned_creation_boundary_returns_safe_json(self):
        response = self.invoke(
            time_booking.OriginalBookingCreationExceeded("Internal timestamp"), Request.from_values(method="POST"),
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(json.loads(response.data), {
            "error": {
                "code": "original_creation_exceeded",
                "message": "The corrected work must end on or before the original booking creation time. "
                           "Please adjust the start time or duration.",
            },
        })

    def test_restricted_lifecycle_error_has_its_own_generic_response(self):
        response = self.invoke(time_booking.SavedTicketIntervalDenied("Protected Ticket details"), Request.from_values())
        self.assertEqual(response.status_code, 422)
        self.assertEqual(json.loads(response.data)["error"]["code"], "invalid_ticket_interval")
        self.assertNotIn(b"Protected Ticket details", response.data)

    def test_reference_denial_stays_forbidden(self):
        response = self.invoke(time_booking.BookingReferenceDenied("Protected Ticket details"), Request.from_values())
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(b"Protected Ticket details", response.data)

    def test_unexpected_and_non_http_exceptions_propagate(self):
        with self.assertRaisesRegex(RuntimeError, "unexpected"):
            self.invoke(RuntimeError("unexpected"), Request.from_values())
        with self.assertRaises(time_booking.OriginalBookingCreationExceeded):
            self.invoke(time_booking.OriginalBookingCreationExceeded())

    def test_internal_permission_messages_preserve_outer_message_log(self):
        messages = ["outer message"]
        local = types.SimpleNamespace(message_log=messages)
        with patch.object(time_booking, "frappe", types.SimpleNamespace(local=local)):
            with self.assertRaisesRegex(RuntimeError, "unexpected"):
                with time_booking._discard_internal_permission_messages():
                    local.message_log.append("internal Ticket message")
                    raise RuntimeError("unexpected")
        self.assertIs(local.message_log, messages)
        self.assertEqual(messages, ["outer message"])
