"""Model validation unit tests."""
import unittest

from delivery.models import (
    AcceptanceCriterion,
    Approval,
    ArchDecision,
    Milestone,
    Module,
    Risk,
    Scope,
)


class TestScopeValidation(unittest.TestCase):
    def test_valid_scope(self):
        s = Scope(vision="Ship it", in_scope=["api"], out_of_scope=["mobile"])
        self.assertEqual(s.validate(), [])

    def test_vision_required(self):
        self.assertIn("vision is required", Scope(vision=" ", in_scope=["x"]).validate())

    def test_in_scope_required(self):
        self.assertTrue(Scope(vision="v").validate())

    def test_overlap_rejected(self):
        s = Scope(vision="v", in_scope=["api"], out_of_scope=["api"])
        self.assertTrue(any("both in and out" in e for e in s.validate()))


class TestModuleValidation(unittest.TestCase):
    def test_valid_module(self):
        self.assertEqual(Module(name="api", priority="P0").validate(), [])

    def test_bad_priority(self):
        self.assertTrue(Module(name="m", priority="P9").validate())

    def test_negative_points(self):
        self.assertTrue(Module(name="m", effort_points=-1).validate())

    def test_self_dependency(self):
        self.assertTrue(Module(name="m", depends_on=["m"]).validate())


class TestArchValidation(unittest.TestCase):
    def test_select_needs_rationale(self):
        d = ArchDecision(category="db", option_name="sqlite", status="selected")
        self.assertTrue(any("rationale" in e for e in d.validate()))

    def test_proposed_without_rationale_ok(self):
        d = ArchDecision(category="db", option_name="pg", status="proposed")
        self.assertEqual(d.validate(), [])


class TestMilestoneValidation(unittest.TestCase):
    def test_bad_phase(self):
        self.assertTrue(Milestone(name="m", phase="nope").validate())

    def test_bad_dates(self):
        m = Milestone(name="m", phase="mvp", start_date="2027-01-02", end_date="2027-01-01")
        self.assertTrue(any("end_date" in e for e in m.validate()))
        m2 = Milestone(name="m", phase="mvp", start_date="not-a-date")
        self.assertTrue(any("start_date" in e for e in m2.validate()))


class TestRiskValidation(unittest.TestCase):
    def test_exposure_scale(self):
        self.assertEqual(Risk(title="t", likelihood="low", impact="low").exposure(), 1)
        self.assertEqual(Risk(title="t", likelihood="high", impact="high").exposure(), 9)

    def test_high_exposure_needs_mitigation(self):
        r = Risk(title="t", likelihood="high", impact="high", mitigation="")
        self.assertTrue(any("mitigation" in e for e in r.validate()))

    def test_low_exposure_ok_without_mitigation(self):
        r = Risk(title="t", likelihood="low", impact="low")
        self.assertEqual(r.validate(), [])


class TestCriterionApprovalValidation(unittest.TestCase):
    def test_criterion_needs_milestone(self):
        self.assertTrue(AcceptanceCriterion(milestone_id=0, description="x").validate())

    def test_rejection_needs_comment(self):
        a = Approval(milestone_id=1, approver_role="product_owner", decision="rejected")
        self.assertTrue(any("comment" in e for e in a.validate()))

    def test_clean_approval_ok(self):
        a = Approval(milestone_id=1, approver_role="product_owner", decision="approved")
        self.assertEqual(a.validate(), [])


if __name__ == "__main__":
    unittest.main()
