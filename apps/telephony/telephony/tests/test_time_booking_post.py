"""No-site tests of the dedicated booking API boundary."""

from contextlib import contextmanager
from datetime import datetime
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

from telephony.time_booking_activation_policy import ActivationConfigurationError
from telephony.time_booking_identity import TechnicianBookingIdentity, TechnicianIdentityError
from telephony import time_booking_provenance_adapter, time_booking_timesheet_controller


class Reference(dict):
    def __init__(self, doctype, name, **values):
        super().__init__(values)
        self.doctype, self.name = doctype, name
        self.visible = True
    def check_permission(self, permission):
        if not self.visible:
            raise PermissionError()


class FakeTimesheet(dict):
    def __init__(self, values, db):
        super().__init__(values)
        self.time_logs = values["time_logs"]
        self.name = None
        self.db = db
        self.flags = types.SimpleNamespace(
            ignore_permissions=False
        )
    def insert(self):
        self.db.writes.append(self)
        if self.db.fail_insert:
            raise RuntimeError("native validation failed")
        self.name = "TS-001"
        self["name"] = self.name
        self["owner"] = self["user"]
        return self


class Database:
    def __init__(self):
        self.writes = []
        self.fail_insert = False
        self.rollback_count = 0
    def rollback(self):
        self.rollback_count += 1
        self.writes.clear()


