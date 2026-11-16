"""Service + store tests: roles, scope, modules/MVP, arch, milestones, risks, approvals."""
import sqlite3
import unittest

from delivery import service
from delivery.models import (
    AcceptanceCriterion,
    Approval,
    ArchDecision,
    Milestone,
    Module,
    Risk,
    Scope,
)
from delivery.seed import seed
from delivery.store import SCHEMA_VERSION, current_version, init_db


def fresh_db() -> sqlite3.Connection:
    conn = init_db(":memory:")
    seed(conn)
    return conn


class TestMigrations(unittest.TestCase):
    def test_migrate_reaches_schema_version_and_is_idempotent(self):
        conn = init_db(":memory:")
        self.assertEqual(current_version(conn), SCHEMA_VERSION)
        tables = {r["name"] for r in
                  conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for expected in ("roles", "scopes", "modules", "arch_decisions", "milestones",
                         "risks", "acceptance_criteria", "approvals", "schema_migrations"):
            self.assertIn(expected, tables)
        # Second migrate is a no-op.
        from delivery.store import migrate
        self.assertEqual(migrate(conn), SCHEMA_VERSION)

    def test_seed_is_idempotent(self):
        conn = fresh_db()
        before = conn.execute("SELECT COUNT(*) AS c FROM milestones").fetchone()["c"]
        added = seed(conn)
        after = conn.execute("SELECT COUNT(*) AS c FROM milestones").fetchone()["c"]
        self.assertEqual(before, after)
        self.assertEqual(sum(added.values()), 0)


class TestRolesAndScope(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()

    def test_five_roles_seeded(self):
        roles = service.list_roles(self.conn)
        self.assertEqual({r["name"] for r in roles},
                         {"admin", "product_owner", "tech_lead", "developer", "stakeholder"})

    def test_unknown_role_rejected(self):
        with self.assertRaises(service.AuthError):
            service.require_role("intruder")

    def test_scope_roundtrip(self):
        scope = service.get_scope(self.conn)
        self.assertTrue(scope["vision"])
        self.assertGreaterEqual(len(scope["in_scope"]), 1)

    def test_stakeholder_cannot_write_scope(self):
        with self.assertRaises(service.AuthError):
            service.save_scope(self.conn, Scope(vision="v", in_scope=["x"]), "stakeholder")
        with self.assertRaises(service.AuthError):
            service.save_scope(self.conn, Scope(vision="v", in_scope=["x"]), "developer")

    def test_product_owner_can_write_scope(self):
        out = service.save_scope(self.conn, Scope(vision="new vision", in_scope=["a"]), "product_owner")
        self.assertEqual(out["vision"], "new vision")
        self.assertEqual(service.get_scope(self.conn)["vision"], "new vision")

    def test_invalid_scope_rejected(self):
        with self.assertRaises(service.ValidationError):
            service.save_scope(self.conn, Scope(vision="", in_scope=["x"]), "admin")


class TestModulesMvp(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()

    def test_mvp_summary_counts(self):
        summary = service.mvp_summary(self.conn)
        self.assertGreaterEqual(summary["total"], 1)
        self.assertTrue(all(m["mvp"] for m in summary["modules"]))
        self.assertEqual(summary["points"], sum(m["effort_points"] for m in summary["modules"]))

    def test_create_and_prioritize(self):
        created = service.create_module(
            self.conn, Module(name="search", priority="P1", mvp=True, effort_points=2), "product_owner")
        self.assertEqual(created["name"], "search")
        names = [m["name"] for m in service.list_modules(self.conn, mvp_only=True)]
        self.assertIn("search", names)

    def test_duplicate_name_rejected(self):
        with self.assertRaises(service.ValidationError):
            service.create_module(self.conn, Module(name="module-registry"), "admin")

    def test_unknown_dependency_rejected(self):
        with self.assertRaises(service.ValidationError):
            service.create_module(self.conn, Module(name="x", depends_on=["ghost"]), "admin")

    def test_developer_can_advance_status_but_not_reprioritize(self):
        mod = service.create_module(self.conn, Module(name="devmod"), "admin")
        out = service.update_module(self.conn, mod["id"], {"status": "in_progress"}, "developer")
        self.assertEqual(out["status"], "in_progress")
        with self.assertRaises(service.AuthError):
            service.update_module(self.conn, mod["id"], {"priority": "P0"}, "developer")

    def test_stakeholder_cannot_touch_modules(self):
        mod = service.list_modules(self.conn)[0]
        with self.assertRaises(service.AuthError):
            service.update_module(self.conn, mod["id"], {"status": "done"}, "stakeholder")


class TestArchitecture(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()

    def test_selected_stack_present(self):
        stack = service.list_arch(self.conn, selected_only=True)
        self.assertGreaterEqual(len(stack), 1)
        cats = {d["category"] for d in stack}
        self.assertIn("language", cats)

    def test_selecting_demotes_previous(self):
        service.save_arch(self.conn, ArchDecision(
            category="datastore", option_name="PostgreSQL", status="selected",
            rationale="scale up"), "tech_lead")
        selected = [d for d in service.list_arch(self.conn) if d["category"] == "datastore" and d["status"] == "selected"]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["option_name"], "PostgreSQL")

    def test_product_owner_cannot_set_stack(self):
        with self.assertRaises(service.AuthError):
            service.save_arch(self.conn, ArchDecision(
                category="language", option_name="cobol", status="proposed"), "product_owner")

    def test_select_without_rationale_rejected(self):
        with self.assertRaises(service.ValidationError):
            service.save_arch(self.conn, ArchDecision(
                category="ui", option_name="x", status="selected"), "tech_lead")


class TestMilestonesRisksApprovals(unittest.TestCase):
    def setUp(self):
        self.conn = fresh_db()
        self.m2 = next(m for m in service.list_milestones(self.conn) if m["name"] == "M2 MVP backend")

    def test_m1_seeded_as_approved(self):
        m1 = next(m for m in service.list_milestones(self.conn) if m["name"].startswith("M1"))
        self.assertEqual(m1["status"], "approved")
        approvals = service.list_approvals(self.conn, m1["id"])
        self.assertEqual(len(approvals), 1)
        self.assertEqual(approvals[0]["decision"], "approved")

    def test_cannot_approve_unready_milestone(self):
        with self.assertRaises(service.ValidationError) as ctx:
            service.record_approval(self.conn, Approval(
                milestone_id=self.m2["id"], approver_role="product_owner",
                decision="approved"), "product_owner")
        self.assertIn("not ready", str(ctx.exception))

    def test_full_approval_flow(self):
        mid = self.m2["id"]
        # Meet every criterion.
        for criterion in service.list_criteria(self.conn, mid):
            service.save_criterion(self.conn, AcceptanceCriterion(
                id=criterion["id"], milestone_id=mid, description=criterion["description"],
                verification_method=criterion["verification_method"], status="met"), "developer")
        # Close or mitigate high-exposure risks.
        for risk in service.list_risks(self.conn, mid):
            if risk["status"] != "closed":
                service.save_risk(self.conn, Risk(
                    id=risk["id"], milestone_id=mid, title=risk["title"],
                    likelihood=risk["likelihood"], impact=risk["impact"],
                    mitigation=risk["mitigation"] or "handled", status="closed"), "developer")
        ready = service.readiness(self.conn, mid)
        self.assertTrue(ready["ready"])
        approval = service.record_approval(self.conn, Approval(
            milestone_id=mid, approver_role="product_owner", decision="approved",
            comment="M2 exit"), "product_owner")
        self.assertEqual(approval["decision"], "approved")
        self.assertEqual(service.get_milestone(self.conn, mid)["status"], "approved")

    def test_high_exposure_risk_blocks_approval(self):
        mid = self.m2["id"]
        service.save_risk(self.conn, Risk(
            milestone_id=mid, title="blocker", likelihood="high", impact="high",
            mitigation="plan in place", status="open"), "tech_lead")
        with self.assertRaises(service.ValidationError):
            service.record_approval(self.conn, Approval(
                milestone_id=mid, approver_role="product_owner", decision="approved"), "product_owner")

    def test_developer_cannot_approve(self):
        with self.assertRaises(service.AuthError):
            service.record_approval(self.conn, Approval(
                milestone_id=self.m2["id"], approver_role="developer",
                decision="approved"), "developer")

    def test_changes_requested_allowed_when_unready(self):
        out = service.record_approval(self.conn, Approval(
            milestone_id=self.m2["id"], approver_role="product_owner",
            decision="changes_requested", comment="finish criteria first"), "product_owner")
        self.assertEqual(out["decision"], "changes_requested")

    def test_approved_milestone_locked_for_non_admin(self):
        m1 = next(m for m in service.list_milestones(self.conn) if m["name"].startswith("M1"))
        with self.assertRaises(service.AuthError):
            service.update_milestone(self.conn, m1["id"], {"status": "in_progress"}, "product_owner")
        out = service.update_milestone(self.conn, m1["id"], {"status": "in_progress"}, "admin")
        self.assertEqual(out["status"], "in_progress")

    def test_criterion_requires_existing_milestone(self):
        with self.assertRaises(service.ValidationError):
            service.save_criterion(self.conn, AcceptanceCriterion(
                milestone_id=99999, description="ghost"), "admin")

    def test_roadmap_rollup(self):
        roadmap = service.roadmap(self.conn)
        self.assertEqual(len(roadmap["phases"]), 5)
        total = sum(p["total"] for p in roadmap["phases"])
        self.assertGreaterEqual(total, 5)
        self.assertIn("mvp", roadmap)
        self.assertIn("stack", roadmap)


if __name__ == "__main__":
    unittest.main()
