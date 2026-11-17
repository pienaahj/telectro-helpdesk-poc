import dataclasses
import unittest

from telephony.time_booking_activation_policy import (
    ACTIVE_RUNTIME,
    PRE_ACTIVATION,
    ActivationConfigurationError,
    ActivationConfigurationSnapshot,
    ConfigurationCategory,
    HookBinding,
    validate_activation_configuration,
)


NATIVE_CONTROLLER = "erpnext.projects.doctype.timesheet.timesheet.Timesheet"
MANAGED_CONTROLLER = (
    "telephony.time_booking_timesheet_controller.TelectroBookingTimesheet"
)
LIFECYCLE_HANDLER = (
    "telephony.time_booking_provenance_lifecycle._validate_timesheet_provenance"
)

WILDCARD_HOOKS = (
    HookBinding(
        "validate",
        (
            "erpnext.support.doctype.service_level_agreement."
            "service_level_agreement.apply",
            "erpnext.setup.doctype.transaction_deletion_record."
            "transaction_deletion_record.check_for_running_deletion_job",
        ),
    ),
    HookBinding(
        "on_update",
        (
            "frappe.desk.notifications.clear_doctype_notifications",
            "frappe.workflow.doctype.workflow_action.workflow_action."
            "process_workflow_actions",
            "frappe.core.doctype.file.utils.attach_files_to_document",
            "frappe.automation.doctype.assignment_rule.assignment_rule.apply",
            "frappe.automation.doctype.assignment_rule.assignment_rule."
            "update_due_date",
            "frappe.core.doctype.user_type.user_type."
            "apply_permissions_for_non_standard_user_type",
            "frappe.search.sqlite_search.update_doc_index",
        ),
    ),
    HookBinding(
        "on_change",
        (
            "frappe.social.doctype.energy_point_rule.energy_point_rule."
            "process_energy_points",
            "frappe.automation.doctype.milestone_tracker.milestone_tracker."
            "evaluate_milestone",
        ),
    ),
)

RUNTIME_HOOKS = tuple(
    HookBinding(event, (LIFECYCLE_HANDLER,))
    for event in (
        "before_insert",
        "before_validate",
        "before_save",
        "before_submit",
        "before_cancel",
        "before_update_after_submit",
        "before_change",
    )
)

CATEGORIES = (
    "notification",
    "webhook",
    "server_script",
    "workflow",
    "assignment_rule",
    "energy_point_rule",
    "milestone_tracker",
)


def baseline(mode=PRE_ACTIVATION, *, disabled_count=0):
    return ActivationConfigurationSnapshot(
        controller=NATIVE_CONTROLLER if mode == PRE_ACTIVATION else MANAGED_CONTROLLER,
        controller_extensions=(),
        timesheet_hooks=() if mode == PRE_ACTIVATION else RUNTIME_HOOKS,
        wildcard_hooks=WILDCARD_HOOKS,
        configuration_categories=tuple(
            ConfigurationCategory(category, 0, disabled_count)
            for category in CATEGORIES
        ),
        attachment_fields=(),
        sqlite_search_integrations=(),
    )


