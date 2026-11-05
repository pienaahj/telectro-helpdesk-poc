"""Permanent regressions for notification batch error reporting.

Frappe document creation and transaction operations are mocked.
"""

import unittest

from unittest.mock import Mock, call, patch

from telephony import data_request_notification_reporting as reporting


class TestNotificationReporting(unittest.TestCase):

    def setUp(self):
        self.intent = "TDRN-ESC114-TEST"

        self.record = Mock()
        self.record.name = "ERROR-LOG-ESC114"

        self.get_doc = Mock(return_value=self.record)
        self.db = Mock()
        self.native_log_error = Mock()

        patches = [
            patch.object(
                reporting.frappe, "get_doc", self.get_doc
            ),
            patch.object(
                reporting.frappe, "db", self.db
            ),
            patch.object(
                reporting.frappe,
                "log_error",
                self.native_log_error,
            ),
        ]

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def persist(self, name=None):
        if name is None:
            name = self.intent

        return reporting.persist_unhandled_batch_error(name)

    def assert_no_writes(self):
        self.get_doc.assert_not_called()
        self.db.commit.assert_not_called()
        self.db.rollback.assert_not_called()

    def test_valid_log_reference_without_commit(self):
        result = self.persist()

        self.assertEqual(result, "ERROR-LOG-ESC114")

        self.get_doc.assert_called_once_with({
            "doctype": "Error Log",
            "method": reporting.ERROR_LOG_TITLE,
            "error": reporting.ERROR_CODE,
            "reference_doctype": reporting.DOCTYPE,
            "reference_name": self.intent,
        })

        self.record.insert.assert_called_once_with(
            ignore_permissions=True
        )

        self.db.commit.assert_not_called()
        self.db.rollback.assert_not_called()

    def test_insert_does_not_commit_or_rollback(self):
        operations = Mock()

        operations.attach_mock(
            self.record.insert, "insert"
        )
        operations.attach_mock(
            self.db.commit, "commit"
        )
        operations.attach_mock(
            self.db.rollback, "rollback"
        )

        self.persist()

        self.assertEqual(
            operations.mock_calls,
            [call.insert(ignore_permissions=True)],
        )

    def test_native_logging_api_not_used(self):
        self.persist()

        self.native_log_error.assert_not_called()

        document = self.get_doc.call_args.args[0]

        self.assertEqual(
            set(document),
            {
                "doctype",
                "method",
                "error",
                "reference_doctype",
                "reference_name",
            },
        )

        self.assertEqual(
            document["error"],
            "UNHANDLED_BATCH_EXCEPTION",
        )

    def test_rejects_non_string_reference(self):
        for value in (
            None,
            123,
            True,
            False,
            b"IDENTITY",
            [],
            {},
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    reporting.persist_unhandled_batch_error(
                        value
                    )

        self.assert_no_writes()

    def test_rejects_empty_or_whitespace_reference(self):
        for value in ("", " ", "   ", "\t", "\n"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    reporting.persist_unhandled_batch_error(
                        value
                    )

        self.assert_no_writes()

    def test_rejects_overlong_reference(self):
        with self.assertRaises(ValueError):
            self.persist("A" * 141)

        self.assert_no_writes()

    def test_accepts_exact_length_limit(self):
        name = "A" * 140

        result = self.persist(name)

        self.assertEqual(result, self.record.name)

        document = self.get_doc.call_args.args[0]

        self.assertEqual(
            document["reference_name"], name
        )

        self.db.commit.assert_not_called()

    def test_rejects_surrounding_whitespace(self):
        for value in (
            " INTENT",
            "INTENT ",
            "\tINTENT",
            "INTENT\n",
        ):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    self.persist(value)

        self.assert_no_writes()

    def test_rejects_control_characters(self):
        for value in (
            "INTENT\nOTHER",
            "INTENT\tOTHER",
            "INTENT\rOTHER",
            "INTENT\x00OTHER",
            "INTENT\x7fOTHER",
        ):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    self.persist(value)

        self.assert_no_writes()

    def test_printable_internal_spaces_allowed(self):
        name = "ESC114 VALID REFERENCE"

        self.persist(name)

        document = self.get_doc.call_args.args[0]

        self.assertEqual(
            document["reference_name"], name
        )

        self.db.commit.assert_not_called()

    def test_get_doc_failure_preserves_transaction(self):
        self.get_doc.side_effect = RuntimeError(
            "Simulated document construction failure"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Notification batch error-log persistence failed",
        ):
            self.persist()

        self.db.rollback.assert_not_called()
        self.db.commit.assert_not_called()

    def test_insert_failure_preserves_transaction(self):
        self.record.insert.side_effect = RuntimeError(
            "Simulated insert failure"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Notification batch error-log persistence failed",
        ):
            self.persist()

        self.db.rollback.assert_not_called()
        self.db.commit.assert_not_called()

    def test_reporting_never_commits_caller_transaction(self):
        self.db.commit.side_effect = RuntimeError(
            "Unexpected caller transaction commit"
        )

        result = self.persist()

        self.assertEqual(result, self.record.name)

        self.record.insert.assert_called_once_with(
            ignore_permissions=True
        )

        self.db.commit.assert_not_called()
        self.db.rollback.assert_not_called()

    def test_exception_detail_not_exposed(self):
        secret = "PRIVATE_CUSTOMER_INFORMATION"

        self.record.insert.side_effect = RuntimeError(
            secret
        )

        with self.assertRaises(RuntimeError) as raised:
            self.persist()

        error = raised.exception

        self.assertEqual(
            str(error),
            "Notification batch error-log persistence failed",
        )

        self.assertNotIn(secret, str(error))
        self.assertIsNone(error.__cause__)
        self.assertTrue(error.__suppress_context__)

        self.db.rollback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
