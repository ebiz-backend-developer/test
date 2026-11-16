"""c4: delivery milestones with stakeholder approval."""
import unittest

from app import milestones as ms
from tests.helpers import make_service


class MilestoneTest(unittest.TestCase):
    def setUp(self):
        self.svc = make_service()

    def test_milestones_ordered_by_due_week(self):
        weeks = [m["due_week"] for m in self.svc.milestones()]
        self.assertEqual(weeks, sorted(weeks))
        self.assertEqual(len(weeks), 5)

    def test_start_as_draft(self):
        for m in self.svc.milestones():
            self.assertEqual(m["status"], "draft")

    def test_single_approval_proposes(self):
        m = self.svc.approve_milestone("M1", "admin", "Office")
        self.assertEqual(m["status"], "proposed")

    def test_dual_approval_approves(self):
        self.svc.approve_milestone("M1", "admin", "Office")
        m = self.svc.approve_milestone("M1", "parent", "PTA rep")
        self.assertEqual(m["status"], "approved")
        roles = {a["role"] for a in m["approvals"]}
        self.assertEqual(roles, {"admin", "parent"})

    def test_teacher_cannot_approve(self):
        with self.assertRaises(PermissionError):
            self.svc.approve_milestone("M1", "teacher", "Ms T")

    def test_student_cannot_approve(self):
        with self.assertRaises(PermissionError):
            self.svc.approve_milestone("M1", "student", "Stu")

    def test_unknown_milestone_rejected(self):
        with self.assertRaises(LookupError):
            self.svc.approve_milestone("M99", "admin", "Office")

    def test_blank_approver_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.approve_milestone("M1", "admin", "  ")

    def test_status_derivation(self):
        self.assertEqual(ms.next_status("draft", set()), "draft")
        self.assertEqual(ms.next_status("draft", {"admin"}), "proposed")
        self.assertEqual(ms.next_status("proposed", {"admin", "parent"}), "approved")
        with self.assertRaises(ValueError):
            ms.next_status("bogus", set())


if __name__ == "__main__":
    unittest.main()
