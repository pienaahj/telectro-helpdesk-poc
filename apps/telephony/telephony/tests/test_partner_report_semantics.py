import unittest
from unittest import mock

from telephony.ftelephony.report.first_response_missed import (
    first_response_missed,
)
from telephony.ftelephony.report.supervisor_team_snapshot import (
    supervisor_team_snapshot,
)


class TestSupervisorTeamSnapshotPartnerSemantics(unittest.TestCase):
    def test_partner_exclusion_uses_fulfilment_party(self):
        with mock.patch.object(
            supervisor_team_snapshot,
            "frappe",
        ) as frappe_mock:
            frappe_mock.db.sql.return_value = []

            supervisor_team_snapshot.get_data(
                include_partner=0,
                stale_hours=24,
            )

        sql = frappe_mock.db.sql.call_args.args[0]

        self.assertIn(
            "COALESCE(h.custom_fulfilment_party, '') != 'Partner'",
            sql,
        )
        self.assertNotIn(
            "partner@local.test",
            sql,
        )


class TestFirstResponseMissedPartnerSemantics(unittest.TestCase):
    def test_partner_bucket_has_no_legacy_dispatch_user_fallback(self):
        with mock.patch.object(
            first_response_missed,
            "frappe",
        ) as frappe_mock:
            frappe_mock.db.sql.return_value = []

            first_response_missed.get_data()

        sql = frappe_mock.db.sql.call_args.args[0]

        self.assertIn(
            "COALESCE(custom_fulfilment_party, '') = 'Partner'",
            sql,
        )
        self.assertNotIn(
            "partner@local.test",
            sql,
        )


if __name__ == "__main__":
    unittest.main()
