"""Pure transition planner tests: no database, site, or implicit clock."""

import copy
import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta, timezone

from telephony.time_booking_assignment_history import (
    AssignmentHistoryError,
    _ActiveAssignmentEpisode,
    _UNKNOWN_AUTHORITY,
    _plan_assignment_transition,
)
from telephony.time_booking_identity import TechnicianBookingIdentity


class TestAssignmentTransitionPlanner(unittest.TestCase):
    def setUp(self):
        self.a = TechnicianBookingIdentity("tech-a", "EMP-A", "Company")
        self.b = TechnicianBookingIdentity("tech-b", "EMP-B", "Company")
        self.at = datetime(2026, 11, 19, 10, 0, 0, 123456)
        self.episode = _ActiveAssignmentEpisode(
            "EP-A", self.a, self.at - timedelta(hours=1),
            self.at - timedelta(minutes=59))

    def plan(self, **updates):
        args = dict(previous_owner=self.a, new_owner=self.b,
                    active_episodes=[self.episode], at=self.at,
                    supported_transition=True)
        args.update(updates)
        return _plan_assignment_transition(**args)

    def test_initial_assignment(self):
        plan = self.plan(previous_owner=None, active_episodes=[])
        self.assertIsNone(plan.end_episode)
        self.assertEqual(plan.start_owner, self.b)
        self.assertFalse(plan.is_noop)

    def test_handoff(self):
        plan = self.plan()
        self.assertEqual(plan.end_episode, "EP-A")
        self.assertEqual(plan.start_owner, self.b)
        self.assertEqual(plan.at, self.at)
        self.assertFalse(plan.is_noop)

    def test_release(self):
        plan = self.plan(new_owner=None)
        self.assertEqual(plan.end_episode, "EP-A")
        self.assertIsNone(plan.start_owner)
        self.assertFalse(plan.is_noop)

    def test_same_owner_noop(self):
        plan = self.plan(new_owner=self.a)
        self.assertTrue(plan.is_noop)
        self.assertIsNone(plan.end_episode)
        self.assertIsNone(plan.start_owner)

    def test_redundant_same_owner_todo_cleanup_noop(self):
        # Normalization yields the same canonical owner, regardless of ToDo count.
        same_identity = TechnicianBookingIdentity("tech-a", "EMP-A", "Company")
        self.assertTrue(self.plan(new_owner=same_identity).is_noop)

    def test_unassigned_noop(self):
        self.assertTrue(self.plan(previous_owner=None, new_owner=None,
                                  active_episodes=()).is_noop)

    def test_cancelled_assignment_reopened(self):
        # Only active episodes are supplied; a closed episode cannot be reused.
        plan = self.plan(previous_owner=None, new_owner=self.a, active_episodes=[])
        self.assertIsNone(plan.end_episode)
        self.assertEqual(plan.start_owner, self.a)
        self.assertEqual(plan.at, self.at)

    def test_missing_episode_fails_for_release_handoff_and_noop(self):
        for new_owner in (None, self.a, self.b):
            with self.subTest(new_owner=new_owner), self.assertRaises(AssignmentHistoryError):
                self.plan(new_owner=new_owner, active_episodes=[])

    def test_conflicting_active_episodes(self):
        other = replace(self.episode, name="EP-B", identity=self.b)
        for episodes in ([self.episode, other], [self.episode, self.episode]):
            with self.subTest(episodes=episodes), self.assertRaises(AssignmentHistoryError):
                self.plan(active_episodes=episodes)

    def test_active_episode_without_prior_owner_fails(self):
        with self.assertRaises(AssignmentHistoryError):
            self.plan(previous_owner=None)

    def test_unknown_is_never_unassigned(self):
        for field in ("previous_owner", "new_owner"):
            with self.subTest(field=field), self.assertRaises(AssignmentHistoryError):
                self.plan(active_episodes=[], **{field: _UNKNOWN_AUTHORITY})
        self.assertTrue(self.plan(previous_owner=None, new_owner=None,
                                  active_episodes=[]).is_noop)

    def test_unknown_prior_with_matching_episode_still_fails(self):
        with self.assertRaises(AssignmentHistoryError):
            self.plan(previous_owner=_UNKNOWN_AUTHORITY)

    def test_invalid_owner_inputs(self):
        for owner in ("tech-a", {}, False, 0,
                      TechnicianBookingIdentity(" tech-a", "EMP-A", "Company"),
                      TechnicianBookingIdentity("tech-a", "", "Company"),
                      TechnicianBookingIdentity("tech-a", "EMP-A", None)):
            for field in ("previous_owner", "new_owner"):
                with self.subTest(owner=owner, field=field), self.assertRaises(AssignmentHistoryError):
                    self.plan(**{field: owner})

    def test_same_user_changed_identity_fails(self):
        for owner in (replace(self.a, employee="EMP-OTHER"),
                      replace(self.a, company="Other Company")):
            with self.subTest(owner=owner), self.assertRaises(AssignmentHistoryError):
                self.plan(new_owner=owner)

    def test_episode_identity_must_match_previous_owner(self):
        for identity in (self.b, replace(self.a, employee="other"),
                         replace(self.a, company="other"), None, "tech-a"):
            with self.subTest(identity=identity), self.assertRaises(AssignmentHistoryError):
                self.plan(active_episodes=[replace(self.episode, identity=identity)])

    def test_invalid_operation_timestamps(self):
        for at in (None, self.at.isoformat(), date(2026, 11, 19), 1,
                   self.at.replace(tzinfo=timezone.utc)):
            with self.subTest(at=at), self.assertRaises(AssignmentHistoryError):
                self.plan(at=at)

    def test_invalid_episode_timestamps(self):
        for field in ("effective_start", "recorded_start"):
            for value in (None, "2026-11-19 09:00:00", 1,
                          self.at.replace(tzinfo=timezone(timedelta(hours=2)))):
                with self.subTest(field=field, value=value), self.assertRaises(AssignmentHistoryError):
                    self.plan(active_episodes=[replace(self.episode, **{field: value})])

    def test_contradictory_timestamp_order(self):
        for episode in (
            replace(self.episode, effective_start=self.at),
            replace(self.episode, recorded_start=self.at + timedelta(microseconds=1)),
        ):
            with self.subTest(episode=episode), self.assertRaises(AssignmentHistoryError):
                self.plan(active_episodes=[episode])

    def test_exact_timestamp_preserved_for_all_decisions(self):
        for updates in ({}, {"new_owner": None}, {"new_owner": self.a},
                        {"previous_owner": None, "active_episodes": []}):
            with self.subTest(updates=updates):
                self.assertIs(self.plan(**updates).at, self.at)
                self.assertEqual(self.plan(**updates).at.microsecond, 123456)

    def test_end_at_start_is_allowed_without_inventing_duration(self):
        episode = replace(self.episode, effective_start=self.at, recorded_start=self.at)
        plan = self.plan(new_owner=None, active_episodes=[episode])
        self.assertEqual(plan.at, episode.effective_start)
        self.assertEqual(plan.end_episode, episode.name)

    def test_non_technician_transitions(self):
        # Caller maps known Partner/non-Technician ownership to None.
        self.assertEqual(self.plan(new_owner=None).end_episode, "EP-A")
        self.assertEqual(self.plan(previous_owner=None, active_episodes=[]).start_owner, self.b)
        self.assertTrue(self.plan(previous_owner=None, new_owner=None,
                                  active_episodes=[]).is_noop)

    def test_unsupported_or_malformed_support_flag_fails(self):
        for flag in (False, None, 0, 1, "true"):
            with self.subTest(flag=flag), self.assertRaises(AssignmentHistoryError):
                self.plan(supported_transition=flag)
        with self.assertRaises(AssignmentHistoryError):
            self.plan(previous_owner=None, new_owner=None, active_episodes=[],
                      supported_transition=False)

    def test_malformed_episode_collection_or_projection(self):
        for episodes in (None, {}, "", iter(()), [None], [dict(name="EP-A")],
                         [replace(self.episode, name="")],
                         [replace(self.episode, name=" EP-A")]):
            with self.subTest(episodes=episodes), self.assertRaises(AssignmentHistoryError):
                self.plan(active_episodes=episodes)

    def test_invalid_evidence_cannot_hide_in_noop(self):
        with self.assertRaises(AssignmentHistoryError):
            self.plan(new_owner=self.a,
                      active_episodes=[replace(self.episode, recorded_start=None)])

    def test_deterministic_and_input_immutable(self):
        episodes = [self.episode]
        before = copy.deepcopy(episodes)
        first = self.plan(active_episodes=episodes)
        self.assertEqual(first, self.plan(active_episodes=episodes))
        self.assertEqual(episodes, before)
        self.assertEqual(first, self.plan(active_episodes=tuple(episodes)))
        with self.assertRaises(FrozenInstanceError):
            first.end_episode = "different"
        with self.assertRaises(FrozenInstanceError):
            episodes[0].name = "different"


if __name__ == "__main__":
    unittest.main()
