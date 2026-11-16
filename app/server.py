"""HTTP JSON API + static UI server (standard library only)."""
from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .seed import seed
from .service import Service
from .store import Store

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = REPO_ROOT / "web"
CONTENT_TYPES = {".html": "text/html", ".css": "text/css", ".js": "text/javascript",
                 ".json": "application/json", ".png": "image/png"}


class Handler(BaseHTTPRequestHandler):
    service: Service
    lock = threading.Lock()

    def do_GET(self):
        with Handler.lock:
            self._do_GET()

    def do_POST(self):
        with Handler.lock:
            self._do_POST()

    def log_message(self, *args):  # quieter logs
        pass

    # -- helpers --
    def _send(self, status: int, payload: object, content_type="application/json"):
        body = payload if isinstance(payload, (bytes, str)) else json.dumps(payload)
        if isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _ok(self, payload: object):
        self._send(200, payload)

    def _err(self, status: int, message: str):
        self._send(status, {"error": message})

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode() or "{}")
        except json.JSONDecodeError:
            return {}

    # -- routing --
    def _do_GET(self):
        path = urlparse(self.path).path
        svc = self.service
        try:
            if path == "/api/health":
                return self._ok({"status": "ok"})
            if path == "/api/scope":
                return self._ok(svc.scope())
            if path == "/api/roles":
                return self._ok(svc.roles())
            if path == "/api/stakeholders":
                return self._ok(svc.stakeholders())
            if path == "/api/workflows":
                return self._ok(svc.workflow_list())
            if m := re.fullmatch(r"/api/workflows/([\w-]+)", path):
                return self._ok(svc.workflow_get(m.group(1)))
            if m := re.fullmatch(r"/api/workflow-instances/(\d+)", path):
                return self._ok(svc.instance_get(int(m.group(1))))
            if path == "/api/modules":
                return self._ok(svc.modules())
            if path == "/api/modules/mvp":
                return self._ok(svc.mvp())
            if path == "/api/architecture":
                return self._ok(svc.architecture())
            if path == "/api/milestones":
                return self._ok(svc.milestones())
            return self._serve_static(path)
        except (ValueError, LookupError) as exc:
            return self._err(404 if isinstance(exc, LookupError) else 400, str(exc))
        except PermissionError as exc:
            return self._err(403, str(exc))

    def _do_POST(self):
        path = urlparse(self.path).path
        svc = self.service
        try:
            if path == "/api/auth/check":
                data = self._body()
                return self._ok(svc.check_access(data.get("role", ""), data.get("permission", "")))
            if m := re.fullmatch(r"/api/workflows/([\w-]+)/instances", path):
                data = self._body()
                return self._send(201, svc.instance_start(m.group(1), data.get("subject", "")))
            if m := re.fullmatch(r"/api/workflow-instances/(\d+)/advance", path):
                data = self._body()
                return self._ok(svc.instance_advance(
                    int(m.group(1)), data.get("action", ""), data.get("actor_role", "")))
            if m := re.fullmatch(r"/api/modules/([\w-]+)/priority", path):
                data = self._body()
                return self._ok(svc.set_module_priority(m.group(1), int(data.get("priority", -1))))
            if m := re.fullmatch(r"/api/milestones/([\w-]+)/approve", path):
                data = self._body()
                return self._ok(svc.approve_milestone(
                    m.group(1), data.get("role", ""), data.get("approver", "")))
            return self._err(404, f"unknown route {path}")
        except (ValueError, LookupError) as exc:
            code = 404 if isinstance(exc, LookupError) else 400
            return self._err(code, str(exc))
        except PermissionError as exc:
            return self._err(403, str(exc))

    def _serve_static(self, path: str):
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        target = (WEB_ROOT / rel).resolve()
        if WEB_ROOT.resolve() not in target.parents and target != WEB_ROOT.resolve():
            return self._err(403, "forbidden")
        if not target.is_file():
            return self._err(404, f"unknown route {path}")
        self._send(200, target.read_bytes(),
                   CONTENT_TYPES.get(target.suffix, "application/octet-stream"))


def create_server(db_path: str = "schoolms.db", port: int = 8000) -> ThreadingHTTPServer:
    store = Store(db_path)
    seed(store)
    Handler.service = Service(store)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def main() -> None:
    import sys

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    db = sys.argv[2] if len(sys.argv) > 2 else "schoolms.db"
    server = create_server(db, port)
    print(f"SchoolMS task-3 server on http://127.0.0.1:{port} (db={db})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
