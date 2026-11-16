"""Stdlib JSON API + static UI server for the Design Hub.

Run:  python3 run.py [--port 8130] [--db data/hub.db]
"""
from __future__ import annotations

import json
import mimetypes
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .models import (
    ConflictError,
    NewFlow,
    NewMilestone,
    NewModule,
    NewScopeItem,
    NewTechOption,
    NewWireframe,
    NotFoundError,
    ValidationError,
)
from .rbac import can
from .store import Store, connect, migrate

APP_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = APP_ROOT / "web"


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = handler.headers.get("Content-Length")
    if not length:
        return {}
    try:
        raw = handler.rfile.read(int(length)).decode("utf-8")
    except (ValueError, OSError):
        raise ApiError(400, "unreadable request body")
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ApiError(400, "request body must be valid JSON")
    if not isinstance(data, dict):
        raise ApiError(400, "request body must be a JSON object")
    return data


class Handler(BaseHTTPRequestHandler):
    store: Store
    server_version = "DesignHub/1.0"

    # -- plumbing ------------------------------------------------------
    def log_message(self, fmt: str, *args) -> None:  # quieter logs
        pass

    def _send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _current_user(self) -> dict | None:
        username = (self.headers.get("X-User") or "").strip()
        if not username:
            return None
        return self.store.get_user(username)

    def _require(self, action: str) -> dict:
        user = self._current_user()
        if user is None:
            raise ApiError(401, "unknown or missing X-User")
        if not can(user["role"], action):
            raise ApiError(403, f"role '{user['role']}' may not {action}")
        return user

    def _route(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        method = self.command
        query = parse_qs(parsed.query)

        try:
            if path == "/api/health" and method == "GET":
                return self._send_json({"ok": True})

            if path == "/api/roles" and method == "GET":
                return self._send_json(self.store.list_roles())

            if path == "/api/users" and method == "GET":
                return self._send_json(self.store.list_users())

            if path == "/api/scope" and method == "GET":
                return self._send_json(self.store.list_scope())
            if path == "/api/scope" and method == "POST":
                self._require("scope.write")
                body = _json_body(self)
                item = self.store.add_scope(NewScopeItem(
                    title=body.get("title", ""),
                    kind=body.get("kind", "in_scope"),
                    detail=body.get("detail", "")))
                return self._send_json(item, 201)

            if path == "/api/modules" and method == "GET":
                mvp_only = query.get("mvp", [""])[0] == "1"
                return self._send_json(self.store.list_modules(mvp_only))
            if path == "/api/modules" and method == "POST":
                self._require("modules.write")
                body = _json_body(self)
                mod = self.store.add_module(NewModule(
                    name=body.get("name", ""),
                    description=body.get("description", ""),
                    priority=body.get("priority", "P2"),
                    moscow=body.get("moscow", "should"),
                    mvp=body.get("mvp", True),
                    status=body.get("status", "planned"),
                    owner_role=body.get("owner_role", "product_manager")))
                return self._send_json(mod, 201)

            m = re.fullmatch(r"/api/modules/(\d+)", path)
            if m and method == "GET":
                return self._send_json(self.store.get_module(int(m.group(1))))
            if m and method == "PATCH":
                body = _json_body(self)
                keys = set(body)
                if keys <= {"status"} and keys:
                    user = self._current_user()
                    if user is None:
                        raise ApiError(401, "unknown or missing X-User")
                    if not can(user["role"], "modules.status"):
                        raise ApiError(403, "may not update module status")
                    return self._send_json(self.store.update_module_status(
                        int(m.group(1)), body.get("status", "")))
                self._require("modules.write")
                if "status" in body:
                    updated = self.store.update_module_status(
                        int(m.group(1)), body["status"])
                    return self._send_json(updated)
                raise ApiError(400, "PATCH modules supports {status} or"
                                    " use /prioritize for priority/mvp")

            m = re.fullmatch(r"/api/modules/(\d+)/prioritize", path)
            if m and method == "POST":
                self._require("modules.write")
                body = _json_body(self)
                if "priority" not in body or "mvp" not in body:
                    raise ApiError(400, "body needs {priority, mvp}")
                return self._send_json(self.store.prioritize_module(
                    int(m.group(1)), body["priority"], body["mvp"],
                    body.get("sort_order")))

            if path == "/api/tech" and method == "GET":
                return self._send_json(
                    self.store.list_tech(query.get("layer", [None])[0]))
            if path == "/api/tech" and method == "POST":
                self._require("tech.propose")
                body = _json_body(self)
                opt = self.store.add_tech(NewTechOption(
                    layer=body.get("layer", ""),
                    name=body.get("name", ""),
                    description=body.get("description", ""),
                    rationale=body.get("rationale", "")))
                return self._send_json(opt, 201)

            m = re.fullmatch(r"/api/tech/(\d+)/(select|reject)", path)
            if m and method == "POST":
                self._require("tech.select")
                body = _json_body(self)
                action = "selected" if m.group(2) == "select" else "rejected"
                return self._send_json(self.store.decide_tech(
                    int(m.group(1)), action, body.get("rationale", "")))

            if path == "/api/milestones" and method == "GET":
                return self._send_json(self.store.list_milestones())
            if path == "/api/milestones" and method == "POST":
                self._require("milestones.propose")
                body = _json_body(self)
                ms = self.store.add_milestone(NewMilestone(
                    title=body.get("title", ""),
                    description=body.get("description", ""),
                    due_date=body.get("due_date", "")))
                return self._send_json(ms, 201)

            m = re.fullmatch(r"/api/milestones/(\d+)/(submit|approve|reject)", path)
            if m and method == "POST":
                action = m.group(2)
                mid = int(m.group(1))
                if action == "submit":
                    self._require("milestones.propose")
                    return self._send_json(self.store.submit_milestone(mid))
                user = self._require("milestones.approve")
                decision = "approved" if action == "approve" else "rejected"
                return self._send_json(self.store.decide_milestone(
                    mid, decision, user["username"]))

            if path == "/api/flows" and method == "GET":
                return self._send_json(self.store.list_flows())
            if path == "/api/flows" and method == "POST":
                self._require("flows.write")
                body = _json_body(self)
                flow = self.store.add_flow(NewFlow(
                    name=body.get("name", ""),
                    persona=body.get("persona", ""),
                    device=body.get("device", "both"),
                    steps=body.get("steps", [])))
                return self._send_json(flow, 201)

            m = re.fullmatch(r"/api/flows/(\d+)", path)
            if m and method == "GET":
                return self._send_json(self.store.get_flow(int(m.group(1))))

            if path == "/api/wireframes" and method == "GET":
                return self._send_json(self.store.list_wireframes())
            if path == "/api/wireframes" and method == "POST":
                self._require("wireframes.write")
                body = _json_body(self)
                wf = self.store.add_wireframe(NewWireframe(
                    title=body.get("title", ""),
                    screen=body.get("screen", ""),
                    device=body.get("device", "desktop"),
                    module_id=body.get("module_id"),
                    blocks=body.get("blocks", [])))
                return self._send_json(wf, 201)

            m = re.fullmatch(r"/api/wireframes/(\d+)", path)
            if m and method == "GET":
                return self._send_json(self.store.get_wireframe(int(m.group(1))))

            if path == "/api/dashboard" and method == "GET":
                role = query.get("role", ["stakeholder"])[0]
                return self._send_json(self.store.dashboard(role))
        except (ValidationError, ConflictError) as exc:
            code = 409 if isinstance(exc, ConflictError) else 400
            return self._send_json({"error": str(exc)}, code)
        except NotFoundError as exc:
            return self._send_json({"error": str(exc)}, 404)
        except ApiError as exc:
            return self._send_json({"error": exc.message}, exc.status)

        if path.startswith("/api/"):
            return self._send_json({"error": "not found"}, 404)
        if method == "GET":
            return self._serve_static(path)
        return self._send_json({"error": "method not allowed"}, 405)

    def _serve_static(self, path: str) -> None:
        rel = "index.html" if path == "/" else path.lstrip("/").split("?")[0]
        # Block path traversal: only serve files inside WEB_ROOT.
        target = (WEB_ROOT / rel).resolve()
        if WEB_ROOT.resolve() not in target.parents and target != WEB_ROOT.resolve():
            return self._send_json({"error": "not found"}, 404)
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file() or target.suffix not in (
                ".html", ".css", ".js", ".svg", ".png", ".json"):
            return self._send_json({"error": "not found"}, 404)
        ctype, _ = mimetypes.guess_type(str(target))
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    _lock = threading.Lock()

    def _dispatch(self) -> None:
        # One shared SQLite connection: serialize request handling.
        with type(self)._lock:
            self._route()

    do_GET = _dispatch
    do_POST = _dispatch
    do_PATCH = _dispatch


def make_server(db_path: str | Path, port: int = 0) -> ThreadingHTTPServer:
    dbp = Path(db_path)
    dbp.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(dbp)
    migrate(conn)
    from .seed import seed

    seed(Store(conn))
    handler = type("HubHandler", (Handler,), {})
    handler.store = Store(conn)
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


def serve(db_path: str | Path = "data/hub.db", port: int = 8130) -> None:
    server = make_server(db_path, port)
    addr = f"http://127.0.0.1:{server.server_address[1]}"
    print(f"Design Hub running at {addr}  (db: {db_path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
