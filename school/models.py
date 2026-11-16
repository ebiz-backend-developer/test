"""Domain models with validation. Pure data + rules, no I/O."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


class ValidationError(ValueError):
    pass


def _non_empty(name, value):
    if not value or not str(value).strip():
        raise ValidationError(f"{name} must not be empty")
    return str(value).strip()


def _email(value):
    value = _non_empty("email", value)
    if "@" not in value or "." not in value.split("@")[-1]:
        raise ValidationError("email must be a valid address")
    return value.lower()


@dataclass
class Student:
    id: str
    first_name: str
    last_name: str
    email: str
    grade_level: int
    date_of_birth: str = ""
    guardian_name: str = ""
    enrolled_on: str = field(default_factory=lambda: date.today().isoformat())
    active: bool = True

    def __post_init__(self):
        self.first_name = _non_empty("first_name", self.first_name)
        self.last_name = _non_empty("last_name", self.last_name)
        self.email = _email(self.email)
        if not 1 <= int(self.grade_level) <= 12:
            raise ValidationError("grade_level must be 1..12")
        self.grade_level = int(self.grade_level)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


@dataclass
class Teacher:
    id: str
    first_name: str
    last_name: str
    email: str
    subject: str
    hire_date: str = field(default_factory=lambda: date.today().isoformat())
    active: bool = True

    def __post_init__(self):
        self.first_name = _non_empty("first_name", self.first_name)
        self.last_name = _non_empty("last_name", self.last_name)
        self.email = _email(self.email)
        self.subject = _non_empty("subject", self.subject)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


@dataclass
class SchoolClass:
    id: str
    name: str
    grade_level: int
    teacher_id: str
    room: str = ""
    capacity: int = 30

    def __post_init__(self):
        self.name = _non_empty("name", self.name)
        if not 1 <= int(self.grade_level) <= 12:
            raise ValidationError("grade_level must be 1..12")
        self.grade_level = int(self.grade_level)
        self.teacher_id = _non_empty("teacher_id", self.teacher_id)
        if int(self.capacity) < 1:
            raise ValidationError("capacity must be >= 1")
        self.capacity = int(self.capacity)


@dataclass
class Enrollment:
    id: str
    student_id: str
    class_id: str
    enrolled_on: str = field(default_factory=lambda: date.today().isoformat())

    def __post_init__(self):
        self.student_id = _non_empty("student_id", self.student_id)
        self.class_id = _non_empty("class_id", self.class_id)


@dataclass
class AttendanceRecord:
    id: str
    student_id: str
    class_id: str
    day: str  # ISO date
    status: str  # present | absent | late | excused

    STATUSES = ("present", "absent", "late", "excused")

    def __post_init__(self):
        self.student_id = _non_empty("student_id", self.student_id)
        self.class_id = _non_empty("class_id", self.class_id)
        date.fromisoformat(self.day)  # raises if bad format
        if self.status not in self.STATUSES:
            raise ValidationError(f"status must be one of {self.STATUSES}")


@dataclass
class Grade:
    id: str
    student_id: str
    class_id: str
    assignment: str
    score: float
    max_score: float = 100.0

    def __post_init__(self):
        self.student_id = _non_empty("student_id", self.student_id)
        self.class_id = _non_empty("class_id", self.class_id)
        self.assignment = _non_empty("assignment", self.assignment)
        self.score = float(self.score)
        self.max_score = float(self.max_score)
        if self.max_score <= 0:
            raise ValidationError("max_score must be > 0")
        if not 0 <= self.score <= self.max_score:
            raise ValidationError("score must be within 0..max_score")

    @property
    def percent(self):
        return round(self.score / self.max_score * 100, 2)


@dataclass
class FeeInvoice:
    id: str
    student_id: str
    title: str
    amount: float
    due_date: str
    paid: float = 0.0
    issued_on: str = field(default_factory=lambda: date.today().isoformat())

    def __post_init__(self):
        self.student_id = _non_empty("student_id", self.student_id)
        self.title = _non_empty("title", self.title)
        self.amount = float(self.amount)
        if self.amount <= 0:
            raise ValidationError("amount must be > 0")
        date.fromisoformat(self.due_date)
        self.paid = float(self.paid)
        if not 0 <= self.paid <= self.amount:
            raise ValidationError("paid must be within 0..amount")

    @property
    def balance(self):
        return round(self.amount - self.paid, 2)

    @property
    def status(self):
        if self.paid >= self.amount:
            return "paid"
        if self.paid > 0:
            return "partial"
        return "unpaid"
