"""Shared test helpers: fresh in-memory migrated DB per test."""
import json
import unittest

from mvp import api, store


class DbTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = store.connect(":memory:")
        store.migrate(self.conn)

    def tearDown(self):
        self.conn.close()

    def call(self, method, path, role="admin", body=None):
        raw = json.dumps(body).encode() if body is not None else b""
        return api.dispatch(self.conn, method, path, {"x-role": role}, raw)
