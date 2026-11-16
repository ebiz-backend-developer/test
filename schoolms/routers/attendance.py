"""Attendance router: daily capture (upsert) and summaries."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(prefix="/attendance", tags=["attendance"])
read = require_roles("staff", "teacher")
write = require_roles("staff", "teacher")


@router.post("", response_model=list[schemas.AttendanceOut])
def mark_attendance(records: list[schemas.AttendanceMark], db: Session = Depends(get_db), _u=Depends(write)):
    if not records:
        raise HTTPException(status_code=400, detail="No attendance records supplied")
    out: list[models.Attendance] = []
    for rec in records:
        if db.get(models.Student, rec.student_id) is None:
            raise HTTPException(status_code=400, detail=f"Student {rec.student_id} not found")
        if db.get(models.SchoolClass, rec.class_id) is None:
            raise HTTPException(status_code=400, detail=f"Class {rec.class_id} not found")
        row = db.query(models.Attendance).filter(
            models.Attendance.student_id == rec.student_id,
            models.Attendance.class_id == rec.class_id,
            models.Attendance.day == rec.day,
        ).first()
        if row is None:
            row = models.Attendance(**rec.model_dump())
            db.add(row)
        else:
            row.status = rec.status
            row.note = rec.note
        out.append(row)
    db.commit()
    for row in out:
        db.refresh(row)
    return out


@router.get("", response_model=list[schemas.AttendanceOut])
def list_attendance(class_id: int | None = None, student_id: int | None = None,
                    day: dt.date | None = None, db: Session = Depends(get_db), _u=Depends(read)):
    query = db.query(models.Attendance).order_by(models.Attendance.day, models.Attendance.id)
    if class_id is not None:
        query = query.filter(models.Attendance.class_id == class_id)
    if student_id is not None:
        query = query.filter(models.Attendance.student_id == student_id)
    if day is not None:
        query = query.filter(models.Attendance.day == day)
    return query.all()


@router.get("/summary", response_model=schemas.AttendanceSummary)
def attendance_summary(class_id: int, day: dt.date | None = None,
                       db: Session = Depends(get_db), _u=Depends(read)):
    query = db.query(models.Attendance).filter(models.Attendance.class_id == class_id)
    if day is not None:
        query = query.filter(models.Attendance.day == day)
    rows = query.all()
    counts = {"present": 0, "absent": 0, "late": 0, "excused": 0}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    total = len(rows)
    rate = round((counts["present"] + counts["late"] * 0.5) / total, 4) if total else 0.0
    return schemas.AttendanceSummary(
        class_id=class_id, day=day, total=total, rate=rate,
        present=counts["present"], absent=counts["absent"],
        late=counts["late"], excused=counts["excused"],
    )


@router.get("/mine", response_model=list[schemas.AttendanceOut])
def my_attendance(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if user.role not in ("student", "parent"):
        raise HTTPException(status_code=403, detail="Only student/parent self-service")
    student = db.query(models.Student).filter(models.Student.user_id == user.id).first()
    if student is None:
        return []
    return db.query(models.Attendance).filter(
        models.Attendance.student_id == student.id).order_by(models.Attendance.day).all()
