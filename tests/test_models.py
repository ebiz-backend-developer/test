import unittest

from school.models import (AttendanceRecord, FeeInvoice, Grade, SchoolClass,
                           Student, Teacher, ValidationError)


class ModelValidationTests(unittest.TestCase):
    def test_student_rejects_bad_email_and_grade(self):
        with self.assertRaises(ValidationError):
            Student(id="x", first_name="A", last_name="B",
                    email="not-an-email", grade_level=5)
        with self.assertRaises(ValidationError):
            Student(id="x", first_name="A", last_name="B",
                    email="a@b.co", grade_level=13)

    def test_student_full_name(self):
        s = Student(id="x", first_name="A", last_name="B",
                    email="a@b.co", grade_level=5)
        self.assertEqual(s.full_name, "A B")

    def test_teacher_requires_subject(self):
        with self.assertRaises(ValidationError):
            Teacher(id="x", first_name="A", last_name="B",
                    email="a@b.co", subject=" ")

    def test_class_rejects_zero_capacity(self):
        with self.assertRaises(ValidationError):
            SchoolClass(id="x", name="C", grade_level=1,
                        teacher_id="t", capacity=0)

    def test_attendance_rejects_bad_status_and_day(self):
        with self.assertRaises(ValidationError):
            AttendanceRecord(id="x", student_id="s", class_id="c",
                             day="2026-01-01", status="sleeping")
        with self.assertRaises(ValueError):
            AttendanceRecord(id="x", student_id="s", class_id="c",
                             day="01/01/2026", status="present")

    def test_grade_bounds_and_percent(self):
        with self.assertRaises(ValidationError):
            Grade(id="x", student_id="s", class_id="c",
                  assignment="Q", score=120)
        g = Grade(id="x", student_id="s", class_id="c",
                  assignment="Q", score=45, max_score=50)
        self.assertEqual(g.percent, 90.0)

    def test_invoice_status_lifecycle(self):
        inv = FeeInvoice(id="x", student_id="s", title="T",
                         amount=100, due_date="2026-12-01")
        self.assertEqual((inv.status, inv.balance), ("unpaid", 100))
        inv.paid = 40
        self.assertEqual(inv.status, "partial")
        inv.paid = 100
        self.assertEqual(inv.status, "paid")
        with self.assertRaises(ValidationError):
            FeeInvoice(id="x", student_id="s", title="T",
                       amount=-5, due_date="2026-12-01")


if __name__ == "__main__":
    unittest.main()
