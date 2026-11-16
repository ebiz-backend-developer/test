"""Classes and enrollments routers (roster management with capacity checks)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_roles

router = APIRouter(tags=["classes"])
read = require_roles("staff", "teacher", "student")
write = require_roles("staff")


def _class_out(db: Session, cls: models.SchoolClass) -> schemas.ClassOut:
    enrolled = db.query(func.count(models.Enrollment.id)).filter(
        models.Enrollment.class_id == cls.id,
        models.Enrollment.status == "active",
    ).scalar()
    out = schemas.ClassOut.model_validate(cls)
    out.enrolled = enrolled or 0
    return out


@router.get("/classes", response_model=list[schemas.ClassOut])
def list_classes(db: Session = Depends(get_db), _u=Depends(read)):
    return [_class_out(db, c) for c in db.query(models.SchoolClass).order_by(models.SchoolClass.id).all()]


@router.post("/classes", response_model=schemas.ClassOut, status_code=status.HTTP_201_CREATED)
def create_class(payload: schemas.ClassCreate, db: Session = Depends(get_db), _u=Depends(write)):
    if db.query(models.SchoolClass).filter(models.SchoolClass.code == payload.code).first():
        raise HTTPException(status_code=409, detail="Class code already exists")
    if payload.teacher_id is not None and db.get(models.Teacher, payload.teacher_id) is None:
        raise HTTPException(status_code=400, detail="Teacher not found")
    cls = models.SchoolClass(**payload.model_dump())
    db.add(cls)
    db.commit()
    db.refresh(cls)
    return _class_out(db, cls)


@router.get("/classes/{class_id}", response_model=schemas.ClassOut)
def get_class(class_id: int, db: Session = Depends(get_db), _u=Depends(read)):
    cls = db.get(models.SchoolClass, class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="Class not found")
    return _class_out(db, cls)


@router.patch("/classes/{class_id}", response_model=schemas.ClassOut)
def update_class(class_id: int, payload: schemas.ClassUpdate, db: Session = Depends(get_db), _u=Depends(write)):
    cls = db.get(models.SchoolClass, class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="Class not found")
    if payload.teacher_id is not None and db.get(models.Teacher, payload.teacher_id) is None:
        raise HTTPException(status_code=400, detail="Teacher not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(cls, field, value)
    db.commit()
    db.refresh(cls)
    return _class_out(db, cls)


@router.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(class_id: int, db: Session = Depends(get_db), _u=Depends(write)):
    cls = db.get(models.SchoolClass, class_id)
    if cls is None:
        raise HTTPException(status_code=404, detail="Class not found")
    db.delete(cls)
    db.commit()
    return None


@router.get("/classes/{class_id}/roster", response_model=list[schemas.StudentOut])
def class_roster(class_id: int, db: Session = Depends(get_db), _u=Depends(read)):
    if db.get(models.SchoolClass, class_id) is None:
        raise HTTPException(status_code=404, detail="Class not found")
    enrollments = db.query(models.Enrollment).filter(
        models.Enrollment.class_id == class_id, models.Enrollment.status == "active"
    ).all()
    return [e.student for e in enrollments]


# --- Enrollments --------------------------------------------------------------
enroll_router = APIRouter(prefix="/enrollments", tags=["enrollments"])
enroll_read = require_roles("staff", "teacher")
enroll_write = require_roles("staff")


@enroll_router.get("", response_model=list[schemas.EnrollmentOut])
def list_enrollments(class_id: int | None = None, student_id: int | None = None,
                     db: Session = Depends(get_db), _u=Depends(enroll_read)):
    query = db.query(models.Enrollment).order_by(models.Enrollment.id)
    if class_id is not None:
        query = query.filter(models.Enrollment.class_id == class_id)
    if student_id is not None:
        query = query.filter(models.Enrollment.student_id == student_id)
    return query.all()


@enroll_router.post("", response_model=schemas.EnrollmentOut, status_code=status.HTTP_201_CREATED)
def enroll(payload: schemas.EnrollmentCreate, db: Session = Depends(get_db), _u=Depends(enroll_write)):
    student = db.get(models.Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=400, detail="Student not found")
    cls = db.get(models.SchoolClass, payload.class_id)
    if cls is None:
        raise HTTPException(status_code=400, detail="Class not found")
    existing = db.query(models.Enrollment).filter(
        models.Enrollment.student_id == payload.student_id,
        models.Enrollment.class_id == payload.class_id,
    ).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Student already enrolled in this class")
    enrolled = db.query(func.count(models.Enrollment.id)).filter(
        models.Enrollment.class_id == payload.class_id,
        models.Enrollment.status == "active",
    ).scalar()
    if (enrolled or 0) >= cls.capacity:
        raise HTTPException(status_code=409, detail="Class is at full capacity")
    enrollment = models.Enrollment(student_id=payload.student_id, class_id=payload.class_id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


@enroll_router.delete("/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
def unenroll(enrollment_id: int, db: Session = Depends(get_db), _u=Depends(enroll_write)):
    enrollment = db.get(models.Enrollment, enrollment_id)
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    db.delete(enrollment)
    db.commit()
    return None
