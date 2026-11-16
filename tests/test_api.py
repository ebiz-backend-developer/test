"""End-to-end API tests against a live server (all criteria via HTTP)."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from delivery.server import serve


class ApiCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        cls._db = tmp.name
        cls.server = serve(host="127.0.0.1", port=0, db_path=cls._db)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        Path(cls._db).unlink(missing_ok=True)

    def call(self, method, path, body=None, role="stakeholder", expect=200):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={"X-Role": role, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req) as res:
                status, data = res.status, res.read()
        except urllib.error.HTTPError as exc:
            status, data = exc.code, exc.read()
        self.assertEqual(status, expect, f"{method} {path}: {data[:300]}")
        ctype = "application/json"
        if method == "GET" and path == "/":
            self.assertTrue(data)
            return data
        payload = json.loads(data.decode())
        self.assertTrue(ctype)
        return payload

    def test_health_roles_scope(self):
        self.assertTrue(self.call("GET", "/api/health")["ok"])
        self.assertEqual(len(self.call("GET", "/api/roles")["roles"]), 5)
        self.assertTrue(self.call("GET", "/api/scope")["scope"]["vision"])

    def test_scope_write_forbidden_for_stakeholder(self):
        self.call("PUT", "/api/scope", {"vision": "x", "in_scope": ["a"]}, expect=403)

    def test_modules_mvp_build_order(self):
        mods = self.call("GET", "/api/modules")["modules"]
        self.assertGreaterEqual(len(mods), 8)
        mvp = self.call("GET", "/api/mvp")
        self.assertIn("percent", mvp)
        order = self.call("GET", "/api/build-order")["order"]
        by_name = {m["name"]: m for m in mods}
        pos = {n: i for i, n in enumerate(order)}
        for m in mods:
            for dep in m["depends_on"]:
                self.assertLess(pos[dep], pos[m["name"]])
        created = self.call("POST", "/api/modules", {"name": "API mod", "priority": "P1"},
                            role="admin", expect=201)["module"]
        self.assertEqual(created["name"], "API mod")
        self.call("POST", "/api/modules", {"name": "API mod"}, role="admin", expect=422)
        updated = self.call("PATCH", f"/api/modules/{created['id']}",
                            {"status": "planned"}, role="developer")["module"]
        self.assertEqual(updated["status"], "planned")
        self.call("GET", "/api/modules/999999", expect=404)

    def test_arch_and_stack(self):
        stack = self.call("GET", "/api/stack")
        self.assertTrue(stack["decided"])
        decisions = self.call("GET", "/api/architecture")["decisions"]
        proposed = next(d for d in decisions if d["status"] == "proposed")
        self.call("POST", f"/api/architecture/{proposed['id']}/select",
                  {"rationale": ""}, role="tech_lead", expect=422)
        self.call("POST", "/api/architecture",
                  {"category": "database", "option_name": "X"}, role="developer", expect=403)

    def test_milestone_approval_flow(self):
        ms = self.call("POST", "/api/milestones",
                       {"name": "HTTP milestone", "phase": "beta",
                        "start_date": "2027-03-02", "end_date": "2027-04-01"},
                       role="admin", expect=201)["milestone"]
        mid = ms["id"]
        self.call("POST", f"/api/milestones/{mid}/approvals", {"decision": "approved"},
                  role="product_owner", expect=422)  # no criteria yet
        crit = self.call("POST", f"/api/milestones/{mid}/criteria",
                         {"description": "works", "verification_method": "demo"},
                         role="tech_lead", expect=201)["criterion"]
        self.call("PATCH", f"/api/criteria/{crit['id']}", {"status": "met"}, role="developer")
        approval = self.call("POST", f"/api/milestones/{mid}/approvals",
                             {"decision": "approved"}, role="product_owner",
                             expect=201)["approval"]
        self.assertEqual(approval["milestone_status"], "approved")
        health = self.call("GET", f"/api/milestones/{mid}/health")
        self.assertEqual(health["health"], "ready")
        timeline = self.call("GET", "/api/timeline")
        self.assertGreaterEqual(timeline["approved"], 2)

    def test_risks_and_bad_requests(self):
        risks = self.call("GET", "/api/risks")["risks"]
        self.assertGreaterEqual(len(risks), 5)
        self.call("POST", "/api/risks", {"title": "Hot", "likelihood": "high",
                                        "impact": "high"}, role="developer", expect=422)
        self.call("GET", "/api/nope", expect=404)
        self.call("GET", "/", role="stakeholder")

    def test_unknown_role_forbidden(self):
        self.call("PUT", "/api/scope", {"vision": "x", "in_scope": ["a"]},
                  role="janitor", expect=403)


if __name__ == "__main__":
    unittest.main()
