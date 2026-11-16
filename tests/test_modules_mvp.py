"""c2: core modules and MVP prioritization."""
import unittest

from app import modules as mods
from tests.helpers import make_service


class ModulesTest(unittest.TestCase):
    def setUp(self):
        self.svc = make_service()

    def test_core_modules_present(self):
        ids = {m["id"] for m in self.svc.modules()}
        self.assertTrue({"admissions", "attendance", "grades", "timetable",
                         "fees", "communication"} <= ids)

    def test_mvp_contains_p0_and_p1_only(self):
        for m in self.svc.mvp():
            self.assertIn(m["priority"], (0, 1))

    def test_mvp_excludes_p2(self):
        mvp_ids = {m["id"] for m in self.svc.mvp()}
        p2 = {m["id"] for m in self.svc.modules() if m["priority"] == 2}
        self.assertTrue(p2)
        self.assertFalse(mvp_ids & p2)

    def test_mvp_respects_dependencies(self):
        mvp = self.svc.mvp()
        position = {m["id"]: i for i, m in enumerate(mvp)}
        for m in mvp:
            for dep in m["depends_on"]:
                if dep in position:
                    self.assertLess(position[dep], position[m["id"]])

    def test_reprioritize_moves_module_in_and_out_of_mvp(self):
        self.svc.set_module_priority("communication", 1)
        self.assertIn("communication", {m["id"] for m in self.svc.mvp()})
        self.svc.set_module_priority("communication", 2)
        self.assertNotIn("communication", {m["id"] for m in self.svc.mvp()})

    def test_invalid_priority_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.set_module_priority("fees", 5)

    def test_unknown_module_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.set_module_priority("teleportation", 1)

    def test_dependency_cycle_detected(self):
        cyclic = [
            {"id": "a", "priority": 0, "moscow": "must", "depends_on": ["b"]},
            {"id": "b", "priority": 0, "moscow": "must", "depends_on": ["a"]},
        ]
        with self.assertRaises(ValueError):
            mods.order_by_dependency(cyclic)


if __name__ == "__main__":
    unittest.main()
