"""Exercise origin policy and native entry points with writes replaced by a test transaction."""

from contextvars import copy_context
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import frappe
from frappe import client
from frappe.core.doctype.data_import.importer import Importer
from frappe.desk.form import save as desk_save
from frappe.email.receive import InboundMail
from frappe.model.document import Document
from helpdesk.helpdesk.doctype.hd_ticket import api as helpdesk_api

from telephony import hd_ticket_manual_origin as origin


TECH = "TELECTRO-POC Role - Tech"


class Ticket:
    def __init__(self, harness, values):
        self.harness = harness
        self.values = dict(values)
        self.meta = harness.meta
        self.flags = frappe._dict()
        self.name = values.get("name")
        self.doctype = values["doctype"]
        self.sla = None
        self.modified = None
        self.modified_by = None
        self.previous = None

    def __deepcopy__(self, memo):
        return Ticket(self.harness, self.values)

    def as_dict(self):
        return self.values.copy()

    def get(self, field):
        return self.values.get(field)

    def set(self, field, value):
        self.values[field] = value

    def run_method(self, method):
        if method == "before_change":
            origin.protect_direct_change(self, method)

    def get_all_children(self):
        return []

    def get_doc_before_save(self):
        return self.previous

    def insert(self, ignore_permissions=False):
        if not ignore_permissions and not self.harness.can_create:
            raise frappe.PermissionError("native create denied")
        self.flags.in_insert = True
        origin.enforce_marker(self, "before_validate")
        if self.harness.fail_at == "validate":
            raise frappe.ValidationError("native validate failed")
        self.flags.in_insert = False
        self.name = str(len(self.harness.pending) + len(self.harness.committed) + 1)
        self.harness.pending[self.name] = self.values.copy()
        if self.harness.fail_at == "after_insert":
            raise frappe.ValidationError("native after_insert failed")
        return self

    def update(self, values):
        self.values.update(values)

    def save(self):
        if self.get("__islocal") or not self.name:
            return self.insert()

        self.previous = self.harness.committed[self.name]
        origin.enforce_marker(self, "before_validate")
        self.harness.pending[self.name] = self.values.copy()
        return self