class TestBookingPost(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.refs = {
            ("HD Ticket", "T"): Reference("HD Ticket", "T", status="Closed"),
            ("Project", "P"): Reference("Project", "P", company="Company A"),
            ("Task", "K"): Reference("Task", "K", project="P"),
            ("HD Customer", "C"): Reference("HD Customer", "C"),
            ("Activity Type", "Service"): Reference("Activity Type", "Service"),
        }
        self.f = types.ModuleType("frappe")
        self.f.whitelist = lambda **kwargs: lambda fn: fn
        self.f.DoesNotExistError = LookupError
        self.f.PermissionError = PermissionError
        self.f.conf = {"telectro_time_booking_enabled": 1}
        self.f.session = types.SimpleNamespace(user="tech")
        self.f.utils = types.SimpleNamespace(now_datetime=lambda: datetime(2026, 11, 17, 12))
        self.f.local = types.SimpleNamespace(
            request=types.SimpleNamespace(method="POST", path="/api/method/telephony.api.time_booking.book_technician_time"),
            form_dict=types.SimpleNamespace(cmd="telephony.api.time_booking.book_technician_time"),
            db=self.db,
        )
        self.f.get_doc = self.get_doc
        module_patch = patch.dict(sys.modules, {"frappe": self.f})
        module_patch.start(); self.addCleanup(module_patch.stop)
        path = Path(__file__).resolve().parents[1] / "api/time_booking.py"
        spec = importlib.util.spec_from_file_location("booking_post_test", path)
        self.m = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.m)
        self.m.TelectroBookingTimesheet = FakeTimesheet
        self.identity = TechnicianBookingIdentity("tech", "EMP-1", "Company A")
        self.m.resolve_current_technician_identity = Mock(return_value=self.identity)
        self.m._require_activation_configuration = Mock()
        self.intent_documents = []
        @contextmanager
        def intent(doc, identity):
            self.intent_documents.append((doc, identity))
            yield
        self.m._phase2_creation_intent = intent

    def get_doc(self, *args):
        if isinstance(args[0], dict):
            return FakeTimesheet(args[0], self.db)
        try:
            return self.refs[args]
        except KeyError as exc:
            raise LookupError() from exc

    def call(self, **updates):
        args = dict(work_context="Helpdesk", from_time="2026-11-16 09:00:00",
                    duration_minutes=90, description="Repair", activity_type="Service",
                    ticket_name="T")
        args.update(updates)
        return self.m.book_technician_time(**args)

    def test_terminal_ticket_retrospective_booking(self):
        self.assertEqual(self.call(), {"timesheet": "TS-001"})
        doc = self.db.writes[0]
        self.assertEqual(len(self.db.writes), 1)
        self.assertEqual(len(doc.time_logs), 1)
        self.assertEqual(doc["employee"], "EMP-1")
        self.assertEqual(doc["company"], "Company A")
        self.assertEqual(doc["user"], "tech")
        self.assertEqual(doc.time_logs[0]["hours"], 1.5)
        self.assertEqual(self.intent_documents[0][1], self.identity)
        self.m._require_activation_configuration.assert_called_once()

    def test_http_string_duration_is_accepted(self):
        self.assertEqual(self.call(duration_minutes="90"), {"timesheet": "TS-001"})
        self.assertEqual(self.db.writes[0].time_logs[0]["hours"], 1.5)

    def test_project_booking(self):
        self.assertEqual(self.call(work_context="Project", ticket_name=None, project_name="P"),
                         {"timesheet": "TS-001"})

    def test_task_booking_checks_project_membership(self):
        self.assertEqual(self.call(work_context="Project", ticket_name=None,
                                   project_name="P", task_name="K"), {"timesheet": "TS-001"})
        self.refs[("Task", "K")]["project"] = "other"
        with self.assertRaises(self.m.BookingReferenceDenied):
            self.call(work_context="Project", ticket_name=None, project_name="P", task_name="K")

    def test_customer_support_and_internal_contexts(self):
        self.assertEqual(self.call(work_context="Customer Support", ticket_name=None,
                                   customer_name="C"), {"timesheet": "TS-001"})
        self.assertEqual(self.call(work_context="Internal", ticket_name=None),
                         {"timesheet": "TS-001"})

    def test_nonexistent_and_hidden_references_denied_without_leak(self):
        for ticket in ("missing", "T"):
            if ticket == "T": self.refs[("HD Ticket", "T")].visible = False
            with self.subTest(ticket=ticket):
                with self.assertRaises(self.m.BookingReferenceDenied) as caught:
                    self.call(ticket_name=ticket)
                self.assertEqual(str(caught.exception), "Booking reference is unavailable.")
                self.assertEqual(self.db.writes, [])

    def test_wrong_company_or_hidden_project_or_task_denied(self):
        self.refs[("Project", "P")]["company"] = "Other"
        with self.assertRaises(self.m.BookingReferenceDenied):
            self.call(work_context="Project", ticket_name=None, project_name="P")
        self.refs[("Project", "P")]["company"] = "Company A"
        self.refs[("Project", "P")].visible = False
        with self.assertRaises(self.m.BookingReferenceDenied):
            self.call(work_context="Project", ticket_name=None, project_name="P")
        self.refs[("Project", "P")].visible = True
        self.refs[("Task", "K")].visible = False
        with self.assertRaises(self.m.BookingReferenceDenied):
            self.call(work_context="Project", ticket_name=None, project_name="P", task_name="K")

    def test_bad_context_and_mixed_references_denied(self):
        for updates in ({"work_context": "Unknown"}, {"project_name": "P"},
                        {"work_context": "Project", "project_name": "P"}):
            with self.subTest(updates=updates):
                with self.assertRaises(ValueError): self.call(**updates)
        self.assertEqual(self.db.writes, [])

    def test_bad_time_duration_description_and_activity_denied(self):
        for updates in ({"from_time": "bad"}, {"from_time": "2026-11-16"},
                        {"from_time": "2026-11-18 09:00:00"},
                        {"duration_minutes": 0}, {"duration_minutes": -1},
                        {"duration_minutes": True}, {"duration_minutes": 1441},
                        {"duration_minutes": "090"}, {"duration_minutes": "9.5"},
                        {"description": " "}, {"activity_type": "missing"}):
            with self.subTest(updates=updates):
                with self.assertRaises((self.m.BookingInputError, self.m.BookingReferenceDenied)):
                    self.call(**updates)
        self.assertEqual(self.db.writes, [])

    def test_guest_method_and_command_denied_before_activation(self):
        for user, method, command in (("Guest", "POST", self.m.COMMAND),
                                      ("tech", "GET", self.m.COMMAND),
                                      ("tech", "POST", "other")):
            self.f.session.user = user
            self.f.local.request.method = method
            self.f.local.form_dict.cmd = command
            with self.assertRaises(PermissionError): self.call()
            self.m._require_activation_configuration.assert_not_called()
        self.assertEqual(self.db.writes, [])

    def test_disabled_and_incomplete_activation_denied_before_identity(self):
        self.f.conf.clear()
        with self.assertRaises(ActivationConfigurationError): self.call()
        self.m.resolve_current_technician_identity.assert_not_called()
        self.f.conf["telectro_time_booking_enabled"] = 1
        self.m._require_activation_configuration.side_effect = ActivationConfigurationError()
        with self.assertRaises(ActivationConfigurationError): self.call()
        self.m.resolve_current_technician_identity.assert_not_called()
        self.assertEqual(self.db.writes, [])

    def test_identity_failure_denies_partner_customer_disabled_or_bad_employee(self):
        for label in ("partner", "customer", "disabled", "employee"):
            with self.subTest(label=label):
                self.m.resolve_current_technician_identity.side_effect = TechnicianIdentityError()
                with self.assertRaises(TechnicianIdentityError): self.call()
                self.assertEqual(self.db.writes, [])

    def test_insert_failure_rolls_back_full_request(self):
        self.db.fail_insert = True

        observed = []
        original_insert = FakeTimesheet.insert

        def observed_insert(doc):
            observed.append(doc)

            # Native insertion must execute inside the
            # temporary document permission scope.
            self.assertIs(doc.flags.ignore_permissions, True)

            return original_insert(doc)

        with patch.object(FakeTimesheet, "insert", observed_insert):
            with self.assertRaisesRegex(
                RuntimeError, "native validation failed"
            ):
                self.call()

        self.assertEqual(len(observed), 1)

        # The document must not remain elevated after failure.
        self.assertIs(
            observed[0].flags.ignore_permissions,
            False,
        )

        # Existing full-request rollback protection remains intact.
        self.assertEqual(self.db.rollback_count, 1)
        self.assertEqual(self.db.writes, [])

    def test_wrong_controller_or_owner_fails_closed(self):
        class Wrong(dict):
            pass
        original = self.f.get_doc
        self.f.get_doc = lambda *args: Wrong() if isinstance(args[0], dict) else original(*args)
        with self.assertRaises(ActivationConfigurationError): self.call()
        self.assertEqual(self.db.writes, [])

    def test_managed_creation_uses_temporary_document_permission_scope(self):
        class RestrictedTimesheet(FakeTimesheet):
            def __init__(self, values, db):
                super().__init__(values, db)
                self.flags = types.SimpleNamespace(
                    ignore_permissions=False
                )
                self.elevated_during_insert = False

            def insert(self):
                self.elevated_during_insert = (
                    self.flags.ignore_permissions is True
                )

                if not self.elevated_during_insert:
                    raise PermissionError(
                        "Native Timesheet create permission denied"
                    )

                return super().insert()

        original_get_doc = self.f.get_doc

        def get_doc(*args):
            if (
                isinstance(args[0], dict)
                and args[0].get("doctype") == "Timesheet"
            ):
                return RestrictedTimesheet(args[0], self.db)

            return original_get_doc(*args)

        self.f.get_doc = get_doc
        self.m.TelectroBookingTimesheet = RestrictedTimesheet

        result = self.call()

        self.assertEqual(result, {"timesheet": "TS-001"})
        self.assertEqual(len(self.db.writes), 1)

        doc = self.db.writes[0]

        # Native insertion must run with temporary permission elevation.
        self.assertTrue(doc.elevated_during_insert)

        # The permission override must not survive insertion.
        self.assertIs(doc.flags.ignore_permissions, False)

        # Existing managed creation authority remains required.
        self.assertEqual(len(self.intent_documents), 1)
        self.assertIs(self.intent_documents[0][0], doc)
        self.assertIs(self.intent_documents[0][1], self.identity)

        self.assertEqual(self.db.rollback_count, 0)

    def test_pre_elevated_timesheet_is_rejected_before_insert(self):
        original_get_doc = self.f.get_doc
        created = []

        def get_doc(*args):
            doc = original_get_doc(*args)

            if isinstance(args[0], dict):
                doc.flags.ignore_permissions = True
                created.append(doc)

            return doc

        self.f.get_doc = get_doc

        with self.assertRaises(ActivationConfigurationError):
            self.call()

        # Exactly one Timesheet was constructed.
        self.assertEqual(len(created), 1)

        # The pre-existing elevated state is not silently modified.
        self.assertIs(
            created[0].flags.ignore_permissions,
            True,
        )

        # Native insertion must never execute.
        self.assertEqual(self.db.writes, [])

        # The surrounding request must abort.
        self.assertEqual(self.db.rollback_count, 1)

    def test_helpdesk_hidden_optional_customer_denied_without_write(self):
        self.refs[("HD Customer", "C")].visible = False

        with self.assertRaises(
            self.m.BookingReferenceDenied
        ) as caught:
            self.call(customer_name="C")

        self.assertEqual(
            str(caught.exception),
            "Booking reference is unavailable.",
        )
        self.assertEqual(self.db.writes, [])

    def test_project_hidden_optional_customer_denied_without_write(self):
        self.refs[("HD Customer", "C")].visible = False

        with self.assertRaises(
            self.m.BookingReferenceDenied
        ) as caught:
            self.call(
                work_context="Project",
                ticket_name=None,
                project_name="P",
                customer_name="C",
            )

        self.assertEqual(
            str(caught.exception),
            "Booking reference is unavailable.",
        )
        self.assertEqual(self.db.writes, [])

    def test_customer_support_unlisted_identity_booking(self):
        result = self.call(
            work_context="Customer Support",
            ticket_name=None,
            customer_name=None,
            unlisted_customer_name="Walk-in customer",
        )

        self.assertEqual(result, {"timesheet": "TS-001"})
        self.assertEqual(len(self.db.writes), 1)

        row = self.db.writes[0].time_logs[0]

        self.assertEqual(
            row["custom_work_context"],
            "Customer Support",
        )
        self.assertIsNone(row["custom_hd_customer"])
        self.assertEqual(
            row["custom_unlisted_customer_name"],
            "Walk-in customer",
        )

    def test_customer_support_requires_exactly_one_identity(self):
        invalid_cases = (
            {
                "customer_name": None,
                "unlisted_customer_name": None,
            },
            {
                "customer_name": "C",
                "unlisted_customer_name": "Walk-in customer",
            },
        )

        for identity in invalid_cases:
            with self.subTest(identity=identity):
                with self.assertRaises(ValueError):
                    self.call(
                        work_context="Customer Support",
                        ticket_name=None,
                        **identity,
                    )

        self.assertEqual(self.db.writes, [])

    def test_customer_support_rejects_invalid_unlisted_names(self):
        invalid_names = (
            "",
            "   ",
            0,
            False,
            [],
            {},
        )

        for name in invalid_names:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.call(
                        work_context="Customer Support",
                        ticket_name=None,
                        customer_name=None,
                        unlisted_customer_name=name,
                    )

                self.assertEqual(self.db.writes, [])

    def test_customer_support_hidden_existing_customer_denied(self):
        self.refs[("HD Customer", "C")].visible = False

        with self.assertRaises(
            self.m.BookingReferenceDenied
        ) as caught:
            self.call(
                work_context="Customer Support",
                ticket_name=None,
                customer_name="C",
                unlisted_customer_name=None,
            )

        self.assertEqual(
            str(caught.exception),
            "Booking reference is unavailable.",
        )
        self.assertEqual(self.db.writes, [])

    def test_creation_endpoint_remains_post_whitelisted(self):
        import ast
        from pathlib import Path

        source = Path(self.m.__file__).read_text(encoding="utf-8")
        module = ast.parse(source)

        definitions = [
            node
            for node in module.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "book_technician_time"
        ]

        self.assertEqual(len(definitions), 1)

        expected = ast.parse(
            'frappe.whitelist(methods=["POST"])',
            mode="eval",
        ).body

        actual = [
            ast.dump(decorator, include_attributes=False)
            for decorator in definitions[0].decorator_list
        ]

        self.assertIn(
            ast.dump(expected, include_attributes=False),
            actual,
        )
