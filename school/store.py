"""Thread-safe JSON-file storage. Collections keyed by record id."""
from __future__ import annotations

import copy
import json
import os
import threading
from dataclasses import asdict


class NotFoundError(KeyError):
    pass


class ConflictError(ValueError):
    pass


class Store:
    def __init__(self, path=None):
        self._path = path
        self._lock = threading.RLock()
        self._data = {}
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                self._data = json.load(fh)

    # -- persistence ----------------------------------------------------
    def _save(self):
        if not self._path:
            return
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        tmp = self._path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, sort_keys=True)
        os.replace(tmp, self._path)

    def _coll(self, name):
        return self._data.setdefault(name, {})

    # -- CRUD ------------------------------------------------------------
    def put(self, collection, record_id, record):
        with self._lock:
            if hasattr(record, "__dataclass_fields__"):
                record = asdict(record)
            self._coll(collection)[record_id] = copy.deepcopy(record)
            self._save()
            return copy.deepcopy(record)

    def get(self, collection, record_id):
        with self._lock:
            try:
                return copy.deepcopy(self._coll(collection)[record_id])
            except KeyError:
                raise NotFoundError(f"{collection}/{record_id} not found")

    def delete(self, collection, record_id):
        with self._lock:
            try:
                del self._coll(collection)[record_id]
            except KeyError:
                raise NotFoundError(f"{collection}/{record_id} not found")
            self._save()

    def list(self, collection, **filters):
        with self._lock:
            rows = list(self._coll(collection).values())
        out = []
        for row in rows:
            if all(row.get(k) == v for k, v in filters.items()):
                out.append(copy.deepcopy(row))
        return out

    def exists(self, collection, record_id):
        with self._lock:
            return record_id in self._coll(collection)
