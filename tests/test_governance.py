"""c1/c2/c4 as runtime data: scope, roles, module catalog, milestones."""
import unittest

from mvp import catalog, milestones, roles


class ScopeRolesTest(unittest.TestCase):
    def test_scope_has_in_and_out(self):
        self.assertIn("admissions", " ".join(
            roles.SCOPE["in_scope"]).lower())
        self.assertTrue(roles.SCOPE["out_of_scope"])

    def test_all_six_roles_defined(self):
        self.assertEqual(sorted(roles.ROLES),
                         ["accountant", "admin", "admissions_officer",
                          "parent", "student", "teacher"])

    def test_admin_has_every_permission(self):
        self.assertEqual(set(roles.ROLES["admin"]["permissions"]),
                         set(roles.PERMISSIONS))

    def test_every_permission_held_by_some_role(self):
        for perm in roles.PERMISSIONS:
            self.assertTrue(roles.roles_for(perm), perm)

    def test_check_grants_and_denies(self):
        roles.check("teacher", "grades.edit")
        with self.assertRaises(roles.PermissionDenied):
            roles.check("student", "grades.edit")
        with self.assertRaises(roles.PermissionDenied):
            roles.check("nobody", "grades.read")


class CatalogTest(unittest.TestCase):
    def test_six_core_modules(self):
        ids = [m["id"] for m in catalog.MODULES]
        self.assertEqual(sorted(ids), ["admissions", "attendance",
                                       "communication", "fees", "grades",
                                       "timetable"])

    def test_mvp_prioritized_p0_first(self):
        ordered = catalog.ordered_modules()
        self.assertTrue(all(m["mvp"] for m in ordered))
        prios = [m["priority"] for m in ordered]
        self.assertEqual(prios, sorted(prios))

    def test_each_module_has_mvp_slice_and_resources(self):
        for m in catalog.MODULES:
            self.assertTrue(m["mvp_features"], m["id"])
            self.assertTrue(m["resources"], m["id"])

    def test_get_module_unknown(self):
        with self.assertRaises(KeyError):
            catalog.get_module("payroll")


class MilestonesTest(unittest.TestCase):
    def test_four_milestones_cover_all_modules(self):
        covered = {m for ms in milestones.MILESTONES for m in ms["modules"]}
        self.assertEqual(covered, {m["id"] for m in catalog.MODULES})

    def test_legal_flow(self):
        milestones.check_transition("planned", "approved")
        milestones.check_transition("approved", "in_progress")
        milestones.check_transition("in_progress", "done")

    def test_illegal_transitions_rejected(self):
        with self.assertRaises(ValueError):
            milestones.check_transition("planned", "done")
        with self.assertRaises(ValueError):
            milestones.check_transition("done", "planned")


if __name__ == "__main__":
    unittest.main()
