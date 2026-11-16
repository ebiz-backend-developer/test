"""Teachers router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_roles

router = APIRouter(prefix="/teachers", tags=["teachers"])
read = require_roles("staff", "teacher")
write = require_roles("staff")


def _get_or_404(db: Session, teacher_id: int) -> models.Teacher:
    teacher = db.get(models.Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return teacher


@router.get("", response_model=list[schemas.TeacherOut])
def list_teachers(db: Session = Depends(get_db), _u=Depends(read)):
    return db.query(models.Teacher).order_by(models.Teacher.id).all()


@router.post("", response_model=schemas.TeacherOut, status_code=status.HTTP_201_CREATED)
def create_teacher(payload: schemas.TeacherCreate, db: Session = Depends(get_db), _u=Depends(write)):
    if db.query(models.Teacher).filter(models.Teacher.staff_no == payload.staff_no).first():
        raise HTTPException(status_code=409, detail="Staff number already exists")
    if payload.user_id is not None and db.get(models.User, payload.user_id) is None:
        raise HTTPException(status_code=400, detail="Linked user not found")
    teacher = models.Teacher(**payload.model_dump())
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


@router.get("/{teacher_id}", response_model=schemas.TeacherOut)
def get_teacher(teacher_id: int, db: Session = Depends(get_db), _u=Depends(read)):
    return _get_or_404(db, teacher_id)


@router.patch("/{teacher_id}", response_model=schemas.TeacherOut)
def update_teacher(teacher_id: int, payload: schemas.TeacherUpdate, db: Session = Depends(get_db),
                   _u=Depends(write)):
    teacher = _get_or_404(db, teacher_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(teacher, field, value)
    db.commit()
    db.refresh(teacher)
    return teacher


@router.delete("/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_teacher(teacher_id: int, db: Session = Depends(get_db), _u=Depends(write)):
    teacher = _get_or_404(db, teacher_id)
    db.delete(teacher)
    db.commit()
    return None
