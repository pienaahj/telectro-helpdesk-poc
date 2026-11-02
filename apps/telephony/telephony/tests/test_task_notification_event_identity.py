import unittest

from telephony import task_notification_policy as policy


class TestTaskNotificationEventIdentity(unittest.TestCase):

    def key(
        self,
        *,
        ticket="911",
        action="assignment",
        event_id="TODO-001",
        recipient="tech.alfa@local.test",
    ):
        return policy.task_notification_event_key(
            ticket=ticket,
            action=action,
            event_id=event_id,
            recipient=recipient,
        )

    def test_same_event_produces_same_key(self):
        first = self.key()
        retry = self.key()

        self.assertEqual(first, retry)
        self.assertRegex(first, r"^[0-9a-f]{64}$")

    def test_later_assignment_has_different_key(self):
        first = self.key(event_id="TODO-001")
        later = self.key(event_id="TODO-002")

        self.assertNotEqual(first, later)

    def test_different_recipient_has_different_key(self):
        alfa = self.key(recipient="tech.alfa@local.test")
        bravo = self.key(recipient="tech.bravo@local.test")

        self.assertNotEqual(alfa, bravo)

    def test_recipient_case_is_normalised(self):
        first = self.key(recipient="Tech.Alfa@Local.Test")
        second = self.key(recipient="tech.alfa@local.test")

        self.assertEqual(first, second)

    def test_different_action_has_different_key(self):
        assignment = self.key(action="assignment")
        handoff = self.key(action="handoff")

        self.assertNotEqual(assignment, handoff)

    def test_missing_identity_fails_closed(self):
        for field in (
            "ticket",
            "action",
            "event_id",
            "recipient",
        ):
            with self.subTest(field=field):
                kwargs = {field: ""}

                with self.assertRaises(ValueError):
                    self.key(**kwargs)

    def test_unknown_action_fails_closed(self):
        with self.assertRaises(ValueError):
            self.key(action="unexpected")


if __name__ == "__main__":
    unittest.main()
