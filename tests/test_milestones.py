"""Milestones: propose/decide/track with approval gate. (c4)"""
import unittest

from app import service
from app.seed import seed
from app.store import Store


class TestMilestones(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        seed(self.store)

    def tearDown(self):
        self.store.close()

    def test_seed_milestones_m0_to_m4(self):
        codes = [m["code"] for m in service.list_milestones(self.store)]
        self.assertEqual(codes, ["M0", "M1", "M2", "M3", "M4"])
        for milestone in service.list_milestones(self.store):
            self.assertTrue(milestone["exit_criteria"], milestone["code"])

    def test_full_lifecycle_propose_approve_track_done(self):
        milestone = service.propose_milestone(
            self.store, "Rita", "registrar", "M5", "Phase 2 kickoff",
            goal="Start staff module", exit_criteria="M7 planned")
        self.assertEqual(milestone["status"], "proposed")
        decided = service.decide_milestone(
            self.store, "Ada", "principal", "M5", "approved",
            note="scope agreed")
        self.assertEqual(decided["status"], "approved")
        self.assertEqual(decided["approved_by"], "Ada")
        tracked = service.track_milestone(
            self.store, "Ada", "principal", "M5", "in_progress")
        self.assertEqual(tracked["status"], "in_progress")
        done = service.track_milestone(
            self.store, "Ada", "principal", "M5", "done")
        self.assertEqual(done["status"], "done")

    def test_approval_gate_roles(self):
        with self.assertRaises(service.ServiceError) as ctx:
            service.decide_milestone(
                self.store, "Tom", "teacher", "M1", "approved")
        self.assertEqual(ctx.exception.status, 403)
        with self.assertRaises(service.ServiceError):
            service.propose_milestone(
                self.store, "Tom", "teacher", "M9", "Side quest")

    def test_rejection_needs_a_note(self):
        with self.assertRaises(service.ServiceError):
            service.decide_milestone(
                self.store, "Ada", "principal", "M1", "rejected")
        rejected = service.decide_milestone(
            self.store, "Ada", "principal", "M1", "rejected",
            note="M2 exit criteria overlap; merge them")
        self.assertEqual(rejected["status"], "rejected")

    def test_double_decision_rejected(self):
        service.decide_milestone(
            self.store, "Ada", "principal", "M1", "approved")
        with self.assertRaises(service.ServiceError):
            service.decide_milestone(
                self.store, "Ada", "principal", "M1", "approved")

    def test_tracking_cannot_skip_or_go_backwards(self):
        with self.assertRaises(service.ServiceError):
            service.track_milestone(
                self.store, "Ada", "principal", "M1", "done")
        with self.assertRaises(service.ServiceError):
            service.track_milestone(
                self.store, "Ada", "principal", "M1", "approved")
        service.decide_milestone(
            self.store, "Ada", "principal", "M1", "approved")
        service.track_milestone(
            self.store, "Ada", "principal", "M1", "in_progress")
        with self.assertRaises(service.ServiceError):
            service.track_milestone(
                self.store, "Ada", "principal", "M1", "in_progress")

    def test_decision_records_approval_and_audit(self):
        service.decide_milestone(
            self.store, "Ada", "principal", "M2", "approved", note="go")
        milestones = {m["code"]: m
                      for m in service.list_milestones(self.store)}
        self.assertEqual(len(milestones["M2"]["approvals"]), 1)
        self.assertEqual(milestones["M2"]["approvals"][0]["actor"], "Ada")
        actions = [a["action"] for a in service.list_audit(self.store)]
        self.assertIn("milestones.approved", actions)

    def test_duplicate_code_rejected(self):
        with self.assertRaises(service.ServiceError):
            service.propose_milestone(
                self.store, "Ada", "principal", "M1", "Duplicate")


if __name__ == "__main__":
    unittest.main()
