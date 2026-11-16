"""RBAC matrix: grants, denials, deny-by-default. (c1)"""
import unittest

from app import rbac


class TestRbac(unittest.TestCase):
    def test_principal_can_approve_milestones(self):
        self.assertTrue(rbac.can("principal", "milestones.approve"))
        self.assertTrue(rbac.can("sysadmin", "milestones.approve"))

    def test_teacher_cannot_approve_milestones(self):
        self.assertFalse(rbac.can("teacher", "milestones.approve"))
        self.assertFalse(rbac.can("student", "milestones.approve"))
        self.assertFalse(rbac.can("parent", "milestones.approve"))

    def test_approval_steps_need_approver_action(self):
        # Grade publishing / offer / waiver steps require an approval-level
        # action, which front-line roles lack.
        self.assertFalse(rbac.can("teacher", "milestones.approve"))
        self.assertFalse(rbac.can("registrar", "milestones.approve"))
        self.assertFalse(rbac.can("accountant", "milestones.approve"))

    def test_every_school_role_can_run_workflows(self):
        for role in ("registrar", "teacher", "class_teacher", "accountant",
                     "office_staff", "student", "parent"):
            self.assertTrue(rbac.can(role, "workflows.run"), role)

    def test_only_admins_manage_workflow_definitions(self):
        self.assertTrue(rbac.can("sysadmin", "workflows.manage"))
        self.assertTrue(rbac.can("principal", "workflows.manage"))
        self.assertFalse(rbac.can("teacher", "workflows.manage"))

    def test_tech_selection_is_restricted_but_proposals_are_open(self):
        self.assertTrue(rbac.can("teacher", "tech.propose"))
        self.assertTrue(rbac.can("it_support", "tech.propose"))
        self.assertFalse(rbac.can("teacher", "tech.select"))
        self.assertFalse(rbac.can("student", "tech.propose"))

    def test_module_priority_vs_status_split(self):
        self.assertTrue(rbac.can("principal", "modules.write"))
        self.assertFalse(rbac.can("registrar", "modules.write"))
        self.assertTrue(rbac.can("registrar", "modules.status"))
        self.assertFalse(rbac.can("teacher", "modules.status"))

    def test_unknown_role_and_action_denied(self):
        self.assertFalse(rbac.can("superuser", "milestones.approve"))
        self.assertFalse(rbac.can("principal", "nuclear.launch"))
        self.assertFalse(rbac.can(None, "workflows.run"))

    def test_role_permissions_lists_grants(self):
        perms = rbac.role_permissions("student")
        self.assertEqual(perms, ["workflows.run"])
        self.assertIn("scope.write", rbac.role_permissions("office_staff"))
        self.assertEqual(rbac.role_permissions(None), [])

    def test_all_seed_roles_known(self):
        for role in ("sysadmin", "principal", "registrar", "teacher",
                     "class_teacher", "accountant", "office_staff",
                     "student", "parent", "it_support"):
            self.assertTrue(rbac.known_role(role), role)


if __name__ == "__main__":
    unittest.main()
