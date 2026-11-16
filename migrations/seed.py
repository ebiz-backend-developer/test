"""Demo seed data: admin user, teachers, classes, students, enrollments.

Usage: ``python -m migrations.seed`` (idempotent — safe to re-run).
"""

from __future__ import annotations

import datetime as dt

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin1234"
ADMIN_EMAIL = "admin@schoolms.local"


def seed() -> dict:
    from schoolms import models
    from schoolms.database import SessionLocal, engine
    from schoolms.security import hash_password
    from migrations.run import run as run_migrations

    run_migrations()
    db = SessionLocal()
    try:
        if db.query(models.User).filter(models.User.username == ADMIN_USERNAME).first() is None:
            db.add(models.User(
                username=ADMIN_USERNAME, full_name="System Administrator",
                email=ADMIN_EMAIL, password_hash=hash_password(ADMIN_PASSWORD),
                role="admin",
            ))
        # Staff + teacher + student demo accounts
        for username, full_name, email, role, password in [
            ("office", "Front Office", "office@schoolms.local", "staff", "Office1234"),
            ("t.alice", "Alice Teacher", "alice@schoolms.local", "teacher", "Teacher1234"),
            ("s.bob", "Bob Student", "bob@schoolms.local", "student", "Student1234"),
        ]:
            if db.query(models.User).filter(models.User.username == username).first() is None:
                db.add(models.User(
                    username=username, full_name=full_name, email=email,
                    password_hash=hash_password(password), role=role,
                ))
        db.commit()

        teacher_user = db.query(models.User).filter(models.User.username == "t.alice").first()
        student_user = db.query(models.User).filter(models.User.username == "s.bob").first()

        if db.query(models.Teacher).filter(models.Teacher.staff_no == "T-001").first() is None:
            db.add(models.Teacher(staff_no="T-001", first_name="Alice", last_name="Mensah",
                                  subject="Mathematics", phone="0240000001",
                                  user_id=teacher_user.id if teacher_user else None))
        if db.query(models.Student).filter(models.Student.admission_no == "S-001").first() is None:
            db.add(models.Student(admission_no="S-001", first_name="Bob", last_name="Owusu",
                                  date_of_birth=dt.date(2012, 3, 15), gender="male",
                                  guardian_name="Ama Owusu", guardian_phone="0240000002",
                                  user_id=student_user.id if student_user else None))
        db.commit()

        teacher = db.query(models.Teacher).filter(models.Teacher.staff_no == "T-001").first()
        if db.query(models.SchoolClass).filter(models.SchoolClass.code == "JHS1-A").first() is None:
            db.add(models.SchoolClass(code="JHS1-A", name="JHS 1 - A", grade_level="JHS 1",
                                      term="Term 1", capacity=40,
                                      teacher_id=teacher.id if teacher else None))
        db.commit()

        student = db.query(models.Student).filter(models.Student.admission_no == "S-001").first()
        cls = db.query(models.SchoolClass).filter(models.SchoolClass.code == "JHS1-A").first()
        if student and cls and db.query(models.Enrollment).filter(
                models.Enrollment.student_id == student.id,
                models.Enrollment.class_id == cls.id).first() is None:
            db.add(models.Enrollment(student_id=student.id, class_id=cls.id))
        db.commit()
        return {"seeded": True, "admin": ADMIN_USERNAME}
    finally:
        db.close()


if __name__ == "__main__":
    print(seed())
