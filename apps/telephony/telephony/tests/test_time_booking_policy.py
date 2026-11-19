"""Isolated tests: standard library and the pure policy module only."""

import copy
import unittest
from types import MappingProxyType

from telephony.time_booking_policy import (
    WorkContextValidationError,
    validate_work_context,
)


class TestWorkContextPolicy(unittest.TestCase):
    def row(self, context, **references):
        return {"custom_work_context": context, **references}

    def test_valid_contexts(self):
        for row in [
            self.row("Helpdesk", custom_hd_ticket="76"),
            self.row("Project", project="PROJ-0001"),
            self.row("Customer Support", custom_hd_customer="Operational Customer"),
            self.row("Internal", activity_type="Planning", description="Plan work"),
        ]:
            with self.subTest(row=row):
                self.assertIsNone(validate_work_context(row))

    def test_required_references(self):
        for context, field in [
            ("Helpdesk", "custom_hd_ticket"),
            ("Project", "project"),
            ("Customer Support", "custom_hd_customer"),
        ]:
            for value in [None, "", "   "]:
                with self.subTest(context=context, value=value):
                    with self.assertRaisesRegex(WorkContextValidationError, field):
                        validate_work_context(self.row(context, **{field: value}))

    def test_all_prohibited_references(self):
        cases = [
            ("Helpdesk", {"custom_hd_ticket": "76"}, ["project", "task"]),
            ("Project", {"project": "P"}, ["custom_hd_ticket"]),
            ("Customer Support", {"custom_hd_customer": "C"},
             ["custom_hd_ticket", "project", "task"]),
            ("Internal", {},
             ["custom_hd_ticket", "custom_hd_customer", "project", "task"]),
        ]
        for context, required, prohibited in cases:
            for field in prohibited:
                with self.subTest(context=context, field=field):
                    with self.assertRaisesRegex(WorkContextValidationError, field):
                        validate_work_context(
                            self.row(context, **required, **{field: "reference"})
                        )

    def test_unknown_context(self):
        for value in ["Other", "helpdesk", " Project ", 42, []]:
            with self.subTest(value=value):
                with self.assertRaises(WorkContextValidationError):
                    validate_work_context(self.row(value))

    def test_new_blank_context_rejected(self):
        for row in [{}, self.row(None), self.row(""), self.row("   ")]:
            with self.subTest(row=row):
                with self.assertRaisesRegex(WorkContextValidationError, "required"):
                    validate_work_context(row)

    def test_project_optional_task_and_customer(self):
        for extras in [{}, {"task": "T"}, {"custom_hd_customer": "C"},
                       {"task": "T", "custom_hd_customer": "C"}]:
            with self.subTest(extras=extras):
                self.assertIsNone(validate_work_context(
                    self.row("Project", project="P", **extras)
                ))

    def test_helpdesk_optional_customer(self):
        self.assertIsNone(validate_work_context(
            self.row("Helpdesk", custom_hd_ticket="76", custom_hd_customer="C")
        ))

    def test_customer_support_exactly_one_customer_identity(self):
        cases = [
            (
                "existing customer",
                {
                    "custom_hd_customer": "Operational Customer",
                    "custom_unlisted_customer_name": None,
                },
                True,
            ),
            (
                "unlisted customer",
                {
                    "custom_hd_customer": None,
                    "custom_unlisted_customer_name": "Prospective Customer",
                },
                True,
            ),
            (
                "both identities",
                {
                    "custom_hd_customer": "Operational Customer",
                    "custom_unlisted_customer_name": "Prospective Customer",
                },
                False,
            ),
            (
                "neither identity",
                {
                    "custom_hd_customer": None,
                    "custom_unlisted_customer_name": None,
                },
                False,
            ),
        ]

        for name, references, valid in cases:
            with self.subTest(case=name):
                row = self.row("Customer Support", **references)

                if valid:
                    self.assertIsNone(validate_work_context(row))
                else:
                    with self.assertRaises(WorkContextValidationError):
                        validate_work_context(row)

    def test_emergency_independence(self):
        for flag in [0, 1]:
            self.assertIsNone(validate_work_context(
                self.row("Internal", custom_emergency=flag)
            ))
            with self.assertRaises(WorkContextValidationError):
                validate_work_context(self.row("Helpdesk", custom_emergency=flag))

    def test_no_mutation_on_success_or_failure(self):
        valid = self.row("Project", project=" P ", task=" T ", custom_emergency=1)
        before = copy.deepcopy(valid)
        self.assertIsNone(validate_work_context(MappingProxyType(valid)))
        self.assertEqual(valid, before)

        invalid = self.row("Internal", custom_hd_ticket="private-reference")
        before = copy.deepcopy(invalid)
        with self.assertRaisesRegex(WorkContextValidationError, "custom_hd_ticket"):
            validate_work_context(MappingProxyType(invalid))
        self.assertEqual(invalid, before)

    def test_untouched_historical_blank_is_preserved(self):
        for context in [None, "", "   "]:
            row = self.row(context, project="legacy", task="legacy-task")
            before = copy.deepcopy(row)
            self.assertIsNone(validate_work_context(
                MappingProxyType(row), untouched_historical=True
            ))
            self.assertEqual(row, before)

    def test_historical_flag_does_not_skip_classified_invalid_rows(self):
        for row in [self.row("Unknown"), self.row("Helpdesk"),
                    self.row("Internal", project="P")]:
            with self.subTest(row=row):
                with self.assertRaises(WorkContextValidationError):
                    validate_work_context(row, untouched_historical=True)

    def test_invalid_required_or_prohibited_reference_type(self):
        for row in [self.row("Project", project=123),
                    self.row("Internal", custom_hd_ticket=["76"])]:
            with self.subTest(row=row):
                with self.assertRaises(WorkContextValidationError):
                    validate_work_context(row)


    def test_invalid_optional_reference_types(self):
        cases = [
            ("Project", {"project": "P"}, "task"),
            ("Project", {"project": "P"}, "custom_hd_customer"),
            ("Helpdesk", {"custom_hd_ticket": "76"}, "custom_hd_customer"),
        ]
        for context, required, field in cases:
            for value in [123, [], {}, True, 1.5, object()]:
                with self.subTest(context=context, field=field, value=value):
                    with self.assertRaisesRegex(WorkContextValidationError, field):
                        validate_work_context(
                            self.row(context, **required, **{field: value})
                        )

    def test_optional_absent_reference_forms(self):
        cases = [
            ("Project", {"project": "P"}, "task"),
            ("Project", {"project": "P"}, "custom_hd_customer"),
            ("Helpdesk", {"custom_hd_ticket": "76"}, "custom_hd_customer"),
        ]
        for context, required, field in cases:
            for extras in [{}, {field: None}, {field: ""}, {field: "   "}]:
                with self.subTest(context=context, field=field, extras=extras):
                    self.assertIsNone(validate_work_context(
                        self.row(context, **required, **extras)
                    ))

    def test_nonboolean_historical_flags_rejected(self):
        for flag in [1, 0, "yes", "", [1], {"enabled": True}, None]:
            for row in [self.row(""), self.row("Internal")]:
                with self.subTest(flag=flag, row=row):
                    with self.assertRaisesRegex(
                        WorkContextValidationError, "untouched_historical"
                    ):
                        validate_work_context(row, untouched_historical=flag)

    def test_missing_context_historical_exemption(self):
        row = {"project": "legacy"}
        self.assertIsNone(validate_work_context(row, untouched_historical=True))
        self.assertEqual(row, {"project": "legacy"})

    def test_unlisted_customer_boundary_cases(self):
        # Empty alternatives count as absent when an HD Customer exists.
        for value in [None, "", "   "]:
            with self.subTest(empty_unlisted=value):
                self.assertIsNone(validate_work_context(self.row(
                    "Customer Support",
                    custom_hd_customer="Existing Customer",
                    custom_unlisted_customer_name=value,
                )))

        # An unlisted customer name must be meaningful.
        for value in [None, "", "   "]:
            with self.subTest(missing_unlisted=value):
                with self.assertRaises(WorkContextValidationError):
                    validate_work_context(self.row(
                        "Customer Support",
                        custom_unlisted_customer_name=value,
                    ))

        # Reject invalid input types, even with a valid Customer link.
        for value in [123, [], {}, True, 1.5]:
            with self.subTest(invalid_type=value):
                with self.assertRaisesRegex(
                    WorkContextValidationError,
                    "custom_unlisted_customer_name",
                ):
                    validate_work_context(self.row(
                        "Customer Support",
                        custom_hd_customer="Existing Customer",
                        custom_unlisted_customer_name=value,
                    ))

        # Unlisted customer identities belong only to Customer Support.
        for context, references in [
            ("Helpdesk", {"custom_hd_ticket": "76"}),
            ("Project", {"project": "PROJ-0001"}),
            ("Internal", {}),
        ]:
            with self.subTest(prohibited_context=context):
                with self.assertRaisesRegex(
                    WorkContextValidationError,
                    "custom_unlisted_customer_name",
                ):
                    validate_work_context(self.row(
                        context,
                        **references,
                        custom_unlisted_customer_name="Prospective Customer",
                    ))

if __name__ == "__main__":
    unittest.main()
