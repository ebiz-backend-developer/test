"""Users, roles, token auth and RBAC permission matrix (c1: scope & roles)."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets

from .store import Store, NotFoundError

ROLES = ("admin", "teacher", "student", "parent", "staff")

# resource -> {action -> roles allowed}; "*" means any authenticated user
# with ownership checks applied by the service layer where noted.
PERMISSIONS = {
    "students": {
        "read": {"admin", "teacher", "staff", "student", "parent"},
        "write": {"admin", "staff"},
    },
    "teachers": {
        "read": {"admin", "teacher", "staff"},
        "write": {"admin"},
    },
    "classes": {
        "read": {"admin", "teacher", "staff", "student", "parent"},
        "write": {"admin"},
    },
    "enrollments": {
        "read": {"admin", "teacher", "staff", "student", "parent"},
        "write": {"admin", "staff"},
    },
    "attendance": {
        "read": {"admin", "teacher", "staff", "student", "parent"},
        "write": {"admin", "teacher"},
    },
    "grades": {
        "read": {"admin", "teacher", "staff", "student", "parent"},
        "write": {"admin", "teacher"},
    },
    "fees": {
        "read": {"admin", "staff", "student", "parent"},
        "write": {"admin", "staff"},
    },
    "users": {
        "read": {"admin"},
        "write": {"admin"},
    },
    "reports": {
        "read": {"admin", "teacher", "staff"},
        "write": {"admin"},
    },
}


class AuthError(Exception):
    pass


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"{salt}${digest}"


def verify_password(password, stored):
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


class AuthService:
    """User accounts + bearer tokens. Tokens kept in memory."""

    def __init__(self, store: Store):
        self.store = store
        self._tokens = {}  # token -> user_id

    def create_user(self, username, password, role, link_id=""):
        username = username.strip().lower()
        if not username or not password:
            raise AuthError("username and password are required")
        if role not in ROLES:
            raise AuthError(f"role must be one of {ROLES}")
        if self.store.list("users", username=username):
            raise AuthError("username already exists")
        user = {
            "id": f"u-{secrets.token_hex(4)}",
            "username": username,
            "password": hash_password(password),
            "role": role,
            "link_id": link_id,  # student_id/teacher_id this account represents
        }
        return self.store.put("users", user["id"], user)

    def login(self, username, password):
        rows = self.store.list("users", username=username.strip().lower())
        if not rows or not verify_password(password, rows[0]["password"]):
            raise AuthError("invalid credentials")
        token = secrets.token_urlsafe(32)
        self._tokens[token] = rows[0]["id"]
        return token, self.public(rows[0])

    def logout(self, token):
        self._tokens.pop(token, None)

    def authenticate(self, token):
        if not token or token not in self._tokens:
            raise AuthError("missing or invalid token")
        try:
            return self.store.get("users", self._tokens[token])
        except NotFoundError:
            raise AuthError("account no longer exists")

    @staticmethod
    def public(user):
        return {k: v for k, v in user.items() if k != "password"}

    @staticmethod
    def can(role, resource, action):
        return role in PERMISSIONS.get(resource, {}).get(action, set())

    def require(self, user, resource, action):
        if not self.can(user["role"], resource, action):
            raise AuthError(f"role '{user['role']}' may not {action} {resource}")
        return user


def load_roles_config(path=None):
    """Roles reference (scope definition) loadable from config/roles.json."""
    path = path or os.path.join(os.path.dirname(__file__), "..", "config", "roles.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {
        "roles": [
            {"id": r, "permissions": {res: sorted(a for a, rs in acts.items() if r in rs)
                                      for res, acts in PERMISSIONS.items()}}
            for r in ROLES
        ]
    }
