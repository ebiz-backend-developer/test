"""HTTP server: JSON REST API + server-served dashboard UI (stdlib only)."""
from __future__ import annotations

import argparse
import json
import sqlite3
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import __version__, models, service
from .config import DEFAULT_PORT, db_path
from .models import (
    AcceptanceCriterion,
    Approval,
    ArchDecision,
    Milestone,
    Module,
    Risk,
    Scope,
)
from .seed import seed
from .store import init_db

STATIC_DIR = Path(__file__).parent / "static"


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
    db_file: str = ""
    server_version = f"delivery-milestones/{__version__}"

    # -- plumbing -----------------------------------------------------

    def log_message(self, fmt: str, *args) -> None:  # quieter logs
        pass

    def _conn(self) -> sqlite3.Connection:
        from .store import connect, migrate

        conn = connect(self.db_file)
        migrate(conn)
        return conn

    def _role(self) -> str:
        return (self.headers.get("X-Role") or "stakeholder").strip() or "stakeholder"

    def _send_json(self, status: int, payload) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: int, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _parse(self):
        parsed = urllib.parse.urlparse(self.path)
        return parsed.path, urllib.parse.parse_qs(parsed.query)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Role")
        self.end_headers()

    def do_GET(self) -> None:
        self._dispatch()

    def do_POST(self) -> None:
        self._dispatch()

    def do_PUT(self) -> None:
        self._dispatch()

    def do_PATCH(self) -> None:
        self._dispatch()

    def _dispatch(self) -> None:
        try:
            path, query = self._parse()
            if path == "/" or path == "/index.html":
                self._send_html(200, (STATIC_DIR / "index.html").read_text(encoding="utf-8"))
                return
            if not path.startswith("/api/v1/"):
                raise ApiError(404, f"not found: {path}")
            resource = path[len("/api/v1/"):]
            method = self.command
            conn = self._conn()
            try:
                result = self._route(conn, method, resource, query)
            finally:
                conn.close()
            self._send_json(200, result)
        except ApiError as exc:
            self._send_json(exc.status, {"error": exc.message})
        except service.AuthError as exc:
            self._send_json(403, {"error": str(exc)})
        except service.ValidationError as exc:
            self._send_json(400, {"error": str(exc), "details": exc.errors})
        except Exception as exc:  # never leak a traceback to clients
            self._send_json(500, {"error": f"internal error: {exc}"})

    # -- routing ------------------------------------------------------

    def _route(self, conn: sqlite3.Connection, method: str, resource: str, query: dict):
        role = self._role()
        parts = [p for p in resource.split("/") if p]
        if not parts:
            raise ApiError(404, "missing resource")

        if parts[0] == "health" and method == "GET":
            return {"status": "ok", "version": __version__}

        if parts[0] == "roles" and method == "GET":
            service.require_role(role)
            return {"roles": service.list_roles(conn)}

        if parts[0] == "scope":
            if method == "GET":
                service.require_role(role)
                return {"scope": service.get_scope(conn)}
            if method == "PUT":
                body = _json_body(self)
                scope = Scope(
                    vision=body.get("vision", ""),
                    in_scope=list(body.get("in_scope", [])),
                    out_of_scope=list(body.get("out_of_scope", [])),
                    assumptions=list(body.get("assumptions", [])),
                    constraints=list(body.get("constraints", [])),
                )
                return {"scope": service.save_scope(conn, scope, role)}
            raise ApiError(405, "scope supports GET, PUT")

        if parts[0] == "modules":
            if len(parts) == 1:
                if method == "GET":
                    service.require_role(role)
                    mvp_only = query.get("mvp_only", ["0"])[0] == "1"
                    return {"modules": service.list_modules(conn, mvp_only=mvp_only)}
                if method == "POST":
                    body = _json_body(self)
                    module = Module(
                        name=body.get("name", ""),
                        description=body.get("description", ""),
                        priority=body.get("priority", "P2"),
                        mvp=bool(body.get("mvp", False)),
                        effort_points=int(body.get("effort_points", 1)),
                        status=body.get("status", "backlog"),
                        depends_on=list(body.get("depends_on", [])),
                    )
                    return {"module": service.create_module(conn, module, role)}
                raise ApiError(405, "modules supports GET, POST")
            if len(parts) == 2 and method == "PATCH":
                return {"module": service.update_module(conn, int(parts[1]), _json_body(self), role)}
            raise ApiError(404, f"not found: {resource}")

        if parts[0] == "mvp" and method == "GET":
            service.require_role(role)
            return service.mvp_summary(conn)

        if parts[0] == "arch":
            if method == "GET":
                service.require_role(role)
                selected_only = query.get("selected_only", ["0"])[0] == "1"
                return {"decisions": service.list_arch(conn, selected_only=selected_only)}
            if method == "POST":
                body = _json_body(self)
                decision = ArchDecision(
                    category=body.get("category", ""),
                    option_name=body.get("option_name", ""),
                    status=body.get("status", "proposed"),
                    rationale=body.get("rationale", ""),
                    decided_by=body.get("decided_by", "") or role,
                )
                return {"decision": service.save_arch(conn, decision, role)}
            raise ApiError(405, "arch supports GET, POST")

        if parts[0] == "milestones":
            if len(parts) == 1:
                if method == "GET":
                    service.require_role(role)
                    return {"milestones": service.list_milestones(conn)}
                if method == "POST":
                    body = _json_body(self)
                    milestone = Milestone(
                        name=body.get("name", ""),
                        phase=body.get("phase", ""),
                        description=body.get("description", ""),
                        start_date=body.get("start_date", ""),
                        end_date=body.get("end_date", ""),
                        status=body.get("status", "draft"),
                        owner_role=body.get("owner_role", "product_owner"),
                    )
                    return {"milestone": service.create_milestone(conn, milestone, role)}
                raise ApiError(405, "milestones supports GET, POST")
            if len(parts) == 2:
                milestone_id = int(parts[1])
                if method == "GET":
                    service.require_role(role)
                    return service.get_milestone(conn, milestone_id)
                if method == "PATCH":
                    return {"milestone": service.update_milestone(conn, milestone_id, _json_body(self), role)}
            raise ApiError(404, f"not found: {resource}")

        if parts[0] == "risks":
            if method == "GET":
                service.require_role(role)
                milestone_id = query.get("milestone_id", [None])[0]
                mid = int(milestone_id) if milestone_id else None
                return {"risks": service.list_risks(conn, mid)}
            if method == "POST":
                body = _json_body(self)
                risk = Risk(
                    title=body.get("title", ""),
                    likelihood=body.get("likelihood", "medium"),
                    impact=body.get("impact", "medium"),
                    mitigation=body.get("mitigation", ""),
                    status=body.get("status", "open"),
                    milestone_id=body.get("milestone_id"),
                    id=body.get("id"),
                )
                return {"risk": service.save_risk(conn, risk, role)}
            raise ApiError(405, "risks supports GET, POST")

        if parts[0] == "criteria":
            if method == "GET":
                service.require_role(role)
                milestone_id = query.get("milestone_id", [None])[0]
                mid = int(milestone_id) if milestone_id else None
                return {"criteria": service.list_criteria(conn, mid)}
            if method == "POST":
                body = _json_body(self)
                criterion = AcceptanceCriterion(
                    milestone_id=body.get("milestone_id"),
                    description=body.get("description", ""),
                    verification_method=body.get("verification_method", ""),
                    status=body.get("status", "pending"),
                    id=body.get("id"),
                )
                return {"criterion": service.save_criterion(conn, criterion, role)}
            raise ApiError(405, "criteria supports GET, POST")

        if parts[0] == "approvals":
            if method == "GET":
                service.require_role(role)
                milestone_id = query.get("milestone_id", [None])[0]
                mid = int(milestone_id) if milestone_id else None
                return {"approvals": service.list_approvals(conn, mid)}
            if method == "POST":
                body = _json_body(self)
                approval = Approval(
                    milestone_id=body.get("milestone_id"),
                    approver_role=body.get("approver_role") or role,
                    decision=body.get("decision", ""),
                    comment=body.get("comment", ""),
                )
                return {"approval": service.record_approval(conn, approval, role)}
            raise ApiError(405, "approvals supports GET, POST")

        if parts[0] == "roadmap" and method == "GET":
            service.require_role(role)
            return service.roadmap(conn)

        raise ApiError(404, f"not found: {resource}")


def build_server(host: str, port: int, db_file: str) -> ThreadingHTTPServer:
    handler = type("BoundHandler", (Handler,), {"db_file": db_file})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Delivery milestones server (API + dashboard UI)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--db", default=None, help="SQLite file (default: data/delivery.db)")
    parser.add_argument("--no-seed", action="store_true", help="skip seeding the initial plan")
    args = parser.parse_args(argv)

    path = db_path(args.db)
    conn = init_db(path)
    if not args.no_seed:
        added = seed(conn)
        if any(added.values()):
            print(f"seeded initial delivery plan: {added}")
    conn.close()

    server = build_server(args.host, args.port, str(path))
    print(f"delivery-milestones {__version__} on http://{args.host}:{args.port}/ (db: {path})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
