"""Grades router: assignments, scores (upsert), and report cards."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_roles

router = APIRouter(tags=["grades"])
read = require_roles("staff", "teacher")
write = require_roles("staff", "teacher")


def _letter(average_pct: float) -> str:
    for bound, grade in ((90, "A"), (80, "B"), (70, "C"), (60, "D")):
        if average_pct >= bound:
            return grade
    return "F"


@router.post("/assignments", response_model=schemas.AssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment(payload: schemas.AssignmentCreate, db: Session = Depends(get_db), _u=Depends(write)):
    if db.get(models.SchoolClass, payload.class_id) is None:
        raise HTTPException(status_code=400, detail="Class not found")
    assignment = models.Assignment(**payload.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/assignments", response_model=list[schemas.AssignmentOut])
def list_assignments(class_id: int | None = None, db: Session = Depends(get_db), _u=Depends(read)):
    query = db.query(models.Assignment).order_by(models.Assignment.id)
    if class_id is not None:
        query = query.filter(models.Assignment.class_id == class_id)
    return query.all()


@router.post("/grades", response_model=schemas.GradeOut, status_code=status.HTTP_201_CREATED)
def record_grade(payload: schemas.GradeCreate, db: Session = Depends(get_db), _u=Depends(write)):
    assignment = db.get(models.Assignment, payload.assignment_id)
    if assignment is None:
        raise HTTPException(status_code=400, detail="Assignment not found")
    if db.get(models.Student, payload.student_id) is None:
        raise HTTPException(status_code=400, detail="Student not found")
    if payload.score > assignment.max_score:
        raise HTTPException(status_code=400, detail="Score exceeds assignment max_score")
    grade = db.query(models.Grade).filter(
        models.Grade.assignment_id == payload.assignment_id,
        models.Grade.student_id == payload.student_id,
    ).first()
    if grade is None:
        grade = models.Grade(**payload.model_dump())
        db.add(grade)
    else:
        grade.score = payload.score
        grade.comment = payload.comment
    db.commit()
    db.refresh(grade)
    return grade


@router.get("/grades", response_model=list[schemas.GradeOut])
def list_grades(assignment_id: int | None = None, student_id: int | None = None,
                db: Session = Depends(get_db), _u=Depends(read)):
    query = db.query(models.Grade).order_by(models.Grade.id)
    if assignment_id is not None:
        query = query.filter(models.Grade.assignment_id == assignment_id)
    if student_id is not None:
        query = query.filter(models.Grade.student_id == student_id)
    return query.all()


@router.get("/report-cards/{student_id}", response_model=schemas.ReportCard)
def report_card(student_id: int, db: Session = Depends(get_db),
                user: models.User = Depends(get_current_user)):
    if user.role in ("student", "parent"):
        own = db.query(models.Student).filter(models.Student.user_id == user.id).first()
        if own is None or own.id != student_id:
            raise HTTPException(status_code=403, detail="Can only view own report card")
    elif user.role not in ("admin", "staff", "teacher"):
        raise HTTPException(status_code=403, detail="Forbidden")
    if db.get(models.Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Student not found")
    grades = db.query(models.Grade).filter(models.Grade.student_id == student_id).all()
    pcts: list[float] = []
    for grade in grades:
        assignment = db.get(models.Assignment, grade.assignment_id)
        if assignment and assignment.max_score:
            pcts.append(grade.score / assignment.max_score * 100)
    average = round(sum(pcts) / len(pcts), 2) if pcts else 0.0
    return schemas.ReportCard(
        student_id=student_id, average_pct=average, letter=_letter(average),
        grades=[schemas.GradeOut.model_validate(g) for g in grades],
    )
