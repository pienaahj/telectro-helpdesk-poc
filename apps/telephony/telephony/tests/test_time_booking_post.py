"""No-site tests of the dedicated booking API boundary."""

from contextlib import contextmanager
from datetime import datetime
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

from telephony.tests.test_time_booking_correction_audit import snapshot
from telephony.time_booking_activity_types import BOOKING_ACTIVITY_TYPES
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
            ("HD Ticket", "T"): Reference("HD Ticket", "T", status="Closed", custom_service_area="Routing"),
            ("Project", "P"): Reference("Project", "P", company="Company A"),
            ("Task", "K"): Reference("Task", "K", project="P"),
            ("HD Customer", "C"): Reference("HD Customer", "C"),
            ("Activity Type", "Execution"): Reference("Activity Type", "Execution"),
            ("Activity Type", "Repair & Maintenance"): Reference("Activity Type", "Repair & Maintenance"),
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
        self.area_field = types.SimpleNamespace(
            fieldtype="Select",
            options=(
                "\nOther\nRouting\nPABX\nSIM\nInternet Connection"
                "\nFaults\nQuotes & Site Surveys\nCCTV\nData Request"
            ),
        )

        def get_meta(doctype):
            if doctype != "HD Ticket":
                raise AssertionError(f"Unexpected metadata request: {doctype}")

            return types.SimpleNamespace(
                get_field=lambda name: (
                    self.area_field
                    if name == "custom_service_area"
                    else None
                ),
            )

        self.f.get_meta = get_meta
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
        args = dict(
            work_context="Helpdesk",
            from_time="2026-11-16 09:00:00",
            duration_minutes=90,
            description="Repair",
            activity_type="Repair & Maintenance",
            ticket_name="T",
            service_area="Routing",
            work_location="Remote",
            work_origin="Direct / Ad-hoc",
            external_reference=None,
            other_origin_description=None,
            emergency=0,
        )
        args.update(updates)
        return self.m.book_technician_time(**args)

    def test_booking_form_returns_ordered_catalog_for_eligible_technician(self):
        response = self.m.get_booking_form()

        self.assertEqual(response["activity_types"], BOOKING_ACTIVITY_TYPES)
        self.assertEqual(response["service_areas"], self.m._allowed_service_areas())

    def test_booking_form_does_not_disclose_catalog_when_ineligible(self):
        for mode in ("disabled", "invalid runtime", "ineligible identity"):
            with self.subTest(mode=mode), patch.object(self.m, "_allowed_service_areas") as areas:
                self.f.conf["telectro_time_booking_enabled"] = mode != "disabled"
                self.m._require_activation_configuration.side_effect = (
                    ActivationConfigurationError if mode == "invalid runtime" else None
                )
                self.m.resolve_current_technician_identity.side_effect = (
                    TechnicianIdentityError if mode == "ineligible identity" else None
                )

                self.assertIsNone(self.m.get_booking_form())
                areas.assert_not_called()

    def test_creation_rejects_readable_execution_and_accepts_approved_activity(self):
        self.refs["Activity Type", "Execution"].check_permission("read")

        with self.assertRaises(self.m.BookingInputError):
            self.call(activity_type="Execution")
        self.assertEqual(self.db.writes, [])

        self.call(activity_type="Repair & Maintenance")
        self.assertEqual(self.db.writes[0].time_logs[0]["activity_type"], "Repair & Maintenance")

    def test_creation_still_requires_read_permission_for_approved_activity(self):
        self.refs["Activity Type", "Repair & Maintenance"].visible = False

        with self.assertRaises(self.m.BookingReferenceDenied):
            self.call()
        self.assertEqual(self.db.writes, [])

    def test_own_booking_history_keeps_historical_activity_type(self):
        class Row(dict):
            def __getattr__(self, key):
                return self.get(key)

        parent = snapshot()
        parent["user"] = self.identity.user
        row = Row(parent["time_logs"][0], activity_type="Execution")
        parent["time_logs"] = [row]
        doc = types.SimpleNamespace(
            name=parent["name"],
            docstatus=parent["docstatus"],
            modified="2026-11-17 12:00:00",
            time_logs=[row],
            as_dict=lambda: Row(parent),
        )
        self.f.get_all = Mock(return_value=[doc.name])
        self.f.get_doc = Mock(return_value=doc)

        response = self.m.list_own_bookings()

        self.assertEqual(len(response["bookings"]), 1)
        self.assertEqual(response["bookings"][0]["activity_type"], "Execution")

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

    def test_helpdesk_service_area_comes_from_ticket(self):
        ticket = self.refs[("HD Ticket", "T")]
        ticket["custom_service_area"] = "PABX"

        result = self.call(
            service_area=None,
            work_location="Remote",
            work_origin="Direct / Ad-hoc",
            external_reference=None,
            other_origin_description=None,
            emergency=0,
        )

        self.assertEqual(result, {"timesheet": "TS-001"})
        self.assertEqual(len(self.db.writes), 1)

        row = self.db.writes[0].time_logs[0]

        self.assertEqual(row["custom_service_area"], "PABX")
        self.assertEqual(row["custom_work_location"], "Remote")
        self.assertEqual(row["custom_work_origin"], "Direct / Ad-hoc")
        self.assertEqual(row["custom_emergency"], 0)

    def test_helpdesk_rejects_conflicting_service_area(self):
        ticket = self.refs[("HD Ticket", "T")]
        ticket["custom_service_area"] = "PABX"

        with self.assertRaises(
            self.m.BookingMetadataValidationError
        ) as caught:
            self.call(
                service_area="Routing",
            )

        self.assertEqual(
            str(caught.exception),
            "Helpdesk Service Area must match its ticket",
        )

        self.assertEqual(self.db.writes, [])
        self.assertEqual(self.intent_documents, [])

    def test_helpdesk_rejects_invalid_ticket_service_area(self):
        ticket = self.refs[("HD Ticket", "T")]

        for invalid_area in (None, "", "Unknown Area"):
            with self.subTest(ticket_area=invalid_area):
                ticket["custom_service_area"] = invalid_area

                with self.assertRaises(
                    self.m.BookingMetadataValidationError
                ):
                    self.call(service_area=None)

                self.assertEqual(self.db.writes, [])
                self.assertEqual(self.intent_documents, [])

    def test_creation_rejects_missing_mandatory_metadata(self):
        invalid_cases = (
            ("missing_location", {"work_location": None}),
            ("empty_location", {"work_location": ""}),
            ("missing_origin", {"work_origin": None}),
            ("empty_origin", {"work_origin": ""}),
            ("missing_emergency", {"emergency": None}),
        )

        for label, updates in invalid_cases:
            with self.subTest(case=label):
                with self.assertRaises(
                    self.m.BookingMetadataValidationError
                ):
                    self.call(**updates)

                self.assertEqual(self.db.writes, [])
                self.assertEqual(self.intent_documents, [])

    def test_creation_rejects_invalid_work_origin_metadata(self):
        invalid_cases = (
            (
                "snapfix_missing_reference",
                {
                    "work_origin": "Snapfix",
                    "external_reference": None,
                },
            ),
            (
                "snapfix_stale_other_description",
                {
                    "work_origin": "Snapfix",
                    "external_reference": "SF-123",
                    "other_origin_description": "Old description",
                },
            ),
            (
                "other_missing_description",
                {
                    "work_origin": "Other",
                    "other_origin_description": None,
                },
            ),
            (
                "other_stale_external_reference",
                {
                    "work_origin": "Other",
                    "other_origin_description": "Customer phone call",
                    "external_reference": "SF-123",
                },
            ),
            (
                "direct_stale_external_reference",
                {
                    "work_origin": "Direct / Ad-hoc",
                    "external_reference": "SF-123",
                },
            ),
            (
                "direct_stale_other_description",
                {
                    "work_origin": "Direct / Ad-hoc",
                    "other_origin_description": "Old description",
                },
            ),
        )

        for label, updates in invalid_cases:
            with self.subTest(case=label):
                with self.assertRaises(
                    self.m.BookingMetadataValidationError
                ):
                    self.call(**updates)

                self.assertEqual(self.db.writes, [])
                self.assertEqual(self.intent_documents, [])
    def test_creation_accepts_valid_snapfix_and_other_origins(self):
        cases = (
            (
                "Snapfix",
                {
                    "work_origin": "Snapfix",
                    "external_reference": "SF-123",
                    "other_origin_description": None,
                },
                "SF-123",
                None,
            ),
            (
                "Other",
                {
                    "work_origin": "Other",
                    "external_reference": None,
                    "other_origin_description": "Customer phone call",
                },
                None,
                "Customer phone call",
            ),
        )

        for origin, updates, reference, description in cases:
            with self.subTest(origin=origin):
                previous_writes = len(self.db.writes)

                result = self.call(**updates)

                self.assertEqual(result, {"timesheet": "TS-001"})
                self.assertEqual(
                    len(self.db.writes),
                    previous_writes + 1,
                )

                row = self.db.writes[-1].time_logs[0]

                self.assertEqual(row["custom_work_origin"], origin)
                self.assertEqual(
                    row["custom_external_reference"],
                    reference,
                )
                self.assertEqual(
                    row["custom_other_origin_description"],
                    description,
                )
                self.assertEqual(row["custom_emergency"], 0)

    def test_creation_rejects_invalid_service_area_configuration(self):
        invalid_cases = (
            ("wrong_field_type", "Data", "\nOther\nRouting"),
            ("missing_options", "Select", None),
            ("empty_options", "Select", "\n"),
            ("duplicate_options", "Select", "\nRouting\nRouting"),
        )

        original_type = self.area_field.fieldtype
        original_options = self.area_field.options

        try:
            for label, fieldtype, options in invalid_cases:
                with self.subTest(case=label):
                    self.area_field.fieldtype = fieldtype
                    self.area_field.options = options

                    with self.assertRaises(
                        self.m.BookingMetadataValidationError
                    ):
                        self.call()

                    self.assertEqual(self.db.writes, [])
                    self.assertEqual(self.intent_documents, [])
        finally:
            self.area_field.fieldtype = original_type
            self.area_field.options = original_options

    def test_creation_enforces_travel_work_location_exception(self):
        self.refs[("Activity Type", "Travel")] = Reference(
            "Activity Type", "Travel"
        )

        # Travel must reject an explicitly selected Work Location.
        with self.assertRaises(
            self.m.BookingMetadataValidationError
        ):
            self.call(
                activity_type="Travel",
                work_location="On-site",
            )

        self.assertEqual(self.db.writes, [])
        self.assertEqual(self.intent_documents, [])

        # Travel with no Work Location is valid.
        result = self.call(
            activity_type="Travel",
            work_location=None,
        )

        self.assertEqual(result, {"timesheet": "TS-001"})
        self.assertEqual(len(self.db.writes), 1)

        row = self.db.writes[0].time_logs[0]

        self.assertEqual(row["activity_type"], "Travel")
        self.assertIsNone(row["custom_work_location"])
        self.assertEqual(row["custom_work_origin"], "Direct / Ad-hoc")
        self.assertEqual(row["custom_emergency"], 0)

    def test_helpdesk_accepts_canonical_numeric_ticket_name(self):
        ticket = Reference(
            "HD Ticket",
            "965",
            status="Closed",
            custom_service_area="Data Request",
        )

        # Simulate the actual Frappe document representation.
        ticket.name = 965

        self.refs[("HD Ticket", "965")] = ticket

        result = self.call(
            ticket_name="965",
            service_area=None,
        )

        self.assertEqual(result, {"timesheet": "TS-001"})
        self.assertEqual(len(self.db.writes), 1)

        row = self.db.writes[0].time_logs[0]

        self.assertEqual(row["custom_hd_ticket"], "965")
        self.assertEqual(row["custom_service_area"], "Data Request")

    def test_helpdesk_rejects_noncanonical_numeric_ticket_names(self):
        invalid_names = (
            "0965",
            "965.0",
            "+965",
            " 965",
            "965 ",
        )

        for requested_name in invalid_names:
            with self.subTest(requested_name=requested_name):
                ticket = Reference(
                    "HD Ticket",
                    requested_name,
                    status="Closed",
                    custom_service_area="Data Request",
                )

                # Simulate Frappe returning the integer identity.
                ticket.name = 965

                self.refs[("HD Ticket", requested_name)] = ticket

                with self.assertRaises(
                    self.m.BookingReferenceDenied
                ):
                    self.call(
                        ticket_name=requested_name,
                        service_area=None,
                    )

                self.assertEqual(self.db.writes, [])
                self.assertEqual(self.intent_documents, [])
