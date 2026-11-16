"""c2: core modules and MVP prioritization."""
import unittest

from delivery import seed, service
from delivery.models import Module
from delivery.store import connect, migrate


def fresh():
    conn = connect(":memory:")
    migrate(conn)
    seed.seed(conn)
    return conn


class ModulesTest(unittest.TestCase):
    def test_create_and_duplicate_rejected(self):
        conn = fresh()
        created = service.create_module(conn, Module(name="New", priority="P1"), role="admin")
        self.assertEqual(created["status"], "backlog")
        with self.assertRaises(service.ValidationError):
            service.create_module(conn, Module(name="New"), role="admin")

    def test_non_owner_cannot_create(self):
        with self.assertRaises(service.AuthError):
            service.create_module(fresh(), Module(name="X"), role="developer")

    def test_unknown_and_self_dependency_rejected(self):
        conn = fresh()
        with self.assertRaises(service.ValidationError):
            service.create_module(conn, Module(name="A", depends_on=["Nope"]), role="admin")
        with self.assertRaises(service.ValidationError):
            service.create_module(conn, Module(name="B", depends_on=["B"]), role="admin")

    def test_cycle_rejected(self):
        conn = fresh()
        service.create_module(conn, Module(name="A"), role="admin")
        service.create_module(conn, Module(name="B", depends_on=["A"]), role="admin")
        a_id = next(m["id"] for m in service.list_modules(conn) if m["name"] == "A")
        with self.assertRaises(service.ValidationError):
            service.update_module_plan(conn, a_id, {"depends_on": ["B"]}, role="admin")

    def test_status_machine_enforced(self):
        conn = fresh()
        service.create_module(conn, Module(name="A"), role="admin")
        a_id = next(m["id"] for m in service.list_modules(conn) if m["name"] == "A")
        with self.assertRaises(service.ValidationError):  # no backlog -> done jump
            service.update_module_status(conn, a_id, "done", role="developer")
        service.update_module_status(conn, a_id, "planned", role="developer")
        service.update_module_status(conn, a_id, "in_progress", role="developer")
        done = service.update_module_status(conn, a_id, "done", role="developer")
        self.assertEqual(done["status"], "done")
        with self.assertRaises(service.AuthError):  # stakeholder is read-only
            service.update_module_status(conn, a_id, "in_progress", role="stakeholder")

    def test_done_requires_dependencies_done(self):
        conn = fresh()
        service.create_module(conn, Module(name="A"), role="admin")
        service.create_module(conn, Module(name="B", depends_on=["A"]), role="admin")
        by_name = {m["name"]: m["id"] for m in service.list_modules(conn)}
        for step in ("planned", "in_progress"):
            service.update_module_status(conn, by_name["B"], step, role="admin")
        with self.assertRaises(service.ValidationError):
            service.update_module_status(conn, by_name["B"], "done", role="admin")

    def test_mvp_order_and_readiness(self):
        conn = fresh()
        mods = service.mvp_modules(conn)
        self.assertTrue(all(m["mvp"] for m in mods))
        ranks = [{"P0": 0, "P1": 1, "P2": 2}[m["priority"]] for m in mods]
        self.assertEqual(ranks, sorted(ranks))
        readiness = service.mvp_readiness(conn)
        total = sum(m["effort_points"] for m in mods)
        done = sum(m["effort_points"] for m in mods if m["status"] == "done")
        self.assertEqual(readiness["total_points"], total)
        self.assertEqual(readiness["done_points"], done)
        self.assertAlmostEqual(readiness["percent"], round(100 * done / total, 1))

    def test_build_order_respects_dependencies(self):
        conn = fresh()
        order = service.build_order(conn)
        pos = {name: i for i, name in enumerate(order)}
        for m in service.list_modules(conn):
            for dep in m["depends_on"]:
                self.assertLess(pos[dep], pos[m["name"]])


if __name__ == "__main__":
    unittest.main()
