"""Shared test helpers: fresh seeded service and live HTTP server."""
from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from app.seed import seed
from app.server import Handler
from app.service import Service
from app.store import Store


def make_service() -> Service:
    store = Store(":memory:")
    seed(store)
    return Service(store)


class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        store = Store(":memory:")
        seed(store)
        Handler.service = Service(store)
        cls._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls._server.daemon_threads = True
        cls.port = cls._server.server_address[1]
        cls._thread = threading.Thread(target=cls._server.serve_forever, daemon=True)
        cls._thread.start()
        cls.addClassCleanup(cls._server.shutdown)
        cls.addClassCleanup(cls._server.server_close)

    def api(self, method: str, path: str, body: dict | None = None):
        url = f"http://127.0.0.1:{self.port}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode()
            try:
                return exc.code, json.loads(payload)
            except ValueError:
                return exc.code, {"raw": payload}
