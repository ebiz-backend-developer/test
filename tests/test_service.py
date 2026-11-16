from tests import SchoolTestCase
from school.models import ValidationError
from school.store import ConflictError, NotFoundError


class StudentLifecycleTests(SchoolTestCase):
    def test_crud_and_duplicate_email(self):
        s = self.make_student()
        self.assertEqual(self.svc.get_student(self.admin, s["id"])["email"],
                         s["email"])
        updated = self.svc.update_student(self.admin, s["id"], grade_level=10)
        self.assertEqual(updated["grade_level"], 10)
        with self.assertRaises(ConflictError):
            self.make_student(tag="b", email=s["email"])
        self.svc.delete_student(self.admin, s["id"])
        with self.assertRaises(NotFoundError):
            self.svc.get_student(self.admin, s["id"])

    def test_delete_student_cascades_records(self):
        s = self.make_student()
        self.svc.enroll(self.admin, s["id"], self.class_rec["id"])
        self.svc.mark_attendance(self.admin, s["id"], self.class_rec["id"],
                                 "2026-03-01", "present")
        self.svc.record_grade(self.admin, s["id"], self.class_rec["id"],
                              "Q1", 80)
        self.svc.issue_invoice(self.admin, s["id"], "Tuition", 500,
                               "2026-12-01")
        self.svc.delete_student(self.admin, s["id"])
        for coll in ("enrollments", "attendance", "grades", "fees"):
            self.assertEqual(self.store.list(coll, student_id=s["id"]), [])


class EnrollmentTests(SchoolTestCase):
    def test_enroll_duplicate_capacity_and_roster(self):
        s1, s2 = self.make_student(tag="a"), self.make_student(tag="b")
        s3 = self.make_student(tag="c")
        cid = self.class_rec["id"]  # capacity 2
        self.svc.enroll(self.admin, s1["id"], cid)
        with self.assertRaises(ConflictError):
            self.svc.enroll(self.admin, s1["id"], cid)
        self.svc.enroll(self.admin, s2["id"], cid)
        with self.assertRaises(ConflictError):
            self.svc.enroll(self.admin, s3["id"], cid)
        roster = self.svc.class_roster(self.admin, cid)
        self.assertEqual({r["id"] for r in roster}, {s1["id"], s2["id"]})
        with self.assertRaises(NotFoundError):
            self.svc.enroll(self.admin, "stu-missing", cid)

    def test_cannot_enroll_inactive_student(self):
        s = self.make_student()
        self.svc.update_student(self.admin, s["id"], active=False)
        with self.assertRaises(ValidationError):
            self.svc.enroll(self.admin, s["id"], self.class_rec["id"])

    def test_teacher_delete_blocked_while_assigned(self):
        with self.assertRaises(ConflictError):
            self.svc.delete_teacher(self.admin, self.teacher_rec["id"])


class AttendanceTests(SchoolTestCase):
    def test_mark_update_and_report(self):
        s = self.make_student()
        cid = self.class_rec["id"]
        self.svc.enroll(self.admin, s["id"], cid)
        self.svc.mark_attendance(self.admin, s["id"], cid,
                                 "2026-03-01", "absent")
        # same day re-mark overwrites
        self.svc.mark_attendance(self.admin, s["id"], cid,
                                 "2026-03-01", "present")
        self.svc.mark_attendance(self.admin, s["id"], cid,
                                 "2026-03-02", "late")
        rep = self.svc.attendance_report(self.admin, class_id=cid)
        self.assertEqual(len(rep["records"]), 2)
        slot = rep["summary"][s["id"]]
        self.assertEqual(slot["present"], 1)
        self.assertEqual(slot["late"], 1)
        self.assertEqual(slot["attendance_rate"], 100.0)

    def test_unenrolled_student_rejected(self):
        s = self.make_student()
        with self.assertRaises(ValidationError):
            self.svc.mark_attendance(self.admin, s["id"],
                                     self.class_rec["id"],
                                     "2026-03-01", "present")

    def test_date_range_filter(self):
        s = self.make_student()
        cid = self.class_rec["id"]
        self.svc.enroll(self.admin, s["id"], cid)
        for day in ("2026-03-01", "2026-03-02", "2026-03-03"):
            self.svc.mark_attendance(self.admin, s["id"], cid, day, "present")
        rep = self.svc.attendance_report(self.admin, class_id=cid,
                                         start="2026-03-02", end="2026-03-02")
        self.assertEqual(len(rep["records"]), 1)


class GradeTests(SchoolTestCase):
    def test_record_gpa_and_averages(self):
        s1, s2 = self.make_student(tag="a"), self.make_student(tag="b")
        cid = self.class_rec["id"]
        for s in (s1, s2):
            self.svc.enroll(self.admin, s["id"], cid)
        self.svc.record_grade(self.admin, s1["id"], cid, "Q1", 80)
        self.svc.record_grade(self.admin, s1["id"], cid, "Q2", 100)
        self.svc.record_grade(self.admin, s2["id"], cid, "Q1", 70)
        gpa = self.svc.gpa(self.admin, s1["id"])
        self.assertEqual(gpa["average_percent"], 90.0)
        self.assertEqual(gpa["gpa"], 4.0)
        avgs = self.svc.class_averages(self.admin, cid)
        self.assertEqual(avgs, {"Q1": 75.0, "Q2": 100.0})

    def test_gpa_empty_is_none(self):
        s = self.make_student()
        gpa = self.svc.gpa(self.admin, s["id"])
        self.assertIsNone(gpa["gpa"])
        self.assertEqual(gpa["assignments"], 0)

    def test_grade_requires_enrollment(self):
        s = self.make_student()
        with self.assertRaises(ValidationError):
            self.svc.record_grade(self.admin, s["id"], self.class_rec["id"],
                                  "Q1", 50)


class FeeTests(SchoolTestCase):
    def test_invoice_pay_flow_and_overpay_rejected(self):
        s = self.make_student()
        inv = self.svc.issue_invoice(self.admin, s["id"], "Tuition",
                                     1000, "2026-12-01")
        part = self.svc.pay_invoice(self.admin, inv["id"], 300)
        self.assertEqual((part["status"], part["balance"]),
                         ("partial", 700.0))
        with self.assertRaises(ValidationError):
            self.svc.pay_invoice(self.admin, inv["id"], 701)
        full = self.svc.pay_invoice(self.admin, inv["id"], 700)
        self.assertEqual(full["status"], "paid")
        fees = self.svc.student_fees(self.admin, s["id"])
        self.assertEqual(fees["total_due"], 0)

    def test_revenue_summary(self):
        s = self.make_student()
        self.svc.issue_invoice(self.admin, s["id"], "A", 500, "2020-01-01")
        inv2 = self.svc.issue_invoice(self.admin, s["id"], "B", 500,
                                      "2026-12-01")
        self.svc.pay_invoice(self.admin, inv2["id"], 200)
        rep = self.svc.revenue_summary(self.admin)
        self.assertEqual(rep["collected"], 200)
        self.assertEqual(rep["outstanding"], 800)
        self.assertEqual(rep["overdue"], 500)
