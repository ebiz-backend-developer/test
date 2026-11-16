"""Business logic for the MVP core modules (c2).

Modules: students, teachers, classes, enrollments, attendance, grades, fees.
Every mutating operation enforces RBAC via AuthService.require.
"""
from __future__ import annotations

import secrets
from datetime import date

from .auth import AuthService
from .models import (
    AttendanceRecord, Enrollment, FeeInvoice, Grade, SchoolClass, Student,
    Teacher, ValidationError,
)
from .store import ConflictError, NotFoundError, Store


def _new_id(prefix):
    return f"{prefix}-{secrets.token_hex(4)}"


class SchoolService:
    def __init__(self, store: Store, auth: AuthService):
        self.store = store
        self.auth = auth

    # -- students ------------------------------------------------------
    def create_student(self, user, **fields):
        self.auth.require(user, "students", "write")
        student = Student(id=_new_id("stu"), **fields)
        if self.store.list("students", email=student.email):
            raise ConflictError("student email already exists")
        return self.store.put("students", student.id, student)

    def get_student(self, user, student_id):
        self.auth.require(user, "students", "read")
        self._check_student_scope(user, student_id)
        return self.store.get("students", student_id)

    def list_students(self, user, **filters):
        self.auth.require(user, "students", "read")
        rows = self.store.list("students", **filters)
        return [r for r in rows if self._in_student_scope(user, r["id"])]

    def update_student(self, user, student_id, **fields):
        self.auth.require(user, "students", "write")
        current = self.store.get("students", student_id)
        merged = {**current, **fields, "id": student_id}
        student = Student(**merged)
        for row in self.store.list("students", email=student.email):
            if row["id"] != student_id:
                raise ConflictError("student email already exists")
        return self.store.put("students", student_id, student)

    def delete_student(self, user, student_id):
        self.auth.require(user, "students", "write")
        for coll in ("enrollments", "attendance", "grades", "fees"):
            for row in self.store.list(coll, student_id=student_id):
                self.store.delete(coll, row["id"])
        self.store.delete("students", student_id)

    # -- teachers ------------------------------------------------------
    def create_teacher(self, user, **fields):
        self.auth.require(user, "teachers", "write")
        teacher = Teacher(id=_new_id("tch"), **fields)
        if self.store.list("teachers", email=teacher.email):
            raise ConflictError("teacher email already exists")
        return self.store.put("teachers", teacher.id, teacher)

    def list_teachers(self, user):
        self.auth.require(user, "teachers", "read")
        return self.store.list("teachers")

    def get_teacher(self, user, teacher_id):
        self.auth.require(user, "teachers", "read")
        return self.store.get("teachers", teacher_id)

    def delete_teacher(self, user, teacher_id):
        self.auth.require(user, "teachers", "write")
        if self.store.list("classes", teacher_id=teacher_id):
            raise ConflictError("teacher still assigned to classes")
        self.store.delete("teachers", teacher_id)

    # -- classes ---------------------------------------------------------
    def create_class(self, user, **fields):
        self.auth.require(user, "classes", "write")
        cls = SchoolClass(id=_new_id("cls"), **fields)
        self.store.get("teachers", cls.teacher_id)  # teacher must exist
        return self.store.put("classes", cls.id, cls)

    def list_classes(self, user):
        self.auth.require(user, "classes", "read")
        return self.store.list("classes")

    def get_class(self, user, class_id):
        self.auth.require(user, "classes", "read")
        return self.store.get("classes", class_id)

    def delete_class(self, user, class_id):
        self.auth.require(user, "classes", "write")
        for coll in ("enrollments", "attendance", "grades"):
            for row in self.store.list(coll, class_id=class_id):
                self.store.delete(coll, row["id"])
        self.store.delete("classes", class_id)

    # -- enrollments -----------------------------------------------------
    def enroll(self, user, student_id, class_id):
        self.auth.require(user, "enrollments", "write")
        student = self.store.get("students", student_id)
        cls = self.store.get("classes", class_id)
        if not student.get("active", True):
            raise ValidationError("cannot enroll an inactive student")
        if self.store.list("enrollments", student_id=student_id, class_id=class_id):
            raise ConflictError("student already enrolled in this class")
        current = len(self.store.list("enrollments", class_id=class_id))
        if current >= cls["capacity"]:
            raise ConflictError("class is at capacity")
        enr = Enrollment(id=_new_id("enr"), student_id=student_id, class_id=class_id)
        return self.store.put("enrollments", enr.id, enr)

    def unenroll(self, user, enrollment_id):
        self.auth.require(user, "enrollments", "write")
        self.store.delete("enrollments", enrollment_id)

    def list_enrollments(self, user, **filters):
        self.auth.require(user, "enrollments", "read")
        rows = self.store.list("enrollments", **filters)
        return [r for r in rows if self._in_student_scope(user, r["student_id"])]

    def class_roster(self, user, class_id):
        self.auth.require(user, "enrollments", "read")
        self.store.get("classes", class_id)
        out = []
        for enr in self.store.list("enrollments", class_id=class_id):
            try:
                out.append(self.store.get("students", enr["student_id"]))
            except NotFoundError:
                continue
        return out

    # -- attendance ------------------------------------------------------
    def mark_attendance(self, user, student_id, class_id, day, status):
        self.auth.require(user, "attendance", "write")
        self._check_teacher_class_scope(user, class_id)
        if not self.store.list("enrollments", student_id=student_id, class_id=class_id):
            raise ValidationError("student is not enrolled in this class")
        existing = self.store.list(
            "attendance", student_id=student_id, class_id=class_id, day=day)
        rec = AttendanceRecord(
            id=existing[0]["id"] if existing else _new_id("att"),
            student_id=student_id, class_id=class_id, day=day, status=status)
        return self.store.put("attendance", rec.id, rec)

    def attendance_report(self, user, class_id=None, student_id=None,
                          start=None, end=None):
        self.auth.require(user, "attendance", "read")
        filters = {}
        if class_id:
            filters["class_id"] = class_id
        if student_id:
            self._check_student_scope(user, student_id)
            filters["student_id"] = student_id
        rows = self.store.list("attendance", **filters)
        rows = [r for r in rows if self._in_student_scope(user, r["student_id"])]
        if start:
            rows = [r for r in rows if r["day"] >= start]
        if end:
            rows = [r for r in rows if r["day"] <= end]
        summary = {}
        for r in rows:
            key = r["student_id"]
            slot = summary.setdefault(key, {"present": 0, "absent": 0,
                                            "late": 0, "excused": 0, "total": 0})
            slot[r["status"]] += 1
            slot["total"] += 1
        for slot in summary.values():
            denom = slot["total"] or 1
            slot["attendance_rate"] = round(
                (slot["present"] + slot["late"] + slot["excused"]) / denom * 100, 2)
        return {"records": sorted(rows, key=lambda r: r["day"]), "summary": summary}

    # -- grades ----------------------------------------------------------
    def record_grade(self, user, student_id, class_id, assignment,
                     score, max_score=100.0):
        self.auth.require(user, "grades", "write")
        self._check_teacher_class_scope(user, class_id)
        if not self.store.list("enrollments", student_id=student_id, class_id=class_id):
            raise ValidationError("student is not enrolled in this class")
        grade = Grade(id=_new_id("grd"), student_id=student_id,
                      class_id=class_id, assignment=assignment,
                      score=score, max_score=max_score)
        return self.store.put("grades", grade.id, grade)

    def student_grades(self, user, student_id):
        self.auth.require(user, "grades", "read")
        self._check_student_scope(user, student_id)
        self.store.get("students", student_id)
        return self.store.list("grades", student_id=student_id)

    def gpa(self, user, student_id):
        grades = self.student_grades(user, student_id)
        if not grades:
            return {"student_id": student_id, "gpa": None, "average_percent": None,
                    "assignments": 0}
        avg = sum(g["score"] / g["max_score"] for g in grades) / len(grades) * 100
        avg = round(avg, 2)
        if avg >= 90:
            points = 4.0
        elif avg >= 80:
            points = 3.0
        elif avg >= 70:
            points = 2.0
        elif avg >= 60:
            points = 1.0
        else:
            points = 0.0
        return {"student_id": student_id, "gpa": points,
                "average_percent": avg, "assignments": len(grades)}

    def class_averages(self, user, class_id):
        self.auth.require(user, "grades", "read")
        self.store.get("classes", class_id)
        rows = self.store.list("grades", class_id=class_id)
        by_assignment = {}
        for g in rows:
            slot = by_assignment.setdefault(g["assignment"], [])
            slot.append(g["score"] / g["max_score"] * 100)
        return {a: round(sum(v) / len(v), 2) for a, v in sorted(by_assignment.items())}

    # -- fees ------------------------------------------------------------
    def issue_invoice(self, user, student_id, title, amount, due_date):
        self.auth.require(user, "fees", "write")
        self.store.get("students", student_id)
        inv = FeeInvoice(id=_new_id("fee"), student_id=student_id,
                         title=title, amount=amount, due_date=due_date)
        return self.store.put("fees", inv.id, inv)

    def pay_invoice(self, user, invoice_id, amount):
        self.auth.require(user, "fees", "write")
        current = self.store.get("fees", invoice_id)
        amount = float(amount)
        if amount <= 0:
            raise ValidationError("payment amount must be > 0")
        if current["paid"] + amount > current["amount"] + 1e-9:
            raise ValidationError("payment exceeds amount due")
        current["paid"] = round(current["paid"] + amount, 2)
        inv = FeeInvoice(**current)
        saved = self.store.put("fees", invoice_id, inv)
        saved["balance"] = inv.balance
        saved["status"] = inv.status
        return saved

    def student_fees(self, user, student_id):
        self.auth.require(user, "fees", "read")
        self._check_student_scope(user, student_id)
        rows = self.store.list("fees", student_id=student_id)
        for row in rows:
            inv = FeeInvoice(**row)
            row["balance"] = inv.balance
            row["status"] = inv.status
        total_due = round(sum(r["balance"] for r in rows), 2)
        return {"invoices": rows, "total_due": total_due}

    def revenue_summary(self, user):
        self.auth.require(user, "reports", "read")
        rows = self.store.list("fees")
        collected = round(sum(r["paid"] for r in rows), 2)
        outstanding = round(sum(r["amount"] - r["paid"] for r in rows), 2)
        today = date.today().isoformat()
        overdue = round(sum(r["amount"] - r["paid"] for r in rows
                            if r["due_date"] < today and r["paid"] < r["amount"]), 2)
        return {"invoices": len(rows), "collected": collected,
                "outstanding": outstanding, "overdue": overdue}

    # -- ownership scoping -----------------------------------------------
    def _in_student_scope(self, user, student_id):
        if user["role"] in ("admin", "teacher", "staff"):
            return True
        if user["role"] in ("student", "parent"):
            return user.get("link_id") == student_id
        return False

    def _check_student_scope(self, user, student_id):
        if not self._in_student_scope(user, student_id):
            from .auth import AuthError
            raise AuthError("not permitted to access another student's data")

    def _check_teacher_class_scope(self, user, class_id):
        if user["role"] == "teacher":
            try:
                cls = self.store.get("classes", class_id)
            except NotFoundError:
                return  # let the caller raise the canonical error
            if cls.get("teacher_id") != user.get("link_id"):
                from .auth import AuthError
                raise AuthError("teachers may only modify their own classes")
