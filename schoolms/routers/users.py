"""Users router: admin-only account management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_roles
from ..plan import ROLES
from ..security import hash_password

router = APIRouter(prefix="/users", tags=["users"])
admin_only = require_roles("admin")


@router.get("", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db), _user=Depends(admin_only)):
    return db.query(models.User).order_by(models.User.id).all()


@router.post("", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db), _user=Depends(admin_only)):
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Unknown role: {payload.role}")
    if db.query(models.User).filter(models.User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username already taken")
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = models.User(
        username=payload.username,
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), _user=Depends(admin_only)):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: int, payload: schemas.UserUpdate, db: Session = Depends(get_db),
                _user=Depends(admin_only)):
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.role is not None and payload.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Unknown role: {payload.role}")
    for field in ("full_name", "email", "role", "is_active"):
        value = getattr(payload, field)
        if value is not None:
            setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user
