"""Live HTTP API tests: real server thread + real SQLite file, stdlib client."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from delivery.server import build_server
from delivery.store import init_db
from delivery.seed import seed


class ApiResponseError(Exception):
    def __init__(self, status, payload):
        super().__init__(f"HTTP {status}: {payload}")
        self.status = status
        self.payload = payload


class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = str(Path(cls.tmp.name) / "api-test.db")
        conn = init_db(cls.db)
        seed(conn)
        conn.close()
        cls.server = build_server("127.0.0.1", 0, cls.db)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def api(self, method, path, body=None, role="admin"):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={"X-Role": role, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req) as res:
                return res.status, json.loads(res.read().decode())
        except urllib.error.HTTPError as exc:
            payload = json.loads(exc.read().decode() or "{}")
            raise ApiResponseError(exc.code, payload)

    def test_health(self):
        status, data = self.api("GET", "/api/v1/health", role="stakeholder")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")

    def test_dashboard_served(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/") as res:
            html = res.read().decode()
        self.assertIn("Delivery Milestones", html)
        self.assertIn("/api/v1/roadmap", html)

    def test_roles_and_scope_read(self):
        _, data = self.api("GET", "/api/v1/roles")
        self.assertEqual(len(data["roles"]), 5)
        _, scope = self.api("GET", "/api/v1/scope", role="stakeholder")
        self.assertTrue(scope["scope"]["vision"])

    def test_scope_write_forbidden_for_stakeholder(self):
        with self.assertRaises(ApiResponseError) as ctx:
            self.api("PUT", "/api/v1/scope", {"vision": "hijack", "in_scope": ["x"]},
                     role="stakeholder")
        self.assertEqual(ctx.exception.status, 403)

    def test_scope_write_and_read_back(self):
        self.api("PUT", "/api/v1/scope",
                 {"vision": "api vision", "in_scope": ["a"], "out_of_scope": ["b"],
                  "assumptions": [], "constraints": []}, role="product_owner")
        _, data = self.api("GET", "/api/v1/scope")
        self.assertEqual(data["scope"]["vision"], "api vision")
        self.assertEqual(data["scope"]["in_scope"], ["a"])

    def test_modules_crud_and_mvp(self):
        self.api("POST", "/api/v1/modules",
                 {"name": "api-mod", "priority": "P0", "mvp": True, "effort_points": 2},
                 role="product_owner")
        _, data = self.api("GET", "/api/v1/modules?mvp_only=1")
        self.assertIn("api-mod", [m["name"] for m in data["modules"]])
        mod = next(m for m in data["modules"] if m["name"] == "api-mod")
        _, updated = self.api("PATCH", f"/api/v1/modules/{mod['id']}",
                              {"status": "done"}, role="developer")
        self.assertEqual(updated["module"]["status"], "done")
        _, mvp = self.api("GET", "/api/v1/mvp")
        self.assertGreaterEqual(mvp["total"], 1)

    def test_module_validation_error_shape(self):
        with self.assertRaises(ApiResponseError) as ctx:
            self.api("POST", "/api/v1/modules", {"name": "", "priority": "P9"},
                     role="product_owner")
        self.assertEqual(ctx.exception.status, 400)
        self.assertIn("error", ctx.exception.payload)

    def test_arch_select_flow(self):
        _, before = self.api("GET", "/api/v1/arch?selected_only=1")
        self.assertGreaterEqual(len(before["decisions"]), 1)
        self.api("POST", "/api/v1/arch",
                 {"category": "cache", "option_name": "in-memory",
                  "status": "selected", "rationale": "fast enough"}, role="tech_lead")
        _, after = self.api("GET", "/api/v1/arch?selected_only=1")
        cache = [d for d in after["decisions"] if d["category"] == "cache"]
        self.assertEqual(len(cache), 1)

    def test_milestone_lifecycle_end_to_end(self):
        # Create milestone + criterion + risk as tech_lead.
        _, ms = self.api("POST", "/api/v1/milestones",
                         {"name": "E2E milestone", "phase": "beta",
                          "start_date": "2027-02-01", "end_date": "2027-02-10"},
                         role="tech_lead")
        mid = ms["milestone"]["id"]
        _, crit = self.api("POST", "/api/v1/criteria",
                           {"milestone_id": mid, "description": "e2e works",
                            "verification_method": "this test"}, role="developer")
        # Approval must fail while criterion is pending.
        with self.assertRaises(ApiResponseError) as ctx:
            self.api("POST", "/api/v1/approvals",
                     {"milestone_id": mid, "decision": "approved"}, role="product_owner")
        self.assertEqual(ctx.exception.status, 400)
        # Meet the criterion, then approve.
        self.api("POST", "/api/v1/criteria",
                 {"id": crit["criterion"]["id"], "milestone_id": mid,
                  "description": "e2e works", "verification_method": "this test",
                  "status": "met"}, role="developer")
        _, approval = self.api("POST", "/api/v1/approvals",
                               {"milestone_id": mid, "decision": "approved",
                                "comment": "e2e sign-off"}, role="product_owner")
        self.assertEqual(approval["approval"]["decision"], "approved")
        _, detail = self.api("GET", f"/api/v1/milestones/{mid}")
        self.assertEqual(detail["status"], "approved")
        self.assertTrue(detail["acceptance"]["ready"])

    def test_roadmap_shape(self):
        _, data = self.api("GET", "/api/v1/roadmap", role="stakeholder")
        self.assertEqual(len(data["phases"]), 5)
        self.assertIn("mvp", data)
        self.assertIn("stack", data)

    def test_unknown_role_rejected(self):
        with self.assertRaises(ApiResponseError) as ctx:
            self.api("GET", "/api/v1/roles", role="intruder")
        self.assertEqual(ctx.exception.status, 403)

    def test_404_for_unknown_resource(self):
        with self.assertRaises(ApiResponseError) as ctx:
            self.api("GET", "/api/v1/nope")
        self.assertEqual(ctx.exception.status, 404)


if __name__ == "__main__":
    unittest.main()
