"""HTTP API integration: live server, role headers, RBAC over the wire."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError

from app.server import make_server


def call(base, method, path, role=None, user="Test User", body=None):
    req = urlrequest.Request(base + path, method=method)
    if role:
        req.add_header("X-Role", role)
    req.add_header("X-User", user)
    data = json.dumps(body or {}).encode() if body is not None else None
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urlrequest.urlopen(req, data=data, timeout=10) as res:
            raw = res.read().decode()
            return res.status, json.loads(raw) if raw else None
    except HTTPError as exc:
        raw = exc.read().decode()
        return exc.code, json.loads(raw) if raw else None


class ApiCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db = str(Path(cls.tmp.name) / "api.db")
        cls.server = make_server(db, 0)
        cls.port = cls.server.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()


class TestApi(ApiCase):
    def test_health_and_reads(self):
        status, body = call(self.base, "GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"ok": True})
        for path in ("/api/roles", "/api/stakeholders", "/api/workflows",
                     "/api/modules", "/api/modules/mvp", "/api/tech",
                     "/api/tech/selected", "/api/milestones", "/api/users",
                     "/api/audit"):
            status, _ = call(self.base, "GET", path)
            self.assertEqual(status, 200, path)

    def test_workflow_run_over_http(self):
        status, inst = call(self.base, "POST",
                            "/api/workflows/student/instances",
                            role="student", user="Stacy")
        self.assertEqual(status, 201)
        status, inst = call(self.base, "POST",
                            f"/api/instances/{inst['id']}/advance",
                            role="student", user="Stacy",
                            body={"note": "checked classes"})
        self.assertEqual(status, 200)
        self.assertEqual(inst["current_position"], 2)

    def test_rbac_denied_over_http(self):
        status, body = call(self.base, "POST",
                            "/api/milestones/M1/approve", role="teacher",
                            user="Tom", body={})
        self.assertEqual(status, 403)
        self.assertIn("may not perform", body["error"])
        status, _ = call(self.base, "POST", "/api/scope",
                         role="student", user="Stacy",
                         body={"kind": "in_scope", "title": "x"})
        self.assertEqual(status, 403)

    def test_milestone_approval_over_http(self):
        status, created = call(
            self.base, "POST", "/api/milestones", role="principal",
            user="Ada", body={"code": "M9", "title": "API milestone",
                              "goal": "g", "exit_criteria": "e"})
        self.assertEqual(status, 201)
        status, decided = call(self.base, "POST",
                               "/api/milestones/M9/approve", role="principal",
                               user="Ada", body={"note": "looks good"})
        self.assertEqual(status, 200)
        self.assertEqual(decided["status"], "approved")

    def test_module_patch_moves_mvp(self):
        status, updated = call(self.base, "PATCH", "/api/modules/M9",
                               role="principal", user="Ada",
                               body={"priority": "P0"})
        self.assertEqual(status, 200)
        self.assertEqual(updated["phase"], "MVP")
        status, mvp = call(self.base, "GET", "/api/modules/mvp")
        self.assertIn("M9", [m["code"] for m in mvp["modules"]])
        call(self.base, "PATCH", "/api/modules/M9", role="principal",
             user="Ada", body={"priority": "P2"})

    def test_unknown_routes_and_ids(self):
        status, _ = call(self.base, "GET", "/api/nope")
        self.assertEqual(status, 404)
        status, _ = call(self.base, "GET", "/api/workflows/janitor")
        self.assertEqual(status, 404)

    def test_static_ui_served(self):
        for page in ("/", "/workflows.html", "/milestones.html",
                     "/css/app.css", "/js/app.js"):
            req = urlrequest.Request(self.base + page)
            with urlrequest.urlopen(req, timeout=10) as res:
                self.assertEqual(res.status, 200, page)
                self.assertTrue(res.read(), page)


if __name__ == "__main__":
    unittest.main()
