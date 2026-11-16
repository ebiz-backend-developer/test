"""Dashboard router: operational overview stats."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import require_roles

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
read = require_roles("staff", "teacher", "student", "parent")


@router.get("/stats")
def stats(db: Session = Depends(get_db), _u=Depends(read)):
    today = dt.date.today()
    present_today = db.query(func.count(models.Attendance.id)).filter(
        models.Attendance.day == today, models.Attendance.status == "present").scalar()
    total_today = db.query(func.count(models.Attendance.id)).filter(
        models.Attendance.day == today).scalar()
    return {
        "students": db.query(func.count(models.Student.id)).scalar(),
        "active_students": db.query(func.count(models.Student.id)).filter(
            models.Student.status == "active").scalar(),
        "teachers": db.query(func.count(models.Teacher.id)).scalar(),
        "classes": db.query(func.count(models.SchoolClass.id)).scalar(),
        "enrollments": db.query(func.count(models.Enrollment.id)).scalar(),
        "assignments": db.query(func.count(models.Assignment.id)).scalar(),
        "grades_recorded": db.query(func.count(models.Grade.id)).scalar(),
        "attendance_today": {"present": present_today or 0, "total": total_today or 0},
        "users_by_role": [
            {"role": role, "count": count}
            for role, count in db.query(models.User.role, func.count(models.User.id))
            .group_by(models.User.role).all()
        ],
    }