class TestManualTicketOrigin(unittest.TestCase):
    def setUp(self):
        self.meta = Mock()
        self.meta.has_field.return_value = True
        self.meta.is_submittable = False
        self.meta.issingle = False
        self.meta.istable = False
        self.meta.fields = [
            SimpleNamespace(fieldname=field)
            for field in ("subject", "custom_request_source", origin.FIELD, "via_customer_portal")
        ]
        self.session = SimpleNamespace(user="tech@example.test")
        self.account = {"enabled": 1, "user_type": "System User"}
        self.can_create = True
        self.fail_at = None
        self.pending = {}
        self.committed = {}
        self.roles = [TECH]
        self.db = Mock()
        self.db.has_column.return_value = True
        self.db.get_value.side_effect = self.read_value
        flags_patch = patch.object(frappe.local, "flags", frappe._dict(), create=True)
        flags_patch.start()
        self.addCleanup(flags_patch.stop)
        translation_patch = patch("frappe.translate.get_all_translations", return_value={})
        translation_patch.start()
        self.addCleanup(translation_patch.stop)
        frappe_patch = patch.multiple(
            frappe,
            session=self.session,
            flags=frappe._dict(currently_saving=[]),
            get_system_settings=Mock(return_value="UTC"),
            new_doc=lambda doctype: self.get_doc({"doctype": doctype, "__islocal": 1}),
            db=self.db,
            get_doc=self.get_doc,
            get_meta=Mock(return_value=self.meta),
            get_roles=Mock(side_effect=lambda user: self.roles),
            is_table=Mock(return_value=False),
            msgprint=Mock(),
            throw=self.throw,
        )
        frappe_patch.start()
        self.addCleanup(frappe_patch.stop)
        desk_patch = patch.multiple(
            desk_save,
            capture_doc=Mock(),
            run_onload=Mock(),
            send_updated_docs=Mock(),
            add_data_to_monitor=Mock(),
        )
        desk_patch.start()
        self.addCleanup(desk_patch.stop)

    def read_value(self, doctype, name, field, **kwargs):
        if doctype == "User":
            return self.account
        row = self.pending.get(name) or self.committed.get(name)
        return {field: row.get(field)} if row else None

    def get_doc(self, values, name=None):
        if name is not None:
            values = {**self.committed[name], "__islocal": 0, "name": name}
        return Ticket(self, values)

    @staticmethod
    def throw(message, exception, **kwargs):
        raise exception(message)

    def fresh(self, **extra):
        return {
            "doctype": origin.DOCTYPE, "__islocal": 1, "name": "new-hd-ticket-abc",
            "subject": "New Ticket", "custom_request_source": "Customer", **extra,
        }

    def request(self, operation):
        # No site or DB writes. Model only the native request commit/rollback boundary.
        try:
            result = operation()
        except Exception:
            self.pending.clear()
            raise
        self.committed.update(self.pending)
        self.pending.clear()
        return result

    def test_staff_save_marks_only_the_ticket_and_preserves_native_response(self):
        raw = self.fresh(
            **{origin.FIELD: 0}, flags={"ignore_permissions": True}, __newname="injected",
            owner="someone-else", creation="1999-01-01",
        )
        self.request(lambda: origin.create(json.dumps(raw)))
        ticket = desk_save.send_updated_docs.call_args.args[0]
        self.assertIs(desk_save.run_onload.call_args.args[0], ticket)
        self.assertEqual(ticket.get("__temporary_name"), raw["name"])
        self.assertEqual(ticket.localname, raw["name"])
        self.assertEqual(self.committed, {"1": {
            "doctype": origin.DOCTYPE, "__islocal": 1, "name": raw["name"],
            "subject": "New Ticket", "custom_request_source": "Customer",
            "__temporary_name": raw["name"], origin.FIELD: 1,
        }})
        self.assertIsNone(origin._creation_intent.get())
        self.db.commit.assert_not_called()

    def test_native_create_permission_is_required(self):
        self.can_create = False
        with self.assertRaisesRegex(frappe.PermissionError, "native create denied"):
            self.request(lambda: origin.create(self.fresh(flags={"ignore_permissions": 1})))
        self.assertEqual(self.committed, {})
        self.assertIsNone(origin._creation_intent.get())
        desk_save.send_updated_docs.assert_not_called()

    def test_unauthorized_principals_cannot_enter_operation(self):
        partner = "TELECTRO-POC Role - Partner"
        for user, account, roles in (
            ("Guest", self.account, [TECH]),
            ("disabled@example.test", {**self.account, "enabled": 0}, [TECH]),
            ("website@example.test", {**self.account, "user_type": "Website User"}, [TECH]),
            ("customer@example.test", self.account, ["Customer"]),
            ("partner@example.test", self.account, [partner]),
            ("mixed@example.test", self.account, [TECH, partner]),
            ("unclassified@example.test", self.account, ["Desk User", "Agent"]),
        ):
            with self.subTest(user=user):
                self.session.user, self.account, self.roles = user, account, roles
                with self.assertRaises(frappe.PermissionError):
                    origin.create(self.fresh())
        self.assertEqual(self.pending, {})
        self.assertIsNone(origin._creation_intent.get())

    def test_platform_classification_and_existing_names_do_not_qualify(self):
        for extra in (
            {"name": "42"}, {"__islocal": 0}, {"doctype": "Communication"},
            {"via_customer_portal": 1}, {"email_account": "Inbound"}, {"ticket_split_from": "42"},
        ):
            with self.subTest(extra=extra), self.assertRaises(frappe.ValidationError):
                origin.create(self.fresh(**extra))
        self.assertEqual(self.pending, {})

    def test_intent_is_exact_single_use_and_revoked_even_in_copied_context(self):
        intended = self.get_doc(self.fresh())
        other = self.get_doc(self.fresh(**{origin.FIELD: 1}))
        with origin._staff_creation(intended) as intent:
            copied_context = copy_context()
            other.insert()
            self.assertEqual(other.get(origin.FIELD), 0)
            self.assertFalse(intent.consumed)
            intended.insert()
            self.assertEqual(intended.get(origin.FIELD), 1)
            with self.assertRaises(frappe.ValidationError):
                intended.insert()
        intended.flags.in_insert = True
        copied_context.run(origin.enforce_marker, intended)
        self.assertEqual(intended.get(origin.FIELD), 0)
        self.assertIsNone(origin._creation_intent.get())

    def test_failure_before_and_after_staged_insert_revokes_and_rolls_back(self):
        for phase in ("validate", "after_insert"):
            with self.subTest(phase=phase):
                self.fail_at = phase
                with self.assertRaisesRegex(frappe.ValidationError, "native"):
                    self.request(lambda: origin.create(self.fresh()))
                self.assertIsNone(origin._creation_intent.get())
                self.assertEqual(self.committed, {})
                self.assertEqual(self.pending, {})
        self.db.commit.assert_not_called()
        desk_save.send_updated_docs.assert_not_called()

    def test_native_generic_and_portal_inserts_cannot_supply_marker(self):
        for path in (
            lambda data: desk_save.savedocs(json.dumps(data), "Save"),
            client.insert_doc,
            helpdesk_api.new,
        ):
            with self.subTest(path=path):
                payload = self.fresh(**{origin.FIELD: 1})
                self.request(lambda: path(payload))
        self.assertEqual(len(self.committed), 3)
        self.assertTrue(all(row[origin.FIELD] == 0 for row in self.committed.values()))
        self.assertTrue(all(row["custom_request_source"] == "Customer" for row in self.committed.values()))

    def test_native_email_insert_does_not_qualify_even_under_a_staff_session(self):
        email = SimpleNamespace(
            subject="Source by email", from_email="sender@example.test",
            email_account=SimpleNamespace(name="Inbound"),
            get_email_fields=lambda doctype: SimpleNamespace(
                subject_field="subject", sender_field="raised_by",
                sender_name_field=None, recipient_account_field="email_account",
            ),
        )
        name = self.request(lambda: InboundMail._create_reference_document(email, origin.DOCTYPE))
        self.assertEqual(self.committed[name][origin.FIELD], 0)
        self.assertEqual(self.committed[name]["email_account"], "Inbound")

    def test_native_split_and_import_do_not_inherit(self):
        self.request(lambda: origin.create(self.fresh()))
        original = self.get_doc(origin.DOCTYPE, "1")
        name = self.request(lambda: helpdesk_api.duplicate_ticket(original, "Copy from split"))
        self.assertEqual(self.committed[name][origin.FIELD], 0)
        importer = SimpleNamespace(
            doctype=origin.DOCTYPE, data_import=SimpleNamespace(doctype="Data Import", name="import"),
        )
        self.request(lambda: Importer.insert_record(
            importer, frappe._dict(self.fresh(**{origin.FIELD: 1})),
        ))
        self.assertEqual(self.committed["3"][origin.FIELD], 0)
        self.assertEqual(self.committed["1"][origin.FIELD], 1)

    def test_native_client_update_preserves_origin_and_allows_request_source_edit(self):
        self.request(lambda: origin.create(self.fresh()))
        self.request(lambda: client.set_value(
            origin.DOCTYPE, "1", {origin.FIELD: 0, "custom_request_source": "Telectro"},
        ))
        self.assertEqual(self.committed["1"][origin.FIELD], 1)
        self.assertEqual(self.committed["1"]["custom_request_source"], "Telectro")

        self.request(lambda: self.get_doc(self.fresh()).insert())
        self.request(lambda: client.set_value(origin.DOCTYPE, "2", origin.FIELD, 1))
        self.assertEqual(self.committed["2"][origin.FIELD], 0)

    def test_direct_change_hook_uses_current_persisted_origin(self):
        self.request(lambda: origin.create(self.fresh()))
        ticket = self.get_doc(origin.DOCTYPE, "1")
        ticket.previous = self.committed["1"]
        Document.db_set(ticket, "custom_request_source", "Telectro", update_modified=False)
        self.db.set_value.assert_called_once()
        self.db.set_value.reset_mock()
        with self.assertRaises(frappe.PermissionError):
            Document.db_set(ticket, origin.FIELD, 0, update_modified=False)
        self.db.set_value.assert_not_called()
        self.assertEqual(self.committed["1"][origin.FIELD], 1)
        self.db.get_value.assert_called_with(
            origin.DOCTYPE, "1", origin.FIELD, as_dict=True, for_update=True,
        )

    def test_missing_schema_preserves_native_staff_save_and_suppresses_desk_opt_in(self):
        self.meta.has_field.return_value = False
        boot = SimpleNamespace()
        origin.add_desk_capability(boot)
        self.assertFalse(hasattr(boot, "telectro_manual_ticket_create"))
        self.request(lambda: origin.create(self.fresh(**{origin.FIELD: 1})))
        self.assertNotIn(origin.FIELD, self.committed["1"])
        self.assertIsNone(origin._creation_intent.get())
        self.db.has_column.assert_not_called()

    def test_boot_offers_operation_only_when_staff_and_both_schema_parts_exist(self):
        for roles, column, expected in (
            ([TECH], True, True), (["Agent"], True, False), ([TECH], False, False),
        ):
            with self.subTest(roles=roles, column=column):
                self.roles, self.db.has_column.return_value = roles, column
                boot = SimpleNamespace()
                origin.add_desk_capability(boot)
                self.assertEqual(getattr(boot, "telectro_manual_ticket_create", False), expected)

    def test_endpoint_is_whitelisted_only_for_authenticated_post(self):
        self.assertIn(origin.create, frappe.whitelisted)
        self.assertNotIn(origin.create, frappe.guest_methods)
        self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[origin.create], ["POST"])

    def test_fixture_declares_one_hidden_noncopyable_server_managed_check(self):
        root = Path(__file__).resolve().parents[1]
        fixtures = json.loads((root / "fixtures/custom_field.json").read_text())
        records = [row for row in fixtures if row.get("fieldname") == origin.FIELD]
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(
            {key: record[key] for key in ("dt", "fieldtype", "default", "hidden", "read_only", "no_copy")},
            {"dt": origin.DOCTYPE, "fieldtype": "Check", "default": "0", "hidden": 1,
             "read_only": 1, "no_copy": 1},
        )
