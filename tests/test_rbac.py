"""RBAC matrix tests (c1): every action, every role."""
import unittest

from app.rbac import PERMISSIONS, ROLE_DESCRIPTIONS, can, role_permissions


class RbacTest(unittest.TestCase):
    def test_all_roles_documented(self):
        self.assertEqual(
            set(ROLE_DESCRIPTIONS),
            {"admin", "product_manager", "designer", "developer", "stakeholder"},
        )

    def test_admin_can_do_everything(self):
        for action in PERMISSIONS:
            self.assertTrue(can("admin", action), action)

    def test_product_manager_scope(self):
        for action in ("scope.write", "modules.write", "modules.status",
                       "tech.propose", "tech.select", "milestones.propose",
                       "flows.write"):
            self.assertTrue(can("product_manager", action), action)
        self.assertFalse(can("product_manager", "milestones.approve"))
        self.assertFalse(can("product_manager", "wireframes.write"))

    def test_designer_scope(self):
        self.assertTrue(can("designer", "flows.write"))
        self.assertTrue(can("designer", "wireframes.write"))
        for action in ("modules.write", "tech.select", "milestones.approve",
                       "scope.write"):
            self.assertFalse(can("designer", action), action)

    def test_developer_scope(self):
        self.assertTrue(can("developer", "modules.status"))
        self.assertTrue(can("developer", "tech.propose"))
        self.assertFalse(can("developer", "modules.write"))
        self.assertFalse(can("developer", "tech.select"))
        self.assertFalse(can("developer", "milestones.approve"))

    def test_stakeholder_approves_but_does_not_edit(self):
        self.assertTrue(can("stakeholder", "milestones.approve"))
        for action in ("modules.write", "tech.select", "flows.write",
                       "wireframes.write", "milestones.propose"):
            self.assertFalse(can("stakeholder", action), action)

    def test_unknown_role_and_action_denied(self):
        self.assertFalse(can(None, "modules.write"))
        self.assertFalse(can("admin", "nope.action"))
        self.assertFalse(can("visitor", "modules.write"))

    def test_role_permissions_consistent_with_matrix(self):
        for role in ROLE_DESCRIPTIONS:
            expected = sorted(a for a, rs in PERMISSIONS.items() if role in rs)
            self.assertEqual(role_permissions(role), expected)


if __name__ == "__main__":
    unittest.main()
