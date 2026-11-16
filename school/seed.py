"""Demo seed data: one account per role plus sample records."""
from __future__ import annotations

from datetime import date, timedelta

from .auth import AuthService
from .service import SchoolService

SEED_USERS = [
    ("admin", "admin123", "admin"),
    ("teacher", "teacher123", "teacher"),
    ("student", "student123", "student"),
    ("parent", "parent123", "parent"),
    ("staff", "staff123", "staff"),
]


def seed(auth: AuthService, service: SchoolService):
    store = auth.store
    if store.list("users"):
        return False  # already seeded
    users = {}
    for username, password, role in SEED_USERS:
        users[role] = auth.create_user(username, password, role)
    admin = store.get("users", users["admin"]["id"])

    t1 = service.create_teacher(admin, first_name="Ada", last_name="Lovelace",
                                email="ada@school.edu", subject="Mathematics")
    t2 = service.create_teacher(admin, first_name="Grace", last_name="Hopper",
                                email="grace@school.edu", subject="Physics")
    store.put("users", users["teacher"]["id"],
              {**store.get("users", users["teacher"]["id"]), "link_id": t1["id"]})

    s1 = service.create_student(admin, first_name="Alan", last_name="Turing",
                                email="alan@student.edu", grade_level=10,
                                guardian_name="Ethel Turing")
    s2 = service.create_student(admin, first_name="Katherine", last_name="Johnson",
                                email="katherine@student.edu", grade_level=10,
                                guardian_name="Joylette Johnson")
    for role in ("student", "parent"):
        store.put("users", users[role]["id"],
                  {**store.get("users", users[role]["id"]), "link_id": s1["id"]})

    c1 = service.create_class(admin, name="Algebra II", grade_level=10,
                              teacher_id=t1["id"], room="A101", capacity=30)
    c2 = service.create_class(admin, name="Physics I", grade_level=10,
                              teacher_id=t2["id"], room="B205", capacity=25)
    service.enroll(admin, s1["id"], c1["id"])
    service.enroll(admin, s2["id"], c1["id"])
    service.enroll(admin, s1["id"], c2["id"])

    today = date.today()
    for i, day in enumerate([today - timedelta(days=d) for d in (2, 1, 0)]):
        service.mark_attendance(admin, s1["id"], c1["id"], day.isoformat(),
                                "present" if i < 2 else "late")
        service.mark_attendance(admin, s2["id"], c1["id"], day.isoformat(),
                                "present")
    service.record_grade(admin, s1["id"], c1["id"], "Quiz 1", 85)
    service.record_grade(admin, s1["id"], c1["id"], "Midterm", 92)
    service.record_grade(admin, s2["id"], c1["id"], "Quiz 1", 95)
    inv = service.issue_invoice(admin, s1["id"], "Term 1 tuition", 1200.00,
                                (today + timedelta(days=30)).isoformat())
    service.pay_invoice(admin, inv["id"], 400.00)
    return True
