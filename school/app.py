"""REST API over stdlib http.server + static dashboard UI (c3: architecture).

Run:  python run.py [--port 8000] [--seed]
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from .auth import AuthError, AuthService, load_roles_config
from .milestones import MODULES, load_modules_config, overall_progress
from .models import ValidationError
from .service import SchoolService
from .store import ConflictError, NotFoundError, Store

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "school.json")


def build_services(data_path=None):
    store = Store(data_path or DATA_PATH)
    auth = AuthService(store)
    service = SchoolService(store, auth)
    return store, auth, service


class Handler(BaseHTTPRequestHandler):
    auth: AuthService = None
    service: SchoolService = None
    server_version = "SchoolMS/1.0"

    # -- plumbing --------------------------------------------------------
    def log_message(self, *args):
        pass

    def _send(self, status, payload=None):
        body = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode() or "{}")
        except json.JSONDecodeError:
            raise ValidationError("request body must be valid JSON")

    def _user(self, optional=False):
        header = self.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        try:
            return self.auth.authenticate(token)
        except AuthError:
            if optional:
                return None
            raise

    def _route(self):
        parsed = urlparse(self.path)
        return self.command, parsed.path, parse_qs(parsed.query)

    # -- dispatch ----------------------------------------------------------
    def do_GET(self):
        self._dispatch()

    def do_POST(self):
        self._dispatch()

    def do_PUT(self):
        self._dispatch()

    def do_DELETE(self):
        self._dispatch()

    def _dispatch(self):
        method, path, query = self._route()
        try:
            if path == "/" or path == "/index.html":
                return self._serve_static("index.html")
            if path.startswith("/static/"):
                return self._serve_static(path[len("/static/"):])
            if path == "/api/login" and method == "POST":
                return self._login()
            if path == "/api/logout" and method == "POST":
                return self._logout()
            if path == "/api/me" and method == "GET":
                return self._send(200, AuthService.public(self._user()))
            if path == "/api/modules" and method == "GET":
                self._user()
                return self._send(200, load_modules_config())
            if path == "/api/milestones" and method == "GET":
                self._user()
                return self._send(200, overall_progress())
            if path == "/api/roles" and method == "GET":
                self._user()
                return self._send(200, load_roles_config())
            if path == "/api/users" and method == "GET":
                user = self._user()
                self.auth.require(user, "users", "read")
                users = [AuthService.public(u) for u in
                         self.auth.store.list("users")]
                return self._send(200, {"users": users})
            if path == "/api/users" and method == "POST":
                user = self._user()
                self.auth.require(user, "users", "write")
                created = self.auth.create_user(**self._body())
                return self._send(201, AuthService.public(created))

            m = re.fullmatch(r"/api/(\w[\w-]*)(?:/([\w-]+)(?:/([\w-]+))?)?", path)
            if not m:
                return self._send(404, {"error": "not found"})
            resource, rid, sub = m.group(1), m.group(2), m.group(3)
            handler = getattr(self, f"_res_{resource}", None)
            if handler is None:
                return self._send(404, {"error": "unknown resource"})
            return handler(method, rid, sub, query)
        except AuthError as exc:
            msg = str(exc)
            code = 403 if msg.startswith("role ") or msg.startswith("teachers ") \
                or msg.startswith("not permitted") else 401
            return self._send(code, {"error": msg})
        except ValidationError as exc:
            return self._send(400, {"error": str(exc)})
        except NotFoundError as exc:
            return self._send(404, {"error": str(exc)})
        except ConflictError as exc:
            return self._send(409, {"error": str(exc)})
        except TypeError as exc:  # missing/unknown fields
            return self._send(400, {"error": f"invalid fields: {exc}"})

    # -- static ------------------------------------------------------------
    def _serve_static(self, name):
        full = os.path.normpath(os.path.join(STATIC_DIR, name))
        if not full.startswith(os.path.normpath(STATIC_DIR)) or \
                not os.path.isfile(full):
            return self._send(404, {"error": "not found"})
        with open(full, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type",
                         mimetypes.guess_type(full)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # -- auth --------------------------------------------------------------
    def _login(self):
        data = self._body()
        token, user = self.auth.login(data.get("username", ""),
                                      data.get("password", ""))
        self._send(200, {"token": token, "user": user})

    def _logout(self):
        header = self.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            self.auth.logout(header[7:])
        self._send(200, {"ok": True})

    # -- resources -----------------------------------------------------------
    def _res_students(self, method, rid, sub, query):
        user, svc = self._user(), self.service
        if rid is None and method == "GET":
            return self._send(200, {"students": svc.list_students(user)})
        if rid is None and method == "POST":
            return self._send(201, svc.create_student(user, **self._body()))
        if rid and sub is None and method == "GET":
            return self._send(200, svc.get_student(user, rid))
        if rid and sub is None and method == "PUT":
            return self._send(200, svc.update_student(user, rid, **self._body()))
        if rid and sub is None and method == "DELETE":
            svc.delete_student(user, rid)
            return self._send(204)
        if rid and sub == "gpa" and method == "GET":
            return self._send(200, svc.gpa(user, rid))
        if rid and sub == "grades" and method == "GET":
            return self._send(200, {"grades": svc.student_grades(user, rid)})
        if rid and sub == "fees" and method == "GET":
            return self._send(200, svc.student_fees(user, rid))
        return self._send(404, {"error": "not found"})

    def _res_teachers(self, method, rid, sub, query):
        user, svc = self._user(), self.service
        if rid is None and method == "GET":
            return self._send(200, {"teachers": svc.list_teachers(user)})
        if rid is None and method == "POST":
            return self._send(201, svc.create_teacher(user, **self._body()))
        if rid and sub is None and method == "GET":
            return self._send(200, svc.get_teacher(user, rid))
        if rid and sub is None and method == "DELETE":
            svc.delete_teacher(user, rid)
            return self._send(204)
        return self._send(404, {"error": "not found"})

    def _res_classes(self, method, rid, sub, query):
        user, svc = self._user(), self.service
        if rid is None and method == "GET":
            return self._send(200, {"classes": svc.list_classes(user)})
        if rid is None and method == "POST":
            return self._send(201, svc.create_class(user, **self._body()))
        if rid and sub is None and method == "GET":
            return self._send(200, svc.get_class(user, rid))
        if rid and sub is None and method == "DELETE":
            svc.delete_class(user, rid)
            return self._send(204)
        if rid and sub == "roster" and method == "GET":
            return self._send(200, {"roster": svc.class_roster(user, rid)})
        if rid and sub == "averages" and method == "GET":
            return self._send(200, {"averages": svc.class_averages(user, rid)})
        return self._send(404, {"error": "not found"})

    def _res_enrollments(self, method, rid, sub, query):
        user, svc = self._user(), self.service
        if rid is None and method == "GET":
            filters = {k: v[0] for k, v in query.items()
                       if k in ("student_id", "class_id")}
            return self._send(200, {"enrollments": svc.list_enrollments(user, **filters)})
        if rid is None and method == "POST":
            data = self._body()
            return self._send(201, svc.enroll(user, data.get("student_id"),
                                              data.get("class_id")))
        if rid and method == "DELETE":
            svc.unenroll(user, rid)
            return self._send(204)
        return self._send(404, {"error": "not found"})

    def _res_attendance(self, method, rid, sub, query):
        user, svc = self._user(), self.service
        if rid is None and method == "POST":
            data = self._body()
            return self._send(201, svc.mark_attendance(
                user, data.get("student_id"), data.get("class_id"),
                data.get("day"), data.get("status")))
        if rid is None and method == "GET":
            one = {k: v[0] for k, v in query.items()
                   if k in ("class_id", "student_id", "start", "end")}
            return self._send(200, svc.attendance_report(user, **one))
        return self._send(404, {"error": "not found"})

    def _res_grades(self, method, rid, sub, query):
        user, svc = self._user(), self.service
        if rid is None and method == "POST":
            data = self._body()
            return self._send(201, svc.record_grade(
                user, data.get("student_id"), data.get("class_id"),
                data.get("assignment"), data.get("score"),
                data.get("max_score", 100.0)))
        if rid is None and method == "GET" and "student_id" in query:
            sid = query["student_id"][0]
            return self._send(200, {"grades": svc.student_grades(user, sid),
                                    "gpa": svc.gpa(user, sid)})
        return self._send(404, {"error": "not found"})

    def _res_fees(self, method, rid, sub, query):
        user, svc = self._user(), self.service
        if rid is None and method == "POST":
            data = self._body()
            return self._send(201, svc.issue_invoice(
                user, data.get("student_id"), data.get("title"),
                data.get("amount"), data.get("due_date")))
        if rid is None and method == "GET" and "student_id" in query:
            return self._send(200, svc.student_fees(user, query["student_id"][0]))
        if rid and sub == "pay" and method == "POST":
            return self._send(200, svc.pay_invoice(
                user, rid, self._body().get("amount")))
        return self._send(404, {"error": "not found"})

    def _res_reports(self, method, rid, sub, query):
        user, svc = self._user(), self.service
        if rid == "revenue" and method == "GET":
            return self._send(200, svc.revenue_summary(user))
        if rid == "overview" and method == "GET":
            self.auth.require(user, "reports", "read")
            store = self.auth.store
            return self._send(200, {
                "students": len(store.list("students")),
                "teachers": len(store.list("teachers")),
                "classes": len(store.list("classes")),
                "enrollments": len(store.list("enrollments")),
                "modules": {k: v["name"] for k, v in MODULES.items()},
                "progress": overall_progress(),
            })
        return self._send(404, {"error": "not found"})


def create_server(port=8000, data_path=None):
    _, auth, service = build_services(data_path)
    Handler.auth = auth
    Handler.service = service
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)
