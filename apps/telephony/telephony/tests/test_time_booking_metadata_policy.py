"""Isolated tests for Phase 2 booking metadata policy."""

import unittest

from telephony.time_booking_metadata_policy import (
    BookingMetadataValidationError,
    validate_service_area,
    validate_work_location,
    validate_work_origin,
    normalize_emergency,
)


class TestBookingMetadataPolicy(unittest.TestCase):

    def test_customer_support_service_area(self):
        allowed = ("Other", "Routing", "PABX")

        for value in allowed:
            with self.subTest(valid=value):
                self.assertIsNone(
                    validate_service_area(
                        work_context="Customer Support",
                        service_area=value,
                        allowed_service_areas=allowed,
                    )
                )

        for value in (
            None,
            "",
            "   ",
            "Unknown Service",
            "pabx",
            123,
        ):
            with self.subTest(invalid=value):
                with self.assertRaises(
                    BookingMetadataValidationError
                ):
                    validate_service_area(
                        work_context="Customer Support",
                        service_area=value,
                        allowed_service_areas=allowed,
                    )


    def test_project_service_area(self):
        allowed = ("Other", "Routing", "PABX")

        for value in allowed:
            with self.subTest(valid=value):
                self.assertIsNone(
                    validate_service_area(
                        work_context="Project",
                        service_area=value,
                        allowed_service_areas=allowed,
                    )
                )

        for value in (
            None,
            "",
            "   ",
            "Unknown Service",
            "pabx",
            123,
        ):
            with self.subTest(invalid=value):
                with self.assertRaises(
                    BookingMetadataValidationError
                ):
                    validate_service_area(
                        work_context="Project",
                        service_area=value,
                        allowed_service_areas=allowed,
                    )

    def test_helpdesk_service_area(self):
        allowed = ("Other", "Routing", "PABX")

        # Valid Service Areas derived from an HD Ticket.
        for value in allowed:
            with self.subTest(valid=value):
                self.assertIsNone(
                    validate_service_area(
                        work_context="Helpdesk",
                        service_area=value,
                        allowed_service_areas=allowed,
                    )
                )

        # Missing or invalid ticket classifications must fail.
        for value in (
            None,
            "",
            "   ",
            "Unknown Service",
            "pabx",
            123,
        ):
            with self.subTest(invalid=value):
                with self.assertRaises(
                    BookingMetadataValidationError
                ):
                    validate_service_area(
                        work_context="Helpdesk",
                        service_area=value,
                        allowed_service_areas=allowed,
                    )

    def test_internal_service_area(self):
        allowed = ("Other", "Routing", "PABX")

        # Internal work does not require a Service Area.
        for value in (None, ""):
            with self.subTest(absent=value):
                self.assertIsNone(
                    validate_service_area(
                        work_context="Internal",
                        service_area=value,
                        allowed_service_areas=allowed,
                    )
                )

        # An explicitly selected Service Area must be valid.
        for value in allowed:
            with self.subTest(valid=value):
                self.assertIsNone(
                    validate_service_area(
                        work_context="Internal",
                        service_area=value,
                        allowed_service_areas=allowed,
                    )
                )

        # Invalid values must never be persisted.
        for value in ("   ", "Unknown Service", "pabx", 123):
            with self.subTest(invalid=value):
                with self.assertRaises(
                    BookingMetadataValidationError
                ):
                    validate_service_area(
                        work_context="Internal",
                        service_area=value,
                        allowed_service_areas=allowed,
                    )

    def test_technical_work_location(self):
        for location in (
            "On-site",
            "Remote",
            "Workshop / Internal",
        ):
            with self.subTest(valid=location):
                self.assertIsNone(
                    validate_work_location(
                        activity_type="Fault Finding & Diagnosis",
                        work_location=location,
                    )
                )

        for location in (
            None,
            "",
            "   ",
            "Customer Site",
            "on-site",
            123,
        ):
            with self.subTest(invalid=location):
                with self.assertRaises(
                    BookingMetadataValidationError
                ):
                    validate_work_location(
                        activity_type="Fault Finding & Diagnosis",
                        work_location=location,
                    )

    def test_travel_work_location(self):
        # Travel has its own Activity Type and no Work Location.
        for location in (None, ""):
            with self.subTest(valid=location):
                self.assertIsNone(
                    validate_work_location(
                        activity_type="Travel",
                        work_location=location,
                    )
                )

        # Travel must not carry a misleading location.
        for location in (
            "On-site",
            "Remote",
            "Workshop / Internal",
            "   ",
            123,
        ):
            with self.subTest(invalid=location):
                with self.assertRaises(
                    BookingMetadataValidationError
                ):
                    validate_work_location(
                        activity_type="Travel",
                        work_location=location,
                    )

    def test_direct_work_origin(self):
        # Direct / Ad-hoc requires no additional origin metadata.
        for external_reference, other_description in (
            (None, None),
            ("", ""),
        ):
            with self.subTest(
                valid=(external_reference, other_description)
            ):
                self.assertIsNone(
                    validate_work_origin(
                        work_origin="Direct / Ad-hoc",
                        external_reference=external_reference,
                        other_origin_description=other_description,
                    )
                )

        # Unrelated origin metadata must not survive.
        for external_reference, other_description in (
            ("SNAP-123", None),
            (None, "Referral"),
            ("SNAP-123", "Referral"),
            (" ", None),
            (123, None),
        ):
            with self.subTest(
                invalid=(external_reference, other_description)
            ):
                with self.assertRaises(
                    BookingMetadataValidationError
                ):
                    validate_work_origin(
                        work_origin="Direct / Ad-hoc",
                        external_reference=external_reference,
                        other_origin_description=other_description,
                    )

    def test_snapfix_work_origin(self):
        # Snapfix requires an external reference.
        for reference, description in (
            ("SNAP-123", None),
            ("SNAP-456", ""),
        ):
            with self.subTest(valid=(reference, description)):
                self.assertIsNone(
                    validate_work_origin(
                        work_origin="Snapfix",
                        external_reference=reference,
                        other_origin_description=description,
                    )
                )

        # Missing, malformed or conflicting metadata must fail.
        for reference, description in (
            (None, None),
            ("", None),
            ("   ", None),
            (" SNAP-123 ", None),
            (123, None),
            ("SNAP-123", "Referral"),
            ("SNAP-123", " "),
        ):
            with self.subTest(invalid=(reference, description)):
                with self.assertRaises(
                    BookingMetadataValidationError
                ):
                    validate_work_origin(
                        work_origin="Snapfix",
                        external_reference=reference,
                        other_origin_description=description,
                    )

    def test_other_work_origin(self):
        # Other requires a meaningful origin description.
        for reference, description in (
            (None, "Referral from colleague"),
            ("", "Customer telephone request"),
        ):
            with self.subTest(valid=(reference, description)):
                self.assertIsNone(
                    validate_work_origin(
                        work_origin="Other",
                        external_reference=reference,
                        other_origin_description=description,
                    )
                )

        # Missing, malformed or conflicting metadata must fail.
        for reference, description in (
            (None, None),
            (None, ""),
            (None, "   "),
            (None, " Referral "),
            (None, 123),
            ("SNAP-123", "Referral"),
            (" ", "Referral"),
        ):
            with self.subTest(invalid=(reference, description)):
                with self.assertRaises(
                    BookingMetadataValidationError
                ):
                    validate_work_origin(
                        work_origin="Other",
                        external_reference=reference,
                        other_origin_description=description,
                    )

    def test_emergency_normalization(self):
        valid = ((0, 0), (1, 1), (False, 0), (True, 1))

        for supplied, expected in valid:
            with self.subTest(valid=supplied):
                actual = normalize_emergency(supplied)
                self.assertEqual(actual, expected)
                self.assertIs(type(actual), int)

        invalid = (
            None, "", "0", "1", "true", 2, -1,
            0.0, 1.0, [], {},
        )

        for supplied in invalid:
            with self.subTest(invalid=supplied):
                with self.assertRaises(
                    BookingMetadataValidationError
                ):
                    normalize_emergency(supplied)

if __name__ == "__main__":
    unittest.main()
