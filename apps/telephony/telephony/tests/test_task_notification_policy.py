import importlib
import unittest


class TestTaskNotificationPolicy(unittest.TestCase):

    def policy(self, *, action, previous_owner, recipient):
        module = importlib.import_module(
            "telephony.task_notification_policy"
        )
        return module.should_notify_assignment(
            action=action,
            previous_owner=previous_owner,
            recipient=recipient,
        )

    def test_initial_assignment_requires_notification(self):
        self.assertTrue(self.policy(
            action="assignment",
            previous_owner="",
            recipient="tech.alfa@local.test",
        ))

    def test_reassignment_requires_notification(self):
        self.assertTrue(self.policy(
            action="assignment",
            previous_owner="tech.alfa@local.test",
            recipient="tech.bravo@local.test",
        ))

    def test_claim_from_pool_requires_notification(self):
        self.assertTrue(self.policy(
            action="claim",
            previous_owner="",
            recipient="tech.alfa@local.test",
        ))

    def test_controlled_handoff_requires_notification(self):
        self.assertTrue(self.policy(
            action="handoff",
            previous_owner="tech.alfa@local.test",
            recipient="tech.bravo@local.test",
        ))

    def test_unchanged_owner_does_not_notify(self):
        self.assertFalse(self.policy(
            action="assignment",
            previous_owner="tech.alfa@local.test",
            recipient="tech.alfa@local.test",
        ))

    def test_repair_does_not_notify(self):
        self.assertFalse(self.policy(
            action="repair",
            previous_owner="tech.alfa@local.test",
            recipient="tech.alfa@local.test",
        ))

    def test_new_assignment_after_release_notifies_again(self):
        self.assertTrue(self.policy(
            action="assignment",
            previous_owner="",
            recipient="tech.alfa@local.test",
        ))

    def test_missing_recipient_does_not_notify(self):
        self.assertFalse(self.policy(
            action="assignment",
            previous_owner="",
            recipient="",
        ))

    def test_unknown_action_does_not_notify(self):
        self.assertFalse(self.policy(
            action="unknown",
            previous_owner="",
            recipient="tech.alfa@local.test",
        ))


if __name__ == "__main__":
    unittest.main()
