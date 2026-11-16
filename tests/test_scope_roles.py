"""c1: scope and user roles defined and enforced."""
import unittest

from app import rbac
from tests.helpers import make_service


class ScopeTest(unittest.TestCase):
    def setUp(self):
        self.svc = make_service()

    def test_scope_has_in_and_out(self):
        scope = self.svc.scope()
        self.assertTrue(scope["in_scope"])
        self.assertTrue(scope["out_of_scope"])
        self.assertIn("Student enrollment and profiles", scope["in_scope"])

    def test_four_roles_defined(self):
        roles = {r["name"] for r in self.svc.roles()}
        self.assertEqual(roles, {"admin", "teacher", "student", "parent"})

    def test_stakeholders_cover_every_role(self):
        covered = {s["role"] for s in self.svc.stakeholders()}
        self.assertEqual(covered, {"admin", "teacher", "student", "parent"})


class RbacTest(unittest.TestCase):
    def setUp(self):
        self.svc = make_service()

    def test_admin_can_manage_users(self):
        res = self.svc.check_access("admin", "users.manage")
        self.assertTrue(res["allowed"])

    def test_student_cannot_enter_grades(self):
        res = self.svc.check_access("student", "grades.enter")
        self.assertFalse(res["allowed"])

    def test_teacher_cannot_approve_milestones(self):
        res = self.svc.check_access("teacher", "milestones.approve")
        self.assertFalse(res["allowed"])

    def test_parent_can_pay_but_not_invoice(self):
        self.assertTrue(self.svc.check_access("parent", "fees.pay")["allowed"])
        self.assertFalse(self.svc.check_access("parent", "fees.invoice")["allowed"])

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.check_access("ghost", "grades.view")

    def test_unknown_permission_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.check_access("admin", "nope.nope")

    def test_pure_matrix_matches_service(self):
        for role in rbac.ROLES:
            for perm in rbac.PERMISSIONS:
                self.assertEqual(
                    self.svc.check_access(role, perm)["allowed"],
                    rbac.can(role, perm), f"{role}/{perm}")


if __name__ == "__main__":
    unittest.main()
