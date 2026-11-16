"""Workflow engine: ordered gated steps, role handoffs, completion. (c1)"""
import unittest

from app import service
from app.seed import seed
from app.store import Store


class WorkflowCase(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        seed(self.store)

    def tearDown(self):
        self.store.close()


class TestWorkflowCatalog(WorkflowCase):
    def test_all_stakeholder_journeys_present(self):
        codes = {w["code"] for w in service.list_workflows(self.store)}
        self.assertEqual(
            codes,
            {"admin", "teacher", "student", "parent", "registrar",
             "accountant", "principal"})

    def test_core_four_have_module_tagged_steps_and_gates(self):
        for code in ("admin", "teacher", "student", "parent"):
            flow = service.get_workflow(self.store, code)
            self.assertGreaterEqual(len(flow.steps), 4, code)
            for step in flow.steps:
                self.assertTrue(step.module, f"{code} step untagged")
                self.assertTrue(step.gate, f"{code} step has no gate")
                self.assertTrue(step.allowed_roles,
                                f"{code} step {step.position} has no roles")

    def test_unknown_workflow_is_404(self):
        with self.assertRaises(service.ServiceError) as ctx:
            service.get_workflow(self.store, "janitor")
        self.assertEqual(ctx.exception.status, 404)


class TestWorkflowExecution(WorkflowCase):
    def test_student_runs_own_workflow_end_to_end(self):
        inst = service.start_instance(
            self.store, "Stacy", "student", "student")
        self.assertEqual(inst["status"], "open")
        total = inst["total_steps"]
        for _ in range(total):
            inst = service.advance_instance(
                self.store, "Stacy", "student", inst["id"])
        self.assertEqual(inst["status"], "completed")
        self.assertEqual(len(inst["events"]), total + 1)  # start + steps

    def test_completed_instance_cannot_advance(self):
        inst = service.start_instance(
            self.store, "Stacy", "student", "student")
        for _ in range(inst["total_steps"]):
            inst = service.advance_instance(
                self.store, "Stacy", "student", inst["id"])
        with self.assertRaises(service.ServiceError):
            service.advance_instance(
                self.store, "Stacy", "student", inst["id"])

    def test_parent_handoff_requires_office_first(self):
        # Step 1 (link wards) belongs to the office; a parent cannot start it.
        with self.assertRaises(service.ServiceError) as ctx:
            service.start_instance(self.store, "Pam", "parent", "parent")
        self.assertEqual(ctx.exception.status, 403)
        inst = service.start_instance(
            self.store, "Olive", "office_staff", "parent")
        with self.assertRaises(service.ServiceError):
            service.advance_instance(
                self.store, "Pam", "parent", inst["id"])
        inst = service.advance_instance(
            self.store, "Olive", "office_staff", inst["id"],
            note="wards verified and linked")
        self.assertEqual(inst["current_position"], 2)
        inst = service.advance_instance(
            self.store, "Pam", "parent", inst["id"])
        self.assertEqual(inst["current_position"], 3)

    def test_teacher_cannot_publish_own_grades(self):
        inst = service.start_instance(
            self.store, "Tom", "teacher", "teacher")
        # Steps 1-3 belong to teachers.
        for _ in range(3):
            inst = service.advance_instance(
                self.store, "Tom", "teacher", inst["id"])
        self.assertEqual(inst["current_position"], 4)
        # Step 4 (publish) needs principal approval rights.
        with self.assertRaises(service.ServiceError) as ctx:
            service.advance_instance(
                self.store, "Tom", "teacher", inst["id"])
        self.assertEqual(ctx.exception.status, 403)
        inst = service.advance_instance(
            self.store, "Ada", "principal", inst["id"], note="grades published")
        self.assertEqual(inst["current_position"], 5)

    def test_advance_is_strictly_sequential(self):
        inst = service.start_instance(
            self.store, "Tom", "teacher", "teacher")
        first = service.advance_instance(
            self.store, "Tom", "teacher", inst["id"])
        self.assertEqual(first["current_position"], 2)

    def test_cancel_ends_instance(self):
        inst = service.start_instance(
            self.store, "Rita", "registrar", "registrar")
        cancelled = service.cancel_instance(
            self.store, "Rita", "registrar", inst["id"], note="duplicate")
        self.assertEqual(cancelled["status"], "cancelled")
        with self.assertRaises(service.ServiceError):
            service.advance_instance(
                self.store, "Rita", "registrar", inst["id"])

    def test_advance_writes_audit_entries(self):
        inst = service.start_instance(
            self.store, "Stacy", "student", "student")
        service.advance_instance(self.store, "Stacy", "student", inst["id"])
        actions = [a["action"] for a in service.list_audit(self.store)]
        self.assertIn("workflows.advance", actions)

    def test_list_instances_filters(self):
        service.start_instance(self.store, "Stacy", "student", "student")
        service.start_instance(self.store, "Tom", "teacher", "teacher")
        only_student = service.list_instances(
            self.store, workflow_code="student")
        self.assertEqual(len(only_student), 1)
        self.assertEqual(
            len(service.list_instances(self.store, status="open")), 2)
        with self.assertRaises(service.ServiceError):
            service.list_instances(self.store, status="bogus")


if __name__ == "__main__":
    unittest.main()
