"""Store tests: migrations, seed, CRUD and lifecycle rules."""
import os
import tempfile
import unittest

from app.models import (
    ConflictError,
    NewFlow,
    NewMilestone,
    NewModule,
    NewScopeItem,
    NewTechOption,
    NewWireframe,
    NotFoundError,
    ValidationError,
)
from app.seed import seed
from app.store import Store, connect, migrate


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mktemp(suffix=".db")
        self.conn = connect(self.tmp)
        migrate(self.conn)
        self.store = Store(self.conn)
        seed(self.store)

    def tearDown(self):
        self.conn.close()
        if os.path.exists(self.tmp):
            os.unlink(self.tmp)

    def test_migrations_are_idempotent(self):
        self.assertEqual(migrate(self.conn), [])

    def test_seed_counts_and_idempotent(self):
        counts = seed(self.store)
        self.assertEqual(sum(counts.values()), 0)
        self.assertEqual(len(self.store.list_roles()), 5)
        self.assertEqual(len(self.store.list_users()), 5)
        self.assertEqual(len(self.store.list_modules()), 8)

    def test_module_duplicate_name_conflicts(self):
        with self.assertRaises(ConflictError):
            self.store.add_module(NewModule(name="Identity & Access"))

    def test_module_validation(self):
        with self.assertRaises(ValidationError):
            self.store.add_module(NewModule(name="  "))
        with self.assertRaises(ValidationError):
            self.store.add_module(NewModule(name="X", priority="P9"))

    def test_prioritize_updates_order(self):
        mod = self.store.prioritize_module(8, "P0", True)
        self.assertEqual((mod["priority"], mod["mvp"], mod["sort_order"]),
                         ("P0", 1, 0))
        mvp = self.store.list_modules(mvp_only=True)
        self.assertIn("White-label Themes", [m["name"] for m in mvp])

    def test_update_module_status_rejects_bad_status(self):
        with self.assertRaises(ValidationError):
            self.store.update_module_status(1, "shipped")

    def test_missing_module_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            self.store.get_module(9999)

    def test_tech_select_supersedes_same_layer(self):
        before = [t for t in self.store.list_tech("frontend")
                  if t["status"] == "selected"]
        self.assertEqual(len(before), 1)
        new = self.store.add_tech(NewTechOption(layer="frontend", name="HTMX"))
        decided = self.store.decide_tech(new["id"], "selected", "simpler")
        self.assertEqual(decided["status"], "selected")
        selected = [t for t in self.store.list_tech("frontend")
                    if t["status"] == "selected"]
        self.assertEqual([t["id"] for t in selected], [new["id"]])

    def test_tech_double_decision_conflicts(self):
        opt = self.store.add_tech(NewTechOption(layer="data", name="DuckDB"))
        self.store.decide_tech(opt["id"], "rejected", "no")
        with self.assertRaises(ConflictError):
            self.store.decide_tech(opt["id"], "rejected", "again")

    def test_milestone_lifecycle(self):
        ms = self.store.add_milestone(NewMilestone(title="M9 Test"))
        self.assertEqual(ms["status"], "draft")
        # Cannot approve a draft.
        with self.assertRaises(ConflictError):
            self.store.decide_milestone(ms["id"], "approved", "sam")
        ms = self.store.submit_milestone(ms["id"])
        self.assertEqual(ms["status"], "proposed")
        # Cannot submit twice.
        with self.assertRaises(ConflictError):
            self.store.submit_milestone(ms["id"])
        ms = self.store.decide_milestone(ms["id"], "approved", "sam")
        self.assertEqual(ms["status"], "approved")
        self.assertEqual(ms["approved_by"], "sam")
        self.assertTrue(ms["approved_at"])
        # Terminal state: no further decisions.
        with self.assertRaises(ConflictError):
            self.store.decide_milestone(ms["id"], "rejected", "sam")

    def test_milestone_reject_records_decider(self):
        ms = self.store.add_milestone(NewMilestone(title="M9 Reject"))
        self.store.submit_milestone(ms["id"])
        ms = self.store.decide_milestone(ms["id"], "rejected", "ada")
        self.assertEqual((ms["status"], ms["decided_by"]), ("rejected", "ada"))

    def test_flow_validation(self):
        with self.assertRaises(ValidationError):
            self.store.add_flow(NewFlow(name="x", persona="y", steps=[]))
        with self.assertRaises(ValidationError):
            self.store.add_flow(NewFlow(name="x", persona="y",
                                        steps=[{"label": "  "}]))

    def test_flow_roundtrip(self):
        steps = [{"label": "A", "desc": "first", "next": ["B"]},
                 {"label": "B", "desc": "", "next": []}]
        flow = self.store.add_flow(NewFlow(name="F", persona="P", device="mobile",
                                           steps=steps))
        self.assertEqual(flow["steps"], steps)
        self.assertEqual(self.store.get_flow(flow["id"])["steps"], steps)

    def test_wireframe_requires_module(self):
        with self.assertRaises(NotFoundError):
            self.store.add_wireframe(NewWireframe(
                title="t", screen="s", module_id=9999,
                blocks=[{"type": "header", "label": "h"}]))

    def test_wireframe_block_validation(self):
        with self.assertRaises(ValidationError):
            self.store.add_wireframe(NewWireframe(
                title="t", screen="s", blocks=[{"type": "", "label": "x"}]))

    def test_dashboard_shape(self):
        dash = self.store.dashboard("designer")
        self.assertEqual(dash["role"], "designer")
        self.assertEqual(dash["counts"]["modules"], 8)
        self.assertEqual(len(dash["pending_approvals"]), 1)
        self.assertEqual(set(dash["milestones_by_status"]),
                         {"draft", "proposed", "approved", "rejected"})

    def test_scope_validation(self):
        with self.assertRaises(ValidationError):
            self.store.add_scope(NewScopeItem(title="t", kind="maybe"))


if __name__ == "__main__":
    unittest.main()
