"""Students router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_roles

router = APIRouter(prefix="/students", tags=["students"])
read = require_roles("staff", "teacher")
write = require_roles("staff")


def _get_or_404(db: Session, student_id: int) -> models.Student:
    student = db.get(models.Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.get("", response_model=list[schemas.StudentOut])
def list_students(status_filter: str | None = None, db: Session = Depends(get_db), _u=Depends(read)):
    query = db.query(models.Student).order_by(models.Student.id)
    if status_filter:
        query = query.filter(models.Student.status == status_filter)
    return query.all()


@router.post("", response_model=schemas.StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(payload: schemas.StudentCreate, db: Session = Depends(get_db), _u=Depends(write)):
    if db.query(models.Student).filter(models.Student.admission_no == payload.admission_no).first():
        raise HTTPException(status_code=409, detail="Admission number already exists")
    if payload.user_id is not None and db.get(models.User, payload.user_id) is None:
        raise HTTPException(status_code=400, detail="Linked user not found")
    student = models.Student(**payload.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get("/{student_id}", response_model=schemas.StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db), _u=Depends(read)):
    return _get_or_404(db, student_id)


@router.patch("/{student_id}", response_model=schemas.StudentOut)
def update_student(student_id: int, payload: schemas.StudentUpdate, db: Session = Depends(get_db),
                   _u=Depends(write)):
    student = _get_or_404(db, student_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    db.commit()
    db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: Session = Depends(get_db), _u=Depends(write)):
    student = _get_or_404(db, student_id)
    db.delete(student)
    db.commit()
    return None
