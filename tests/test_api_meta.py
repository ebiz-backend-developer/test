"""Cross-cutting API behavior: meta endpoints, milestone approval (c4),
unknown roles/routes, migrations, seed data, and the live HTTP server."""
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import server
from mvp import store
from tests.helpers import DbTestCase


class MetaApiTest(DbTestCase):
    def test_scope_modules_stack(self):
        for path in ("/api/scope", "/api/modules", "/api/stack"):
            s, payload = self.call("GET", path, role="student")
            self.assertEqual(s, 200, path)
        s, mods = self.call("GET", "/api/modules", role="student")
        self.assertEqual(len(mods["modules"]), 6)
        self.assertEqual(len(mods["mvp"]), 6)

    def test_unknown_role_rejected(self):
        s, err = self.call("GET", "/api/scope", role="hacker")
        self.assertEqual(s, 403)

    def test_unknown_route_404(self):
        s, _ = self.call("GET", "/api/payroll", role="admin")
        self.assertEqual(s, 404)

    def test_invalid_json_body_400(self):
        from mvp import api
        s, err = api.dispatch(self.conn, "POST", "/api/applications",
                              {"x-role": "parent"}, b"{nope")
        self.assertEqual(s, 400)


class MilestoneApprovalTest(DbTestCase):
    def test_approve_advance_finish_flow(self):
        s, data = self.call("GET", "/api/milestones", role="admin")
        self.assertTrue(all(m["status"] == "planned" for m in data["milestones"]))

        s, m1 = self.call("POST", "/api/milestones/M1/approve", role="admin")
        self.assertEqual(m1["status"], "approved")

        s, m1 = self.call("POST", "/api/milestones/M1/status", role="admin",
                          body={"status": "in_progress"})
        self.assertEqual(m1["status"], "in_progress")

        s, m1 = self.call("POST", "/api/milestones/M1/status", role="admin",
                          body={"status": "done"})
        self.assertEqual(m1["status"], "done")

    def test_skip_approval_rejected(self):
        s, _ = self.call("POST", "/api/milestones/M2/status", role="admin",
                         body={"status": "done"})
        self.assertEqual(s, 400)

    def test_non_admin_cannot_approve(self):
        s, _ = self.call("POST", "/api/milestones/M1/approve", role="teacher")
        self.assertEqual(s, 403)

    def test_unknown_milestone_404(self):
        s, _ = self.call("POST", "/api/milestones/M9/approve", role="admin")
        self.assertEqual(s, 404)


class StoreTest(DbTestCase):
    def test_migrate_idempotent(self):
        store.migrate(self.conn)
        ver = self.conn.execute(
            "SELECT value FROM meta WHERE key='schema_version'").fetchone()
        self.assertEqual(ver["value"], "1")

    def test_seed_demo(self):
        self.assertTrue(store.seed_demo(self.conn))
        self.assertFalse(store.seed_demo(self.conn))  # second run is a no-op
        n = self.conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        self.assertEqual(n, 4)


class LiveServerTest(DbTestCase):
    """Spin up the real HTTP server on an ephemeral port and hit it."""

    def test_http_roundtrip(self):
        import tempfile, os
        fd, db = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        old = server.DB_PATH
        server.DB_PATH = db
        try:
            conn = store.connect(db)
            store.migrate(conn)
            conn.close()
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
            port = httpd.server_address[1]
            t = threading.Thread(target=httpd.serve_forever, daemon=True)
            t.start()
            try:
                def req(method, path, role="admin", body=None):
                    r = urllib.request.Request(
                        f"http://127.0.0.1:{port}{path}", method=method,
                        headers={"X-Role": role,
                                 "Content-Type": "application/json"},
                        data=json.dumps(body).encode() if body else None)
                    try:
                        with urllib.request.urlopen(r) as resp:
                            return resp.status, json.loads(resp.read())
                    except urllib.error.HTTPError as e:
                        return e.code, json.loads(e.read())

                s, mods = req("GET", "/api/modules", role="student")
                self.assertEqual(s, 200)
                self.assertEqual(len(mods["modules"]), 6)
                s, app = req("POST", "/api/applications", role="parent",
                             body={"student_name": "Zed",
                                   "grade_applying": "JSS1"})
                self.assertEqual(s, 201)
                s, _ = req("POST", "/api/applications/1/decide",
                           role="student", body={"decision": "admitted"})
                self.assertEqual(s, 403)
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/") as resp:
                    html = resp.read().decode()
                self.assertIn("School Management MVP", html)
            finally:
                httpd.shutdown()
                httpd.server_close()
        finally:
            server.DB_PATH = old
            os.unlink(db)
