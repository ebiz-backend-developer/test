import json
import threading
import unittest
import urllib.error
import urllib.request

from school.app import Handler
from school.auth import AuthService
from school.service import SchoolService
from school.store import Store
from http.server import ThreadingHTTPServer


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        store = Store()
        cls.auth = AuthService(store)
        cls.svc = SchoolService(store, cls.auth)
        cls.admin = cls.auth.create_user("admin", "admin-pw", "admin")
        cls.teacher_user = cls.auth.create_user("t1", "t1-pw", "teacher")
        t = cls.svc.create_teacher(cls.admin, first_name="T",
                                   last_name="One", email="t1@school.edu",
                                   subject="Math")
        cls.teacher_user["link_id"] = t["id"]
        store.put("users", cls.teacher_user["id"], cls.teacher_user)
        cls.cls = cls.svc.create_class(cls.admin, name="Math", grade_level=9,
                                       teacher_id=t["id"], capacity=10)
        Handler.auth = cls.auth
        Handler.service = cls.svc
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def call(self, method, path, body=None, token=""):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}", method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {token}" if token else ""})
        try:
            with urllib.request.urlopen(req) as res:
                raw = res.read().decode()
                return res.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode()
            return exc.code, json.loads(raw) if raw else None

    def login(self, username, password):
        code, data = self.call("POST", "/api/login",
                               {"username": username, "password": password})
        self.assertEqual(code, 200)
        return data["token"]

    def test_login_me_and_logout(self):
        token = self.login("admin", "admin-pw")
        code, me = self.call("GET", "/api/me", token=token)
        self.assertEqual((code, me["role"]), (200, "admin"))
        code, _ = self.call("POST", "/api/logout", {}, token=token)
        self.assertEqual(code, 200)
        code, _ = self.call("GET", "/api/me", token=token)
        self.assertEqual(code, 401)

    def test_unauthorized_without_token(self):
        code, data = self.call("GET", "/api/students")
        self.assertEqual(code, 401)
        self.assertIn("error", data)

    def test_student_crud_over_http(self):
        token = self.login("admin", "admin-pw")
        code, s = self.call("POST", "/api/students",
                            {"first_name": "Http", "last_name": "Kid",
                             "email": "http.kid@student.edu",
                             "grade_level": 7}, token)
        self.assertEqual(code, 201)
        code, got = self.call("GET", f"/api/students/{s['id']}", token=token)
        self.assertEqual(got["email"], "http.kid@student.edu")
        code, upd = self.call("PUT", f"/api/students/{s['id']}",
                              {"grade_level": 8}, token)
        self.assertEqual(upd["grade_level"], 8)
        code, dup = self.call("POST", "/api/students",
                              {"first_name": "X", "last_name": "Y",
                               "email": "http.kid@student.edu",
                               "grade_level": 7}, token)
        self.assertEqual(code, 409)
        code, _ = self.call("DELETE", f"/api/students/{s['id']}", token=token)
        self.assertEqual(code, 204)
        code, _ = self.call("GET", f"/api/students/{s['id']}", token=token)
        self.assertEqual(code, 404)

    def test_full_academic_flow_over_http(self):
        atoken = self.login("admin", "admin-pw")
        ttoken = self.login("t1", "t1-pw")
        _, s = self.call("POST", "/api/students",
                         {"first_name": "Flow", "last_name": "Kid",
                          "email": "flow.kid@student.edu",
                          "grade_level": 9}, atoken)
        code, _ = self.call("POST", "/api/enrollments",
                            {"student_id": s["id"],
                             "class_id": self.cls["id"]}, atoken)
        self.assertEqual(code, 201)
        code, _ = self.call("POST", "/api/attendance",
                            {"student_id": s["id"],
                             "class_id": self.cls["id"],
                             "day": "2026-05-01", "status": "present"},
                            ttoken)
        self.assertEqual(code, 201)
        code, _ = self.call("POST", "/api/grades",
                            {"student_id": s["id"],
                             "class_id": self.cls["id"],
                             "assignment": "Final", "score": 88}, ttoken)
        self.assertEqual(code, 201)
        code, gpa = self.call("GET", f"/api/students/{s['id']}/gpa",
                              token=atoken)
        self.assertEqual((code, gpa["gpa"]), (200, 3.0))
        code, ros = self.call("GET",
                              f"/api/classes/{self.cls['id']}/roster",
                              token=atoken)
        self.assertTrue(any(r["id"] == s["id"] for r in ros["roster"]))

    def test_teacher_forbidden_from_admin_routes(self):
        ttoken = self.login("t1", "t1-pw")
        code, _ = self.call("POST", "/api/teachers",
                            {"first_name": "N", "last_name": "T",
                             "email": "n@t.co", "subject": "X"}, ttoken)
        self.assertEqual(code, 403)
        code, _ = self.call("GET", "/api/users", token=ttoken)
        self.assertEqual(code, 403)

    def test_fees_and_reports_over_http(self):
        token = self.login("admin", "admin-pw")
        _, s = self.call("POST", "/api/students",
                         {"first_name": "Fee", "last_name": "Kid",
                          "email": "fee.kid@student.edu",
                          "grade_level": 9}, token)
        code, inv = self.call("POST", "/api/fees",
                              {"student_id": s["id"], "title": "Tuition",
                               "amount": 200, "due_date": "2026-12-01"},
                              token)
        self.assertEqual(code, 201)
        code, paid = self.call("POST", f"/api/fees/{inv['id']}/pay",
                               {"amount": 200}, token)
        self.assertEqual(paid["status"], "paid")
        code, rev = self.call("GET", "/api/reports/revenue", token=token)
        self.assertGreaterEqual(rev["collected"], 200)
        code, ov = self.call("GET", "/api/reports/overview", token=token)
        self.assertIn("progress", ov)

    def test_plan_endpoints(self):
        token = self.login("admin", "admin-pw")
        code, mods = self.call("GET", "/api/modules", token=token)
        self.assertIn("students", mods["modules"])
        code, ms = self.call("GET", "/api/milestones", token=token)
        self.assertTrue(ms["all_approved"])
        self.assertEqual(ms["milestones_total"], 4)
        code, roles = self.call("GET", "/api/roles", token=token)
        self.assertEqual(len(roles["roles"]), 5)

    def test_dashboard_served(self):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/", method="GET")
        with urllib.request.urlopen(req) as res:
            html = res.read().decode()
        self.assertIn("SchoolMS", html)
        self.assertIn("/api/login", html)


if __name__ == "__main__":
    unittest.main()
