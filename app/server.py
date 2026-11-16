"""HTTP JSON API + static UI. Stdlib only (http.server).

Auth: X-Role header selects the caller's school role, X-User names the actor.
Reads are open; every write is gated by the RBAC matrix in app.rbac.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import service
from .seed import seed
from .store import Store

APP_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = APP_ROOT / "web"

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json",
}


class Handler(BaseHTTPRequestHandler):
    store: Store

    # -- plumbing ------------------------------------------------------
    def log_message(self, *args):
        pass

    def _role(self) -> str | None:
        role = self.headers.get("X-Role", "").strip() or None
        return role

    def _actor(self) -> str:
        return self.headers.get("X-User", "").strip() or "anonymous"

    def _send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message: str, status: int) -> None:
        self._send_json({"error": message}, status)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            raise service.ServiceError("request body is not valid JSON")

    def _serve_static(self, path: str) -> bool:
        rel = path.lstrip("/") or "index.html"
        target = (WEB_ROOT / rel).resolve()
        if WEB_ROOT not in target.parents and target != WEB_ROOT:
            return False
        if target.is_dir():
            target = target / "index.html"
        if not target.exists() or target.suffix not in CONTENT_TYPES:
            return False
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES[target.suffix])
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        return True

    # -- routing -------------------------------------------------------
    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        query = parse_qs(parsed.query)
        try:
            if not parts or parts[0] != "api":
                if not self._serve_static(parsed.path):
                    self._send_error("not found", 404)
                return
            resource = parts[1] if len(parts) > 1 else ""
            store = self.store
            if resource == "health":
                self._send_json({"ok": True})
            elif resource == "scope":
                self._send_json(service.list_scope(
                    store, query.get("kind", [None])[0]))
            elif resource == "stakeholders":
                self._send_json(service.list_stakeholders(store))
            elif resource == "roles":
                if len(parts) > 2:
                    self._send_json(service.role_detail(store, parts[2]))
                else:
                    self._send_json(service.list_roles(store))
            elif resource == "workflows":
                if len(parts) > 2:
                    self._send_json(
                        service.workflow_payload(store, parts[2]))
                else:
                    self._send_json(service.list_workflows(store))
            elif resource == "instances":
                if len(parts) > 2:
                    self._send_json(
                        service.get_instance(store, int(parts[2])))
                else:
                    self._send_json(service.list_instances(
                        store, query.get("workflow", [None])[0],
                        query.get("status", [None])[0]))
            elif resource == "modules":
                if len(parts) > 2 and parts[2] == "mvp":
                    self._send_json(service.mvp_summary(store))
                else:
                    self._send_json(service.list_modules(store))
            elif resource == "tech":
                if len(parts) > 2 and parts[2] == "selected":
                    self._send_json(service.selected_stack(store))
                else:
                    self._send_json(service.list_tech(
                        store, query.get("category", [None])[0],
                        query.get("status", [None])[0]))
            elif resource == "milestones":
                self._send_json(service.list_milestones(store))
            elif resource == "users":
                self._send_json(service.list_users(store))
            elif resource == "audit":
                self._send_json(service.list_audit(
                    store, int(query.get("limit", ["100"])[0])))
            else:
                self._send_error("not found", 404)
        except service.ServiceError as exc:
            self._send_error(str(exc), exc.status)
        except ValueError:
            self._send_error("bad id in path", 400)

    def do_POST(self):  # noqa: N802
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        try:
            body = self._read_json()
            role, actor, store = self._role(), self._actor(), self.store
            if len(parts) < 2 or parts[0] != "api":
                self._send_error("not found", 404)
            elif parts[1] == "scope":
                self._send_json(service.add_scope_item(
                    store, actor, role, body.get("kind", ""),
                    body.get("title", ""), body.get("detail", "")), 201)
            elif parts[1] == "workflows" and len(parts) == 4 and parts[3] == "instances":
                self._send_json(service.start_instance(
                    store, actor, role, parts[2]), 201)
            elif parts[1] == "instances" and len(parts) == 4 and parts[3] == "advance":
                self._send_json(service.advance_instance(
                    store, actor, role, int(parts[2]),
                    body.get("note", "")))
            elif parts[1] == "instances" and len(parts) == 4 and parts[3] == "cancel":
                self._send_json(service.cancel_instance(
                    store, actor, role, int(parts[2]),
                    body.get("note", "")))
            elif parts[1] == "tech" and len(parts) == 2:
                self._send_json(service.propose_tech(
                    store, actor, role, body.get("category", ""),
                    body.get("name", ""), body.get("detail", ""),
                    body.get("rationale", "")), 201)
            elif parts[1] == "tech" and len(parts) == 4 and parts[3] == "select":
                self._send_json(service.select_tech(
                    store, actor, role, int(parts[2]),
                    body.get("rationale", "")))
            elif parts[1] == "tech" and len(parts) == 4 and parts[3] == "reject":
                self._send_json(service.reject_tech(
                    store, actor, role, int(parts[2]),
                    body.get("rationale", "")))
            elif parts[1] == "milestones" and len(parts) == 2:
                self._send_json(service.propose_milestone(
                    store, actor, role, body.get("code", ""),
                    body.get("title", ""), body.get("goal", ""),
                    body.get("exit_criteria", "")), 201)
            elif parts[1] == "milestones" and len(parts) == 4 and parts[3] == "approve":
                self._send_json(service.decide_milestone(
                    store, actor, role, parts[2], "approved",
                    body.get("note", "")))
            elif parts[1] == "milestones" and len(parts) == 4 and parts[3] == "reject":
                self._send_json(service.decide_milestone(
                    store, actor, role, parts[2], "rejected",
                    body.get("note", "")))
            elif parts[1] == "users" and len(parts) == 2:
                self._send_json(service.add_user(
                    store, actor, role, body.get("name", ""),
                    body.get("email", ""), body.get("role", "")), 201)
            else:
                self._send_error("not found", 404)
        except service.ServiceError as exc:
            self._send_error(str(exc), exc.status)
        except ValueError:
            self._send_error("bad id in path", 400)

    def do_PATCH(self):  # noqa: N802
        parts = [p for p in urlparse(self.path).path.split("/") if p]
        try:
            body = self._read_json()
            role, actor, store = self._role(), self._actor(), self.store
            if len(parts) == 3 and parts[0] == "api" and parts[1] == "stakeholders":
                self._send_json(service.update_stakeholder(
                    store, actor, role, parts[2], **{
                        k: body[k] for k in
                        ("label", "interest", "primary_role", "journey_ref")
                        if k in body}))
            elif len(parts) == 3 and parts[0] == "api" and parts[1] == "modules":
                self._send_json(service.update_module(
                    store, actor, role, parts[2],
                    body.get("priority"), body.get("status")))
            elif len(parts) == 3 and parts[0] == "api" and parts[1] == "milestones":
                if "status" not in body:
                    raise service.ServiceError(
                        "tracking needs a 'status' field")
                self._send_json(service.track_milestone(
                    store, actor, role, parts[2], body["status"]))
            else:
                self._send_error("not found", 404)
        except service.ServiceError as exc:
            self._send_error(str(exc), exc.status)


def make_server(db_path: str = "data/school.db", port: int = 8133,
                do_seed: bool = True) -> ThreadingHTTPServer:
    store = Store(db_path)
    if do_seed and not store.query_one("SELECT code FROM roles LIMIT 1"):
        seed(store)
    handler = type("BoundHandler", (Handler,), {"store": store})
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


def serve(db_path: str = "data/school.db", port: int = 8133) -> None:
    server = make_server(db_path, port)
    print(f"Requirements & roles service on http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Requirements & roles server")
    parser.add_argument("--port", type=int, default=8133)
    parser.add_argument("--db", default="data/school.db")
    args = parser.parse_args()
    serve(args.db, args.port)


if __name__ == "__main__":
    main()
