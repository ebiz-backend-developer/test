#!/usr/bin/env python3
"""Runnable server: JSON API + static UI. Stdlib only.

Usage: python3 server.py [--port 8000] [--db school.db] [--seed]
"""
import argparse
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from mvp import api, store

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(ROOT, "static")
DB_PATH = os.path.join(ROOT, "school.db")


class Handler(BaseHTTPRequestHandler):
    server_version = "SchoolMVP/1.0"

    def log_message(self, *args):
        pass

    def _send(self, status, payload, content_type="application/json"):
        body = payload if isinstance(payload, bytes) else \
            json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            path = "/index.html"
        target = os.path.normpath(os.path.join(STATIC, path.lstrip("/")))
        if not target.startswith(STATIC) or not os.path.isfile(target):
            self._send(404, {"error": "not found"})
            return
        ctype = mimetypes.guess_type(target)[0] or "application/octet-stream"
        with open(target, "rb") as fh:
            self._send(200, fh.read(), ctype)

    def _serve_api(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        headers = {k.lower(): v for k, v in self.headers.items()}
        conn = store.connect(DB_PATH)
        try:
            status, payload = api.dispatch(conn, self.command, self.path,
                                           headers, raw)
        finally:
            conn.close()
        self._send(status, payload)

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._serve_api()
        else:
            self._serve_static()

    def do_POST(self):
        self._serve_api()

    def do_DELETE(self):
        self._serve_api()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Role")
        self.end_headers()


def main(argv=None):
    global DB_PATH
    ap = argparse.ArgumentParser(description="School MVP server")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--db", default=DB_PATH)
    ap.add_argument("--seed", action="store_true", help="insert demo data")
    args = ap.parse_args(argv)
    DB_PATH = args.db
    conn = store.connect(DB_PATH)
    try:
        store.migrate(conn)
        if args.seed:
            store.seed_demo(conn)
    finally:
        conn.close()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"School MVP on http://127.0.0.1:{args.port} (db={DB_PATH})")
    server.serve_forever()


if __name__ == "__main__":
    main()
