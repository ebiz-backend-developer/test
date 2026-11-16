"""Pydantic request/response schemas for all MVP modules."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .plan import ROLES

model_config = ConfigDict(from_attributes=True)


# --- Users / auth -----------------------------------------------------------
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    full_name: str = Field(default="", max_length=128)
    email: str
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="student")

    def validated_role(self) -> str:
        if self.role not in ROLES:
            raise ValueError(f"Unknown role: {self.role}")
        return self.role


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    model_config = model_config
    id: int
    username: str
    full_name: str
    email: str
    role: str
    is_active: bool


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Students ---------------------------------------------------------------
class StudentCreate(BaseModel):
    admission_no: str = Field(min_length=1, max_length=32)
    first_name: str = Field(min_length=1, max_length=64)
    last_name: str = Field(min_length=1, max_length=64)
    date_of_birth: dt.date | None = None
    gender: str = "other"
    guardian_name: str = ""
    guardian_phone: str = ""
    user_id: int | None = None


class StudentUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: dt.date | None = None
    gender: str | None = None
    guardian_name: str | None = None
    guardian_phone: str | None = None
    status: str | None = None
    user_id: int | None = None


class StudentOut(BaseModel):
    model_config = model_config
    id: int
    admission_no: str
    first_name: str
    last_name: str
    date_of_birth: dt.date | None
    gender: str
    guardian_name: str
    guardian_phone: str
    status: str
    user_id: int | None


# --- Teachers ---------------------------------------------------------------
class TeacherCreate(BaseModel):
    staff_no: str = Field(min_length=1, max_length=32)
    first_name: str = Field(min_length=1, max_length=64)
    last_name: str = Field(min_length=1, max_length=64)
    subject: str = ""
    phone: str = ""
    user_id: int | None = None


class TeacherUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    subject: str | None = None
    phone: str | None = None
    status: str | None = None
    user_id: int | None = None


class TeacherOut(BaseModel):
    model_config = model_config
    id: int
    staff_no: str
    first_name: str
    last_name: str
    subject: str
    phone: str
    status: str
    user_id: int | None


# --- Classes ----------------------------------------------------------------
class ClassCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    grade_level: str = ""
    term: str = "Term 1"
    capacity: int = Field(default=30, ge=1, le=500)
    teacher_id: int | None = None


class ClassUpdate(BaseModel):
    name: str | None = None
    grade_level: str | None = None
    term: str | None = None
    capacity: int | None = Field(default=None, ge=1, le=500)
    teacher_id: int | None = None


class ClassOut(BaseModel):
    model_config = model_config
    id: int
    code: str
    name: str
    grade_level: str
    term: str
    capacity: int
    teacher_id: int | None
    enrolled: int = 0


# --- Enrollments ------------------------------------------------------------
class EnrollmentCreate(BaseModel):
    student_id: int
    class_id: int


class EnrollmentOut(BaseModel):
    model_config = model_config
    id: int
    student_id: int
    class_id: int
    enrolled_on: dt.date
    status: str


# --- Attendance -------------------------------------------------------------
class AttendanceMark(BaseModel):
    student_id: int
    class_id: int
    day: dt.date = Field(default_factory=dt.date.today)
    status: str = Field(pattern="^(present|absent|late|excused)$")
    note: str = ""


class AttendanceOut(BaseModel):
    model_config = model_config
    id: int
    student_id: int
    class_id: int
    day: dt.date
    status: str
    note: str


class AttendanceSummary(BaseModel):
    class_id: int
    day: dt.date | None = None
    total: int
    present: int
    absent: int
    late: int
    excused: int
    rate: float


# --- Grades -----------------------------------------------------------------
class AssignmentCreate(BaseModel):
    class_id: int
    title: str = Field(min_length=1, max_length=128)
    max_score: float = Field(default=100.0, gt=0)
    due_date: dt.date | None = None


class AssignmentOut(BaseModel):
    model_config = model_config
    id: int
    class_id: int
    title: str
    max_score: float
    due_date: dt.date | None


class GradeCreate(BaseModel):
    assignment_id: int
    student_id: int
    score: float = Field(ge=0)
    comment: str = ""


class GradeOut(BaseModel):
    model_config = model_config
    id: int
    assignment_id: int
    student_id: int
    score: float
    comment: str


class ReportCard(BaseModel):
    student_id: int
    average_pct: float
    grades: list[GradeOut]
    letter: str
