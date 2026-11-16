"""c3: architecture and tech-stack selection."""
import unittest

from delivery import seed, service
from delivery.models import ArchDecision
from delivery.store import connect, migrate


def fresh():
    conn = connect(":memory:")
    migrate(conn)
    seed.seed(conn)
    return conn


class ArchTest(unittest.TestCase):
    def test_seeded_stack_decided(self):
        summary = service.stack_summary(fresh())
        self.assertTrue(summary["decided"])
        self.assertEqual(summary["pending_categories"], [])
        self.assertEqual(len(summary["stack"]), 6)

    def test_propose_select_reject_flow(self):
        conn = fresh()
        proposed = service.propose_arch(
            conn, ArchDecision(category="database", option_name="CockroachDB"), role="tech_lead"
        )
        self.assertEqual(proposed["status"], "proposed")
        with self.assertRaises(service.ValidationError):  # rationale required
            service.select_arch(conn, proposed["id"], " ", role="tech_lead")
        with self.assertRaises(service.ValidationError):  # SQLite already selected
            service.select_arch(conn, proposed["id"], "rational", role="tech_lead")
        current = next(
            d for d in service.list_arch(conn)
            if d["category"] == "database" and d["status"] == "selected"
        )
        service.reject_arch(conn, current["id"], role="tech_lead")
        selected = service.select_arch(conn, proposed["id"], "fits", role="tech_lead")
        self.assertEqual(selected["status"], "selected")
        self.assertEqual(selected["decided_by"], "tech_lead")

    def test_only_owner_roles_write_architecture(self):
        conn = fresh()
        with self.assertRaises(service.AuthError):
            service.propose_arch(
                conn, ArchDecision(category="database", option_name="X"), role="developer"
            )
        with self.assertRaises(service.AuthError):
            service.propose_arch(
                conn, ArchDecision(category="database", option_name="X"), role="product_owner"
            )

    def test_unknown_category_and_duplicate_rejected(self):
        conn = fresh()
        with self.assertRaises(service.ValidationError):
            service.propose_arch(
                conn, ArchDecision(category="starship", option_name="X"), role="admin"
            )
        with self.assertRaises(service.ValidationError):
            service.propose_arch(
                conn, ArchDecision(category="language", option_name="Python 3.12"),
                role="admin",
            )

    def test_rejecting_selected_reopens_category(self):
        conn = fresh()
        current = next(
            d for d in service.list_arch(conn)
            if d["category"] == "auth" and d["status"] == "selected"
        )
        service.reject_arch(conn, current["id"], role="admin")
        summary = service.stack_summary(conn)
        self.assertFalse(summary["decided"])
        self.assertIn("auth", summary["pending_categories"])


if __name__ == "__main__":
    unittest.main()
