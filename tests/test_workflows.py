"""Role workflows: student, teacher, admin, parent state machines."""
import unittest

from tests.helpers import make_service


class WorkflowCatalogTest(unittest.TestCase):
    def setUp(self):
        self.svc = make_service()

    def test_four_role_workflows_present(self):
        flows = {w["id"]: w for w in self.svc.workflow_list()}
        self.assertEqual(set(flows), {"student-enrollment", "teacher-gradebook",
                                     "admin-admissions", "parent-monitoring"})
        owners = {w["owner_role"] for w in flows.values()}
        self.assertEqual(owners, {"student", "teacher", "admin", "parent"})

    def test_unknown_workflow_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.workflow_get("nope")


class WorkflowRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.svc = make_service()

    def test_student_enrollment_happy_path(self):
        inst = self.svc.instance_start("student-enrollment", "Ada")
        self.assertEqual(inst["current_step"], "applied")
        inst = self.svc.instance_advance(inst["id"], "approve-application", "admin")
        self.assertEqual(inst["current_step"], "admitted")
        inst = self.svc.instance_advance(inst["id"], "confirm-enrollment", "student")
        self.assertEqual(inst["current_step"], "enrolled")
        inst = self.svc.instance_advance(inst["id"], "activate", "admin")
        self.assertEqual(inst["current_step"], "active")
        self.assertTrue(inst["is_final"])
        self.assertEqual(inst["status"], "complete")
        self.assertEqual(len(inst["events"]), 3)

    def test_teacher_gradebook_full_cycle(self):
        inst = self.svc.instance_start("teacher-gradebook", "Math 5A")
        for action, role in [("take-attendance", "teacher"),
                             ("enter-grades", "teacher"),
                             ("publish-grades", "teacher")]:
            inst = self.svc.instance_advance(inst["id"], action, role)
        self.assertEqual(inst["current_step"], "published")
        inst = self.svc.instance_advance(inst["id"], "reopen", "admin")
        self.assertEqual(inst["current_step"], "grades-entered")

    def test_admin_pipeline(self):
        inst = self.svc.instance_start("admin-admissions", "Applicant Bo")
        for action in ["start-review", "accept", "assign-class", "invoice-fees"]:
            inst = self.svc.instance_advance(inst["id"], action, "admin")
        self.assertEqual(inst["current_step"], "invoiced")
        self.assertTrue(inst["is_final"])

    def test_parent_monitoring_with_new_invoice_loop(self):
        inst = self.svc.instance_start("parent-monitoring", "Child Cid")
        inst = self.svc.instance_advance(inst["id"], "link-child", "parent")
        inst = self.svc.instance_advance(inst["id"], "start-monitoring", "parent")
        inst = self.svc.instance_advance(inst["id"], "pay-fees", "parent")
        self.assertEqual(inst["current_step"], "fees-current")
        inst = self.svc.instance_advance(inst["id"], "new-invoice", "admin")
        self.assertEqual(inst["current_step"], "monitoring")

    def test_wrong_role_rejected(self):
        inst = self.svc.instance_start("student-enrollment", "Eve")
        with self.assertRaises(PermissionError):
            self.svc.instance_advance(inst["id"], "approve-application", "student")

    def test_out_of_order_action_rejected(self):
        inst = self.svc.instance_start("teacher-gradebook", "Science 6B")
        with self.assertRaises(ValueError):
            self.svc.instance_advance(inst["id"], "publish-grades", "teacher")

    def test_unknown_action_rejected(self):
        inst = self.svc.instance_start("parent-monitoring", "Child Dan")
        with self.assertRaises(ValueError):
            self.svc.instance_advance(inst["id"], "fly", "parent")

    def test_blank_subject_rejected(self):
        with self.assertRaises(ValueError):
            self.svc.instance_start("parent-monitoring", "   ")

    def test_unknown_instance_rejected(self):
        with self.assertRaises(LookupError):
            self.svc.instance_get(999999)

    def test_events_record_actor_and_transition(self):
        inst = self.svc.instance_start("admin-admissions", "Applicant Fay")
        inst = self.svc.instance_advance(inst["id"], "start-review", "admin")
        event = inst["events"][-1]
        self.assertEqual(event["actor_role"], "admin")
        self.assertEqual((event["from_step"], event["to_step"]),
                         ("applied", "under-review"))


if __name__ == "__main__":
    unittest.main()
