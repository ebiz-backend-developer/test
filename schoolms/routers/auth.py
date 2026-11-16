"""Auth router: register, login, me."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user
from ..plan import ROLES
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    role = payload.role if payload.role in ROLES else None
    if role is None:
        raise HTTPException(status_code=400, detail=f"Unknown role: {payload.role}")
    # Self-registration may not mint privileged accounts.
    if role in ("admin", "staff"):
        raise HTTPException(status_code=403, detail="Use an admin account to create staff/admin users")
    if db.query(models.User).filter(models.User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username already taken")
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = models.User(
        username=payload.username,
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return schemas.TokenOut(
        access_token=create_access_token(user.id, user.username, user.role),
        user=schemas.UserOut.model_validate(user),
    )


@router.post("/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    return schemas.TokenOut(
        access_token=create_access_token(user.id, user.username, user.role),
        user=schemas.UserOut.model_validate(user),
    )


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return schemas.UserOut.model_validate(user)
