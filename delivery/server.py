"""JSON API + static UI over stdlib http.server (no dependencies).

Role travels in the X-Role header (default: stakeholder, read-only).

Endpoints:
  GET  /api/health
  GET  /api/roles
  GET  /api/scope            PUT /api/scope
  GET  /api/modules          POST /api/modules
  GET  /api/modules/:id      PATCH /api/modules/:id            (status | plan fields)
  GET  /api/mvp              GET /api/build-order
  GET  /api/architecture     POST /api/architecture
  POST /api/architecture/:id/select   POST /api/architecture/:id/reject
  GET  /api/stack
  GET  /api/milestones       POST /api/milestones
  GET  /api/milestones/:id   PATCH /api/milestones/:id
  GET  /api/timeline         GET /api/milestones/:id/health
  GET  /api/risks            POST /api/risks
  GET  /api/risks/:id        PATCH /api/risks/:id
  GET  /api/milestones/:id/criteria   POST /api/milestones/:id/criteria
  PATCH /api/criteria/:id
  GET  /api/milestones/:id/approvals  POST /api/milestones/:id/approvals
  GET  /  (dashboard UI) + /static/*
"""
from __future__ import annotations

import json
import sqlite3
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import service
from .config import SERVER_HOST, SERVER_PORT
from .models import (
    AcceptanceCriterion,
    Approval,
    ArchDecision,
    Milestone,
    Module,
    Risk,
    Scope,
)
from .store import applied_versions, connect, migrate

STATIC_DIR = Path(__file__).with_name("static")
INDEX_FILE = STATIC_DIR / "index.html"
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
}


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _context():
    """Per-server sqlite connection factory state (set by serve())."""
    raise AssertionError("server context not initialised")


