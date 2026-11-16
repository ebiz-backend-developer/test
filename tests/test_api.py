"""End-to-end API checks over a live HTTP server."""
import urllib.request

from tests.helpers import ApiTestCase


class ApiTest(ApiTestCase):
    def test_health(self):
        status, body = self.api("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_scope_roles_stakeholders(self):
        _, scope = self.api("GET", "/api/scope")
        self.assertTrue(scope["in_scope"])
        _, roles = self.api("GET", "/api/roles")
        self.assertEqual({r["name"] for r in roles},
                         {"admin", "teacher", "student", "parent"})
        _, stakeholders = self.api("GET", "/api/stakeholders")
        self.assertEqual(len(stakeholders), 4)

    def test_auth_check_roundtrip(self):
        status, body = self.api("POST", "/api/auth/check",
                                {"role": "teacher", "permission": "grades.enter"})
        self.assertEqual(status, 200)
        self.assertTrue(body["allowed"])
        status, _ = self.api("POST", "/api/auth/check",
                             {"role": "student", "permission": "grades.enter"})
        self.assertEqual(status, 200)

    def test_workflow_instance_lifecycle_over_http(self):
        status, inst = self.api("POST", "/api/workflows/parent-monitoring/instances",
                                {"subject": "HTTP child"})
        self.assertEqual(status, 201)
        iid = inst["id"]
        status, inst = self.api("POST", f"/api/workflow-instances/{iid}/advance",
                                {"action": "link-child", "actor_role": "parent"})
        self.assertEqual(status, 200)
        self.assertEqual(inst["current_step"], "linked")
        status, inst = self.api("GET", f"/api/workflow-instances/{iid}")
        self.assertEqual(status, 200)
        self.assertEqual(len(inst["events"]), 1)
        status, body = self.api("POST", f"/api/workflow-instances/{iid}/advance",
                                {"action": "pay-fees", "actor_role": "parent"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_modules_and_mvp_over_http(self):
        _, modules = self.api("GET", "/api/modules")
        self.assertGreaterEqual(len(modules), 6)
        _, mvp = self.api("GET", "/api/modules/mvp")
        self.assertTrue(mvp)
        self.assertTrue(all(m["priority"] < 2 for m in mvp))
        status, updated = self.api("POST", "/api/modules/fees/priority", {"priority": 2})
        self.assertEqual(status, 200)
        self.assertEqual(updated["priority"], 2)
        _, mvp = self.api("GET", "/api/modules/mvp")
        self.assertNotIn("fees", {m["id"] for m in mvp})
        self.api("POST", "/api/modules/fees/priority", {"priority": 1})

    def test_architecture_over_http(self):
        _, arch = self.api("GET", "/api/architecture")
        self.assertIn("language", arch["stack"])
        self.assertEqual(len(arch["components"]), 4)

    def test_milestone_approval_over_http(self):
        _, milestones = self.api("GET", "/api/milestones")
        mid = milestones[0]["id"]
        status, body = self.api("POST", f"/api/milestones/{mid}/approve",
                                {"role": "teacher", "approver": "Ms T"})
        self.assertEqual(status, 403)
        status, m = self.api("POST", f"/api/milestones/{mid}/approve",
                             {"role": "admin", "approver": "Office"})
        self.assertEqual(status, 200)
        self.assertEqual(m["status"], "proposed")
        status, m = self.api("POST", f"/api/milestones/{mid}/approve",
                             {"role": "parent", "approver": "PTA"})
        self.assertEqual(status, 200)
        self.assertEqual(m["status"], "approved")

    def test_static_ui_served(self):
        for page in ["/", "/roles.html", "/workflows.html",
                     "/modules.html", "/architecture.html", "/milestones.html"]:
            url = f"http://127.0.0.1:{self.port}{page}"
            with urllib.request.urlopen(url) as resp:
                self.assertEqual(resp.status, 200)
                self.assertIn("SchoolMS", resp.read().decode())

    def test_unknown_route_is_404(self):
        status, body = self.api("GET", "/api/nope")
        self.assertEqual(status, 404)
        self.assertIn("error", body)
