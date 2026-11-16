"""SQLAlchemy ORM models for the MVP modules (c2).

Modules: users, students, teachers, classes, enrollments, attendance, grades.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .plan import ROLES

VALID_ROLES = tuple(ROLES.keys())


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="student")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    student_profile: Mapped["Student | None"] = relationship(back_populates="user", cascade="all, delete-orphan",
                                                             single_parent=True)
    teacher_profile: Mapped["Teacher | None"] = relationship(back_populates="user", cascade="all, delete-orphan",
                                                             single_parent=True)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admission_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(64), nullable=False)
    last_name: Mapped[str] = mapped_column(String(64), nullable=False)
    date_of_birth: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str] = mapped_column(String(16), nullable=False, default="other")
    guardian_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    guardian_phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True)

    user: Mapped["User | None"] = relationship(back_populates="student_profile")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student", cascade="all, delete-orphan")


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    staff_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(64), nullable=False)
    last_name: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True)

    user: Mapped["User | None"] = relationship(back_populates="teacher_profile")
    classes: Mapped[list["SchoolClass"]] = relationship(back_populates="teacher")


class SchoolClass(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    grade_level: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    term: Mapped[str] = mapped_column(String(32), nullable=False, default="Term 1")
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)

    teacher: Mapped["Teacher | None"] = relationship(back_populates="classes")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="school_class", cascade="all, delete-orphan")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("student_id", "class_id", name="uq_enrollment_student_class"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    enrolled_on: Mapped[dt.date] = mapped_column(Date, nullable=False, default=dt.date.today)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")

    student: Mapped["Student"] = relationship(back_populates="enrollments")
    school_class: Mapped["SchoolClass"] = relationship(back_populates="enrollments")


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("student_id", "class_id", "day", name="uq_attendance_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    day: Mapped[dt.date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # present|absent|late|excused
    note: Mapped[str] = mapped_column(String(256), nullable=False, default="")


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    due_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    grades: Mapped[list["Grade"]] = relationship(back_populates="assignment", cascade="all, delete-orphan")


class Grade(Base):
    __tablename__ = "grades"
    __table_args__ = (UniqueConstraint("assignment_id", "student_id", name="uq_grade_assignment_student"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False,
                                               index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")

    assignment: Mapped["Assignment"] = relationship(back_populates="grades")