class Handler(BaseHTTPRequestHandler):
    db_path = ":memory:"
    seed_on_boot = True
    _local = threading.local()
    _write_lock = threading.Lock()

    @classmethod
    def db(cls) -> sqlite3.Connection:
        conn = getattr(cls._local, "conn", None)
        if conn is None:
            from .store import server_connect

            conn = server_connect(cls.db_path)
            migrate(conn)
            if cls.seed_on_boot:
                from . import seed as seed_mod

                seed_mod.seed(conn)
            cls._local.conn = conn
        return conn

    # -- plumbing ----------------------------------------------------

    def log_message(self, *args):
        pass  # keep test output clean; run with -v server for logs

    def _role(self) -> str:
        return self.headers.get("X-Role", "stakeholder") or "stakeholder"

    def _send(self, status: int, payload: object) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type", CONTENT_TYPES.get(path.suffix, "application/octet-stream")
        )
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if not length:
            return {}
        try:
            data = json.loads(self.rfile.read(length).decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ApiError(400, "invalid JSON body")
        if not isinstance(data, dict):
            raise ApiError(400, "JSON body must be an object")
        return data

    def _dispatch(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        method = self.command
        query = urllib.parse.parse_qs(parsed.query)
        conn = self.db()
        role = self._role()

        # static UI
        if not parts or parts == ["index.html"]:
            return self._send_file(INDEX_FILE)
        if parts[0] == "static":
            target = (STATIC_DIR / "/".join(parts[1:])).resolve()
            if str(target).startswith(str(STATIC_DIR.resolve())) and target.is_file():
                return self._send_file(target)
            raise ApiError(404, "not found")
        if parts[0] != "api":
            raise ApiError(404, "not found")
        route = parts[1:]

        try:
            if route == ["health"]:
                return self._send(200, {"ok": True, "migrations": applied_versions(conn)})
            if route == ["roles"]:
                return self._send(200, {"roles": service.list_roles(conn)})
            if route == ["scope"]:
                if method == "GET":
                    return self._send(200, {"scope": service.get_scope(conn)})
                if method == "PUT":
                    body = self._read_json()
                    scope = Scope(
                        vision=body.get("vision", ""),
                        in_scope=list(body.get("in_scope", [])),
                        out_of_scope=list(body.get("out_of_scope", [])),
                        assumptions=list(body.get("assumptions", [])),
                        constraints=list(body.get("constraints", [])),
                    )
                    return self._send(200, {"scope": service.save_scope(conn, scope, role)})
                raise ApiError(405, "method not allowed")
            if route == ["mvp"] and method == "GET":
                return self._send(200, service.mvp_readiness(conn))
            if route == ["build-order"] and method == "GET":
                return self._send(200, {"order": service.build_order(conn)})
            if route == ["stack"] and method == "GET":
                return self._send(200, service.stack_summary(conn))
            if route == ["timeline"] and method == "GET":
                return self._send(200, service.timeline(conn))
            if route[0] == "modules":
                return self._modules(conn, role, method, route[1:], self._read_json if method in ("POST", "PATCH") else None)
            if route[0] == "architecture":
                return self._arch(conn, role, method, route[1:], self._read_json if method == "POST" else None)
            if route[0] == "milestones":
                return self._milestones(conn, role, method, route[1:], query)
            if route[0] == "risks":
                return self._risks(conn, role, method, route[1:], self._read_json if method in ("POST", "PATCH") else None)
            if route[0] == "criteria":
                return self._criteria(conn, role, method, route[1:])
        except (service.AuthError, service.ValidationError, service.NotFoundError):
            raise
        raise ApiError(404, "not found")

    # -- resources ---------------------------------------------------

    def _modules(self, conn, role, method, rest, read_body):
        if not rest:
            if method == "GET":
                return self._send(200, {"modules": service.list_modules(conn)})
            if method == "POST":
                body = read_body()
                module = Module(
                    name=body.get("name", ""),
                    description=body.get("description", ""),
                    priority=body.get("priority", "P2"),
                    mvp=bool(body.get("mvp", False)),
                    effort_points=int(body.get("effort_points", 1)),
                    status=body.get("status", "backlog"),
                    depends_on=list(body.get("depends_on", [])),
                )
                return self._send(201, {"module": service.create_module(conn, module, role)})
            raise ApiError(405, "method not allowed")
        module_id = self._int(rest[0], "module")
        if len(rest) == 1:
            if method == "GET":
                return self._send(200, {"module": service.get_module(conn, module_id)})
            if method == "PATCH":
                body = read_body()
                if set(body) == {"status"}:
                    updated = service.update_module_status(conn, module_id, body["status"], role)
                else:
                    updated = service.update_module_plan(conn, module_id, body, role)
                return self._send(200, {"module": updated})
            raise ApiError(405, "method not allowed")
        raise ApiError(404, "not found")

    def _arch(self, conn, role, method, rest, read_body):
        if not rest:
            if method == "GET":
                return self._send(200, {"decisions": service.list_arch(conn)})
            if method == "POST":
                body = read_body()
                decision = ArchDecision(
                    category=body.get("category", ""),
                    option_name=body.get("option_name", ""),
                    status=body.get("status", "proposed"),
                    rationale=body.get("rationale", ""),
                    decided_by=body.get("decided_by", ""),
                )
                return self._send(201, {"decision": service.propose_arch(conn, decision, role)})
            raise ApiError(405, "method not allowed")
        decision_id = self._int(rest[0], "architecture decision")
        if len(rest) == 2 and method == "POST" and rest[1] == "select":
            body = read_body()
            return self._send(
                200,
                {"decision": service.select_arch(conn, decision_id, body.get("rationale", ""), role)},
            )
        if len(rest) == 2 and method == "POST" and rest[1] == "reject":
            return self._send(200, {"decision": service.reject_arch(conn, decision_id, role)})
        raise ApiError(404, "not found")

    def _milestones(self, conn, role, method, rest, query):
        if not rest:
            if method == "GET":
                return self._send(200, {"milestones": service.list_milestones(conn)})
            if method == "POST":
                body = self._read_json()
                milestone = Milestone(
                    name=body.get("name", ""),
                    phase=body.get("phase", ""),
                    description=body.get("description", ""),
                    start_date=body.get("start_date", ""),
                    end_date=body.get("end_date", ""),
                    status=body.get("status", "draft"),
                    owner_role=body.get("owner_role", "product_owner"),
                )
                return self._send(201, {"milestone": service.create_milestone(conn, milestone, role)})
            raise ApiError(405, "method not allowed")
        milestone_id = self._int(rest[0], "milestone")
        if len(rest) == 1:
            if method == "GET":
                return self._send(200, {"milestone": service.get_milestone(conn, milestone_id)})
            if method == "PATCH":
                updated = service.update_milestone(conn, milestone_id, self._read_json(), role)
                return self._send(200, {"milestone": updated})
            raise ApiError(405, "method not allowed")
        if len(rest) == 2 and rest[1] == "health" and method == "GET":
            return self._send(200, service.milestone_health(conn, milestone_id))
        if len(rest) == 2 and rest[1] == "criteria":
            if method == "GET":
                return self._send(200, {"criteria": service.list_criteria(conn, milestone_id)})
            if method == "POST":
                body = self._read_json()
                criterion = AcceptanceCriterion(
                    milestone_id=milestone_id,
                    description=body.get("description", ""),
                    verification_method=body.get("verification_method", ""),
                    status=body.get("status", "pending"),
                )
                return self._send(201, {"criterion": service.add_criterion(conn, criterion, role)})
            raise ApiError(405, "method not allowed")
        if len(rest) == 2 and rest[1] == "approvals":
            if method == "GET":
                return self._send(200, {"approvals": service.list_approvals(conn, milestone_id)})
            if method == "POST":
                body = self._read_json()
                approval = Approval(
                    milestone_id=milestone_id,
                    approver_role=role,
                    decision=body.get("decision", ""),
                    comment=body.get("comment", ""),
                )
                return self._send(201, {"approval": service.decide_approval(conn, approval, role)})
            raise ApiError(405, "method not allowed")
        raise ApiError(404, "not found")

    def _risks(self, conn, role, method, rest, read_body):
        if not rest:
            if method == "GET":
                return self._send(200, {"risks": service.list_risks(conn)})
            if method == "POST":
                body = read_body()
                risk = Risk(
                    title=body.get("title", ""),
                    likelihood=body.get("likelihood", "medium"),
                    impact=body.get("impact", "medium"),
                    mitigation=body.get("mitigation", ""),
                    status=body.get("status", "open"),
                    milestone_id=body.get("milestone_id"),
                )
                return self._send(201, {"risk": service.create_risk(conn, risk, role)})
            raise ApiError(405, "method not allowed")
        risk_id = self._int(rest[0], "risk")
        if len(rest) == 1:
            if method == "GET":
                return self._send(200, {"risk": service.get_risk(conn, risk_id)})
            if method == "PATCH":
                return self._send(200, {"risk": service.update_risk(conn, risk_id, read_body(), role)})
            raise ApiError(405, "method not allowed")
        raise ApiError(404, "not found")

    def _criteria(self, conn, role, method, rest):
        if len(rest) == 1:
            criterion_id = self._int(rest[0], "criterion")
            if method == "GET":
                return self._send(200, {"criterion": service.get_criterion(conn, criterion_id)})
            if method == "PATCH":
                body = self._read_json()
                if set(body) != {"status"}:
                    raise ApiError(400, "only {status} may be patched on a criterion")
                updated = service.set_criterion_status(conn, criterion_id, body["status"], role)
                return self._send(200, {"criterion": updated})
            raise ApiError(405, "method not allowed")
        raise ApiError(404, "not found")

    @staticmethod
    def _int(raw: str, label: str) -> int:
        try:
            return int(raw)
        except ValueError:
            raise ApiError(404, f"invalid {label} id")

    # -- HTTP verbs ---------------------------------------------------

    def _handle(self) -> None:
        try:
            with type(self)._write_lock:
                self._dispatch()
        except ApiError as exc:
            self._send(exc.status, {"error": exc.message})
        except service.AuthError as exc:
            self._send(403, {"error": str(exc)})
        except service.ValidationError as exc:
            self._send(422, {"error": str(exc), "errors": exc.errors})
        except service.NotFoundError as exc:
            self._send(404, {"error": str(exc)})
        except (BrokenPipeError, ConnectionResetError):
            pass

    do_GET = _handle
    do_POST = _handle
    do_PUT = _handle
    do_PATCH = _handle


def serve(host: str = SERVER_HOST, port: int = SERVER_PORT,
          db_path: str = ":memory:", seed_on_boot: bool = True) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"db_path": db_path, "seed_on_boot": seed_on_boot})
    server = ThreadingHTTPServer((host, port), handler)
    # migrate + seed eagerly so errors surface before serving; keep the
    # connection open for :memory: so the shared-cache db survives.
    from .store import server_connect

    conn = server_connect(db_path)
    migrate(conn)
    if seed_on_boot:
        from . import seed as seed_mod

        seed_mod.seed(conn)
    if db_path == ":memory:":
        server._keeper_conn = conn  # noqa: SLF001 - intentional lifetime tie
    else:
        conn.close()
    return server


def main() -> None:
    import os

    db_path = os.environ.get("DELIVERY_DB", ":memory:")
    server = serve(db_path=db_path)
    print(f"SchoolMS delivery app on http://{SERVER_HOST}:{SERVER_PORT} (db={db_path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
