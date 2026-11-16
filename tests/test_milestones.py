"""c4: delivery milestones — phases, timeline, risks, acceptance, approvals."""
import unittest

from delivery import seed, service
from delivery.models import AcceptanceCriterion, Approval, Milestone, Risk
from delivery.store import connect, migrate


def fresh():
    conn = connect(":memory:")
    migrate(conn)
    seed.seed(conn)
    return conn


def milestone_id(conn, name):
    return next(m["id"] for m in service.list_milestones(conn) if m["name"] == name)


class MilestonesTest(unittest.TestCase):
    def test_timeline_phase_order(self):
        timeline = service.timeline(fresh())
        self.assertEqual(
            [p["phase"] for p in timeline["phases"]],
            ["discovery", "mvp", "beta", "ga", "scale"],
        )
        self.assertEqual(timeline["approved"], 1)  # seeded M1 approval

    def test_milestone_validation(self):
        conn = fresh()
        bad = Milestone(name="X", phase="nope")
        with self.assertRaises(service.ValidationError):
            service.create_milestone(conn, bad, role="admin")
        bad = Milestone(name="X", phase="mvp", start_date="2027-13-01")
        with self.assertRaises(service.ValidationError):
            service.create_milestone(conn, bad, role="admin")
        bad = Milestone(name="X", phase="mvp", start_date="2027-02-01", end_date="2027-01-01")
        with self.assertRaises(service.ValidationError):
            service.create_milestone(conn, bad, role="admin")
        with self.assertRaises(service.AuthError):
            service.create_milestone(conn, Milestone(name="X", phase="mvp"), role="developer")

    def test_approved_milestone_locked_and_status_edit_cannot_approve(self):
        conn = fresh()
        m1 = milestone_id(conn, "M1: Scope & roles signed off")
        with self.assertRaises(service.ValidationError):
            service.update_milestone(conn, m1, {"status": "in_progress"}, role="admin")
        m2 = milestone_id(conn, "M2: Architecture selected")
        with self.assertRaises(service.ValidationError):
            service.update_milestone(conn, m2, {"status": "approved"}, role="admin")


class RisksTest(unittest.TestCase):
    def test_exposure_math_and_order(self):
        risks = service.list_risks(fresh())
        self.assertTrue(risks[0]["exposure"] >= risks[-1]["exposure"])
        hot = next(r for r in risks if r["title"] == "Fee-structure variety across schools")
        self.assertEqual(hot["exposure"], 9)

    def test_high_exposure_requires_mitigation(self):
        conn = fresh()
        with self.assertRaises(service.ValidationError):
            service.create_risk(conn, Risk(title="Big", likelihood="high", impact="high"), role="developer")
        ok = service.create_risk(
            conn, Risk(title="Big", likelihood="high", impact="high", mitigation="plan"),
            role="developer",
        )
        self.assertEqual(ok["exposure"], 9)


class ApprovalWorkflowTest(unittest.TestCase):
    def _draft(self, conn):
        ms = service.create_milestone(conn, Milestone(name="MX", phase="mvp"), role="admin")
        return ms["id"]

    def _meet_all(self, conn, mid):
        for c in service.list_criteria(conn, mid):
            service.set_criterion_status(conn, c["id"], "met", role="developer")

    def test_approval_requires_criteria(self):
        conn = fresh()
        mid = self._draft(conn)
        with self.assertRaises(service.ValidationError):
            service.decide_approval(
                conn, Approval(milestone_id=mid, approver_role="x", decision="approved"),
                role="product_owner",
            )

    def test_approval_requires_all_met(self):
        conn = fresh()
        mid = self._draft(conn)
        service.add_criterion(conn, AcceptanceCriterion(milestone_id=mid, description="a"), role="admin")
        service.add_criterion(conn, AcceptanceCriterion(milestone_id=mid, description="b"), role="admin")
        first = service.list_criteria(conn, mid)[0]
        service.set_criterion_status(conn, first["id"], "met", role="developer")
        with self.assertRaises(service.ValidationError):
            service.decide_approval(
                conn, Approval(milestone_id=mid, approver_role="x", decision="approved"),
                role="product_owner",
            )

    def test_approval_blocked_by_open_hot_risk(self):
        conn = fresh()
        mid = self._draft(conn)
        service.add_criterion(conn, AcceptanceCriterion(milestone_id=mid, description="a"), role="admin")
        self._meet_all(conn, mid)
        service.create_risk(
            conn, Risk(title="Hot", likelihood="high", impact="high",
                       mitigation="plan", milestone_id=mid),
            role="developer",
        )
        with self.assertRaises(service.ValidationError):
            service.decide_approval(
                conn, Approval(milestone_id=mid, approver_role="x", decision="approved"),
                role="product_owner",
            )
        # mitigating the risk unblocks approval
        risk = service.list_risks(conn, mid)[0]
        service.update_risk(conn, risk["id"], {"status": "mitigating"}, role="developer")
        result = service.decide_approval(
            conn, Approval(milestone_id=mid, approver_role="x", decision="approved"),
            role="product_owner",
        )
        self.assertEqual(result["milestone_status"], "approved")
        self.assertEqual(result["approver_role"], "product_owner")

    def test_only_approvers_decide_and_rejections_need_comments(self):
        conn = fresh()
        mid = self._draft(conn)
        service.add_criterion(conn, AcceptanceCriterion(milestone_id=mid, description="a"), role="admin")
        self._meet_all(conn, mid)
        with self.assertRaises(service.AuthError):
            service.decide_approval(
                conn, Approval(milestone_id=mid, approver_role="x", decision="approved"),
                role="tech_lead",
            )
        with self.assertRaises(service.ValidationError):
            service.decide_approval(
                conn, Approval(milestone_id=mid, approver_role="x", decision="rejected"),
                role="product_owner",
            )
        result = service.decide_approval(
            conn, Approval(milestone_id=mid, approver_role="x", decision="rejected", comment="no"),
            role="product_owner",
        )
        self.assertEqual(result["milestone_status"], "draft")

    def test_health_flags_failed_criteria(self):
        conn = fresh()
        mid = self._draft(conn)
        service.add_criterion(conn, AcceptanceCriterion(milestone_id=mid, description="a"), role="admin")
        only = service.list_criteria(conn, mid)[0]
        service.set_criterion_status(conn, only["id"], "failed", role="developer")
        self.assertEqual(service.milestone_health(conn, mid)["health"], "at_risk")


if __name__ == "__main__":
    unittest.main()
