"""Auth dependencies and role-based access control (c1 roles enforced here)."""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .plan import ROLES
from .security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _forbidden(detail: str = "Forbidden") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    if credentials is None or not credentials.credentials:
        raise _unauthorized()
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token expired")
    except jwt.PyJWTError:
        raise _unauthorized("Invalid token")
    user = db.get(models.User, int(payload.get("sub", 0)))
    if user is None or not user.is_active:
        raise _unauthorized("User not found or inactive")
    return user


def require_roles(*roles: str):
    """Dependency factory: allow only users whose role is in ``roles``.

    The ``admin`` role bypasses every check (``*`` permission in plan.ROLES).
    """
    unknown = [r for r in roles if r not in ROLES]
    if unknown:
        raise ValueError(f"Unknown roles in RBAC rule: {unknown}")

    def checker(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role == "admin" or user.role in roles:
            return user
        raise _forbidden(f"Requires one of roles: {', '.join(roles)}")

    return checker


def role_allows(role: str, permission: str) -> bool:
    """Pure helper mirroring the RBAC matrix (used by tests and UI hints)."""
    perms = ROLES.get(role, {}).get("permissions", [])
    return "*" in perms or permission in perms
