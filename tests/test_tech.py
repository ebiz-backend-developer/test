"""Tech stack: propose/select/reject with supersede rule. (c3)"""
import unittest

from app import service
from app.seed import seed
from app.store import Store


class TestTech(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        seed(self.store)

    def tearDown(self):
        self.store.close()

    def test_seed_stack_has_one_selection_per_category(self):
        stack = service.selected_stack(self.store)
        categories = [t["category"] for t in stack]
        self.assertEqual(len(categories), len(set(categories)))
        self.assertGreaterEqual(len(stack), 5)
        names = " ".join(t["name"] for t in stack).lower()
        self.assertIn("monolith", names)

    def test_propose_then_select(self):
        option = service.propose_tech(
            self.store, "Ivan", "it_support", "Database", "SQLite-cluster",
            detail="embedded test entry", rationale="cheap local option")
        self.assertEqual(option["status"], "proposed")
        selected = service.select_tech(
            self.store, "Ada", "principal", option["id"],
            rationale="fits the pilot")
        self.assertEqual(selected["status"], "selected")
        self.assertEqual(selected["rationale"], "fits the pilot")

    def test_select_supersedes_previous_choice_in_category(self):
        option = service.propose_tech(
            self.store, "Ivan", "it_support", "Database", "SQLite-cluster")
        service.select_tech(self.store, "Ada", "principal", option["id"])
        rows = service.list_tech(self.store, category="Database")
        selected = [r for r in rows if r["status"] == "selected"]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["name"], "SQLite-cluster")
        old = [r for r in rows if r["name"] == "PostgreSQL (managed)"][0]
        self.assertEqual(old["status"], "rejected")
        self.assertIn("superseded by", old["rationale"])

    def test_select_needs_approver_role(self):
        option = service.propose_tech(
            self.store, "Tom", "teacher", "Database", "SQLite-cluster")
        with self.assertRaises(service.ServiceError) as ctx:
            service.select_tech(self.store, "Tom", "teacher", option["id"])
        self.assertEqual(ctx.exception.status, 403)

    def test_student_cannot_propose(self):
        with self.assertRaises(service.ServiceError) as ctx:
            service.propose_tech(
                self.store, "Stacy", "student", "Database", "Files")
        self.assertEqual(ctx.exception.status, 403)

    def test_duplicate_proposal_rejected(self):
        service.propose_tech(
            self.store, "Ivan", "it_support", "Database", "SQLite-cluster")
        with self.assertRaises(service.ServiceError):
            service.propose_tech(
                self.store, "Ivan", "it_support", "Database", "SQLite-cluster")

    def test_rejected_option_cannot_be_selected(self):
        option = service.propose_tech(
            self.store, "Ivan", "it_support", "Database", "SQLite-cluster")
        service.reject_tech(self.store, "Ada", "principal", option["id"],
                            rationale="no clustering story")
        with self.assertRaises(service.ServiceError):
            service.select_tech(self.store, "Ada", "principal", option["id"])

    def test_selected_option_cannot_be_rejected_outright(self):
        current = service.list_tech(
            self.store, category="Database", status="selected")[0]
        with self.assertRaises(service.ServiceError):
            service.reject_tech(self.store, "Ada", "principal", current["id"])


if __name__ == "__main__":
    unittest.main()
