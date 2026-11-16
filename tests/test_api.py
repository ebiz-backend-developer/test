"""End-to-end API tests over real HTTP against a live server thread."""
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from app.server import make_server


def _request(base, method, path, user=None, body=None):
    req = urllib.request.Request(base + path, method=method)
    if user:
        req.add_header("X-User", user)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data, timeout=10) as res:
            raw = res.read().decode("utf-8")
            ctype = res.headers.get("Content-Type", "")
            if "application/json" in ctype:
                return res.status, json.loads(raw or "null")
            return res.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw or "null")
        except json.JSONDecodeError:
            return exc.code, raw


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mktemp(suffix=".db")
        cls.server = make_server(cls.tmp, 0)
        cls.port = cls.server.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        if os.path.exists(cls.tmp):
            os.unlink(cls.tmp)

    def call(self, method, path, user=None, body=None):
        return _request(self.base, method, path, user, body)

    # -- health / reads -------------------------------------------------
    def test_health(self):
        status, body = self.call("GET", "/api/health")
        self.assertEqual((status, body), (200, {"ok": True}))

    def test_roles_lists_five_with_permissions(self):
        status, roles = self.call("GET", "/api/roles")
        self.assertEqual(status, 200)
        self.assertEqual(len(roles), 5)
        admin = next(r for r in roles if r["name"] == "admin")
        self.assertIn("milestones.approve", admin["permissions"])

    def test_unknown_api_route_404(self):
        status, _ = self.call("GET", "/api/nope")
        self.assertEqual(status, 404)

    def test_method_not_allowed(self):
        status, _ = self.call("POST", "/api/health", user="ada", body={})
        self.assertEqual(status, 404)

    # -- scope (c1) ------------------------------------------------------
    def test_scope_add_and_rbac(self):
        status, items = self.call("GET", "/api/scope")
        self.assertEqual(status, 200)
        n = len(items)
        status, _ = self.call("POST", "/api/scope", user="diego",
                              body={"title": "x", "kind": "in_scope"})
        self.assertEqual(status, 403)
        status, item = self.call("POST", "/api/scope", user="priya",
                                 body={"title": "API scope item",
                                       "kind": "assumption", "detail": "d"})
        self.assertEqual(status, 201)
        self.assertEqual(item["kind"], "assumption")
        status, items = self.call("GET", "/api/scope")
        self.assertEqual(len(items), n + 1)
        status, _ = self.call("POST", "/api/scope", user="priya",
                              body={"title": "", "kind": "in_scope"})
        self.assertEqual(status, 400)

    # -- modules (c2) ----------------------------------------------------
    def test_modules_mvp_filter(self):
        _, all_mods = self.call("GET", "/api/modules")
        _, mvp = self.call("GET", "/api/modules?mvp=1")
        self.assertTrue(all_mods)
        self.assertTrue(mvp)
        self.assertTrue(all(m["mvp"] for m in mvp))
        self.assertLessEqual(len(mvp), len(all_mods))

    def test_prioritize_requires_pm_or_admin(self):
        _, mods = self.call("GET", "/api/modules")
        mid = mods[0]["id"]
        status, _ = self.call("POST", f"/api/modules/{mid}/prioritize",
                              user="devon", body={"priority": "P0", "mvp": True})
        self.assertEqual(status, 403)
        status, mod = self.call("POST", f"/api/modules/{mid}/prioritize",
                                user="priya",
                                body={"priority": "P1", "mvp": True})
        self.assertEqual(status, 200)
        self.assertEqual(mod["priority"], "P1")
        status, _ = self.call("POST", f"/api/modules/{mid}/prioritize",
                              user="priya", body={"priority": "P1"})
        self.assertEqual(status, 400)

    def test_developer_can_update_status_but_not_priority(self):
        _, mods = self.call("GET", "/api/modules")
        mid = mods[0]["id"]
        status, mod = self.call("PATCH", f"/api/modules/{mid}", user="devon",
                                body={"status": "in_build"})
        self.assertEqual(status, 200)
        self.assertEqual(mod["status"], "in_build")
        status, _ = self.call("PATCH", f"/api/modules/{mid}", user="diego",
                              body={"status": "done"})
        self.assertEqual(status, 403)

    def test_module_not_found(self):
        status, _ = self.call("GET", "/api/modules/99999")
        self.assertEqual(status, 404)

    # -- tech (c3) --------------------------------------------------------
    def test_tech_propose_select_lifecycle(self):
        status, opt = self.call("POST", "/api/tech", user="devon",
                                body={"layer": "data", "name": "API DB",
                                      "description": "test"})
        self.assertEqual(status, 201)
        self.assertEqual(opt["status"], "proposed")
        status, _ = self.call("POST", f"/api/tech/{opt['id']}/select",
                              user="devon", body={})
        self.assertEqual(status, 403)
        status, decided = self.call("POST", f"/api/tech/{opt['id']}/select",
                                    user="priya",
                                    body={"rationale": "fits MVP"})
        self.assertEqual(status, 200)
        self.assertEqual(decided["status"], "selected")
        status, _ = self.call("POST", f"/api/tech/{opt['id']}/select",
                              user="priya", body={})
        self.assertEqual(status, 409)

    def test_tech_layer_filter(self):
        status, opts = self.call("GET", "/api/tech?layer=mobile")
        self.assertEqual(status, 200)
        self.assertTrue(opts)
        self.assertTrue(all(o["layer"] == "mobile" for o in opts))

    # -- milestones (c4) --------------------------------------------------
    def test_milestone_approval_workflow(self):
        status, ms = self.call("POST", "/api/milestones", user="priya",
                               body={"title": "E2E milestone",
                                     "due_date": "2027-05-01"})
        self.assertEqual(status, 201)
        mid = ms["id"]
        # Approve while draft -> conflict.
        status, _ = self.call("POST", f"/api/milestones/{mid}/approve",
                              user="sam", body={})
        self.assertEqual(status, 409)
        # Designer cannot submit.
        status, _ = self.call("POST", f"/api/milestones/{mid}/submit",
                              user="diego", body={})
        self.assertEqual(status, 403)
        status, ms = self.call("POST", f"/api/milestones/{mid}/submit",
                               user="priya", body={})
        self.assertEqual(ms["status"], "proposed")
        # PM cannot approve their own proposal.
        status, _ = self.call("POST", f"/api/milestones/{mid}/approve",
                              user="priya", body={})
        self.assertEqual(status, 403)
        status, ms = self.call("POST", f"/api/milestones/{mid}/approve",
                               user="sam", body={})
        self.assertEqual(status, 200)
        self.assertEqual(ms["status"], "approved")
        self.assertEqual(ms["approved_by"], "sam")
        self.assertTrue(ms["approved_at"])

    def test_milestone_reject(self):
        _, ms = self.call("POST", "/api/milestones", user="ada",
                          body={"title": "E2E reject"})
        self.call("POST", f"/api/milestones/{ms['id']}/submit",
                  user="ada", body={})
        status, ms = self.call("POST", f"/api/milestones/{ms['id']}/reject",
                               user="ada", body={})
        self.assertEqual(status, 200)
        self.assertEqual(ms["status"], "rejected")

    def test_unauthenticated_write_401(self):
        status, _ = self.call("POST", "/api/milestones",
                              body={"title": "anon"})
        self.assertEqual(status, 401)
        status, _ = self.call("POST", "/api/milestones", user="ghost",
                              body={"title": "ghost"})
        self.assertEqual(status, 401)

    # -- flows & wireframes ----------------------------------------------
    def test_flows_crud_and_validation(self):
        steps = [{"label": "Start", "desc": "entry", "next": ["End"]},
                 {"label": "End", "desc": "", "next": []}]
        status, flow = self.call("POST", "/api/flows", user="diego",
                                 body={"name": "E2E flow", "persona": "Tester",
                                       "device": "mobile", "steps": steps})
        self.assertEqual(status, 201)
        status, got = self.call("GET", f"/api/flows/{flow['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(got["steps"], steps)
        status, _ = self.call("POST", "/api/flows", user="devon",
                              body={"name": "x", "persona": "y", "steps": steps})
        self.assertEqual(status, 403)
        status, _ = self.call("POST", "/api/flows", user="diego",
                              body={"name": "bad", "persona": "y", "steps": []})
        self.assertEqual(status, 400)

    def test_wireframes_crud(self):
        blocks = [{"type": "header", "label": "Top bar"}]
        status, wf = self.call(
            "POST", "/api/wireframes", user="diego",
            body={"title": "E2E wf", "screen": "home", "device": "mobile",
                  "blocks": blocks})
        self.assertEqual(status, 201)
        status, got = self.call("GET", f"/api/wireframes/{wf['id']}")
        self.assertEqual(got["blocks"], blocks)
        status, _ = self.call("POST", "/api/wireframes", user="priya",
                              body={"title": "x", "screen": "s",
                                    "blocks": blocks})
        self.assertEqual(status, 403)

    # -- dashboard & static -----------------------------------------------
    def test_dashboard(self):
        status, dash = self.call("GET", "/api/dashboard?role=designer")
        self.assertEqual(status, 200)
        self.assertIn("mvp_modules", dash)
        self.assertIn("pending_approvals", dash)
        self.assertGreaterEqual(dash["counts"]["modules"], 8)

    def test_static_pages_served(self):
        for page in ("/", "/index.html", "/dashboard.html", "/scope.html",
                     "/modules.html", "/tech.html", "/milestones.html",
                     "/flows.html", "/wireframes.html", "/css/app.css",
                     "/js/app.js"):
            status, body = self.call("GET", page)
            self.assertEqual(status, 200, page)
            self.assertTrue(body, page)

    def test_static_traversal_blocked(self):
        status, _ = self.call("GET", "/../run.py")
        self.assertEqual(status, 404)

    def test_bad_json_rejected(self):
        req = urllib.request.Request(self.base + "/api/scope", method="POST")
        req.add_header("X-User", "priya")
        req.add_header("Content-Type", "application/json")
        try:
            urllib.request.urlopen(req, data=b"{oops", timeout=10)
            self.fail("expected HTTPError")
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 400)


if __name__ == "__main__":
    unittest.main()
