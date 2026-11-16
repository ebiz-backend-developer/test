"""Modules & MVP slice: seeded catalog, priority moves, exit rule. (c2)"""
import unittest

from app import service
from app.seed import seed
from app.store import Store


class TestModulesMvp(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        seed(self.store)

    def tearDown(self):
        self.store.close()

    def test_seed_catalog_covers_core_modules(self):
        codes = [m["code"] for m in service.list_modules(self.store)]
        self.assertEqual(len(codes), 11)
        titles = " ".join(
            m["title"] for m in service.list_modules(self.store)).lower()
        for word in ("identity", "admissions", "attendance", "academics",
                     "fees", "communication"):
            self.assertIn(word, titles)

    def test_mvp_is_exactly_p0(self):
        mvp = service.mvp_modules(self.store)
        self.assertEqual([m["code"] for m in mvp],
                         ["M1", "M2", "M3", "M4", "M5", "M6"])
        summary = service.mvp_summary(self.store)
        self.assertEqual(summary["total"], 6)
        self.assertFalse(summary["complete"])
        self.assertIn("admit students", summary["exit_rule"])

    def test_priority_move_changes_phase_and_mvp(self):
        updated = service.update_module(
            self.store, "Ada", "principal", "M7", priority="P0")
        self.assertEqual(updated["phase"], "MVP")
        self.assertIn("M7", [m["code"]
                             for m in service.mvp_modules(self.store)])
        updated = service.update_module(
            self.store, "Ada", "principal", "M6", priority="P2")
        self.assertEqual(updated["phase"], "Phase 3")
        self.assertNotIn("M6", [m["code"]
                                for m in service.mvp_modules(self.store)])

    def test_priority_change_needs_write_role(self):
        with self.assertRaises(service.ServiceError) as ctx:
            service.update_module(
                self.store, "Tom", "teacher", "M7", priority="P0")
        self.assertEqual(ctx.exception.status, 403)
        # Registrar may update status but not priority.
        updated = service.update_module(
            self.store, "Rita", "registrar", "M2", status="in_progress")
        self.assertEqual(updated["status"], "in_progress")

    def test_invalid_priority_status_and_empty_update_rejected(self):
        with self.assertRaises(service.ServiceError):
            service.update_module(
                self.store, "Ada", "principal", "M7", priority="P9")
        with self.assertRaises(service.ServiceError):
            service.update_module(
                self.store, "Ada", "principal", "M7", status="shipped")
        with self.assertRaises(service.ServiceError):
            service.update_module(self.store, "Ada", "principal", "M7")

    def test_unknown_module_is_404(self):
        with self.assertRaises(service.ServiceError) as ctx:
            service.update_module(
                self.store, "Ada", "principal", "M99", status="done")
        self.assertEqual(ctx.exception.status, 404)

    def test_mvp_completes_when_all_p0_done(self):
        for module in service.mvp_modules(self.store):
            service.update_module(
                self.store, "Ada", "principal", module["code"], status="done")
        summary = service.mvp_summary(self.store)
        self.assertTrue(summary["complete"])
        self.assertEqual(summary["done"], summary["total"])


if __name__ == "__main__":
    unittest.main()