class TestActivationConfigurationPolicy(unittest.TestCase):
    def assert_denied(self, snapshot, *, mode=PRE_ACTIVATION):
        with self.assertRaisesRegex(
            ActivationConfigurationError,
            r"^Managed time booking is not available\.$",
        ):
            validate_activation_configuration(snapshot, mode=mode)

    def test_complete_pre_activation_baseline(self):
        self.assertIsNone(
            validate_activation_configuration(baseline(), mode=PRE_ACTIVATION)
        )

    def test_complete_active_runtime_baseline(self):
        self.assertIsNone(
            validate_activation_configuration(
                baseline(ACTIVE_RUNTIME), mode=ACTIVE_RUNTIME
            )
        )

    def test_modes_do_not_accept_the_other_controller_state(self):
        self.assert_denied(baseline(ACTIVE_RUNTIME), mode=PRE_ACTIVATION)
        self.assert_denied(baseline(), mode=ACTIVE_RUNTIME)

    def test_missing_or_incorrect_controller_is_denied(self):
        self.assert_denied(dataclasses.replace(baseline(), controller=""))
        self.assert_denied(
            dataclasses.replace(baseline(), controller="example.OtherTimesheet")
        )

    def test_missing_runtime_lifecycle_handler_is_denied(self):
        snapshot = baseline(ACTIVE_RUNTIME)
        self.assert_denied(
            dataclasses.replace(snapshot, timesheet_hooks=RUNTIME_HOOKS[:-1]),
            mode=ACTIVE_RUNTIME,
        )

    def test_incorrect_runtime_lifecycle_handler_is_denied(self):
        changed = list(RUNTIME_HOOKS)
        changed[0] = HookBinding("before_insert", ("example.handler",))
        self.assert_denied(
            dataclasses.replace(
                baseline(ACTIVE_RUNTIME), timesheet_hooks=tuple(changed)
            ),
            mode=ACTIVE_RUNTIME,
        )

    def test_unexpected_timesheet_hook_is_denied(self):
        self.assert_denied(
            dataclasses.replace(
                baseline(),
                timesheet_hooks=(HookBinding("validate", ("example.handler",)),),
            )
        )

    def test_unexpected_or_reordered_wildcard_hook_is_denied(self):
        self.assert_denied(
            dataclasses.replace(baseline(), wildcard_hooks=WILDCARD_HOOKS[:-1])
        )
        self.assert_denied(
            dataclasses.replace(
                baseline(), wildcard_hooks=tuple(reversed(WILDCARD_HOOKS))
            )
        )

    def test_controller_extension_is_denied(self):
        self.assert_denied(
            dataclasses.replace(
                baseline(), controller_extensions=("example.TimesheetMixin",)
            )
        )

    def test_each_enabled_prohibited_category_is_denied(self):
        for category in CATEGORIES:
            with self.subTest(category=category):
                states = tuple(
                    ConfigurationCategory(name, int(name == category), 0)
                    for name in CATEGORIES
                )
                self.assert_denied(
                    dataclasses.replace(
                        baseline(), configuration_categories=states
                    )
                )

    def test_disabled_configuration_records_are_allowed(self):
        self.assertIsNone(
            validate_activation_configuration(
                baseline(disabled_count=3), mode=PRE_ACTIVATION
            )
        )

    def test_attachment_field_is_denied(self):
        self.assert_denied(
            dataclasses.replace(
                baseline(), attachment_fields=("supporting_document",)
            )
        )

    def test_timesheet_sqlite_integration_is_denied(self):
        self.assert_denied(
            dataclasses.replace(
                baseline(), sqlite_search_integrations=("example.search",)
            )
        )

    def test_missing_configuration_category_is_denied(self):
        self.assert_denied(
            dataclasses.replace(
                baseline(),
                configuration_categories=baseline().configuration_categories[:-1],
            )
        )

    def test_unknown_or_duplicate_configuration_category_is_denied(self):
        items = baseline().configuration_categories
        self.assert_denied(
            dataclasses.replace(
                baseline(),
                configuration_categories=items[:-1]
                + (ConfigurationCategory("unknown", 0, 0),),
            )
        )
        self.assert_denied(
            dataclasses.replace(
                baseline(), configuration_categories=items + (items[0],)
            )
        )

    def test_malformed_counts_are_denied(self):
        for enabled, disabled in ((True, 0), (0, False), (-1, 0), (0, -1)):
            with self.subTest(enabled=enabled, disabled=disabled):
                items = list(baseline().configuration_categories)
                items[0] = ConfigurationCategory("notification", enabled, disabled)
                self.assert_denied(
                    dataclasses.replace(
                        baseline(), configuration_categories=tuple(items)
                    )
                )

    def test_missing_snapshot_or_unknown_mode_is_denied(self):
        self.assert_denied({})
        self.assert_denied(baseline(), mode="unknown")
        self.assert_denied(baseline(), mode=True)

    def test_malformed_collection_shapes_are_denied(self):
        for field, value in (
            ("controller_extensions", []),
            ("timesheet_hooks", []),
            ("wildcard_hooks", []),
            ("configuration_categories", []),
            ("attachment_fields", []),
            ("sqlite_search_integrations", []),
        ):
            with self.subTest(field=field):
                self.assert_denied(dataclasses.replace(baseline(), **{field: value}))

    def test_malformed_hook_and_string_values_are_denied(self):
        self.assert_denied(
            dataclasses.replace(
                baseline(),
                wildcard_hooks=(HookBinding("validate", (object(),)),)
                + WILDCARD_HOOKS[1:],
            )
        )
        self.assert_denied(
            dataclasses.replace(baseline(), attachment_fields=("",))
        )

    def test_snapshot_and_nested_records_are_immutable(self):
        snapshot = baseline()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            snapshot.controller = MANAGED_CONTROLLER
        with self.assertRaises(dataclasses.FrozenInstanceError):
            snapshot.wildcard_hooks[0].event = "before_insert"
        with self.assertRaises(dataclasses.FrozenInstanceError):
            snapshot.configuration_categories[0].enabled_count = 1

    def test_repeated_validation_is_deterministic_and_nonmutating(self):
        snapshot = baseline(ACTIVE_RUNTIME, disabled_count=2)
        original = repr(snapshot)
        for _ in range(3):
            self.assertIsNone(
                validate_activation_configuration(snapshot, mode=ACTIVE_RUNTIME)
            )
        self.assertEqual(repr(snapshot), original)

    def test_public_error_is_generic_for_distinct_failures(self):
        messages = []
        for snapshot in (
            dataclasses.replace(baseline(), controller="secret.Controller"),
            dataclasses.replace(
                baseline(), attachment_fields=("secret_attachment",)
            ),
        ):
            try:
                validate_activation_configuration(snapshot, mode=PRE_ACTIVATION)
            except ActivationConfigurationError as exc:
                messages.append(str(exc))
        self.assertEqual(
            messages,
            [
                "Managed time booking is not available.",
                "Managed time booking is not available.",
            ],
        )


if __name__ == "__main__":
    unittest.main()
