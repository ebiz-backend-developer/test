from tests import SchoolTestCase
from school.auth import AuthError


class AuthTests(SchoolTestCase):
    def test_login_logout_and_bad_password(self):
        token, user = self.auth.login("admin", "admin-pw")
        self.assertEqual(user["role"], "admin")
        self.assertNotIn("password", user)
        self.assertEqual(self.auth.authenticate(token)["username"], "admin")
        with self.assertRaises(AuthError):
            self.auth.login("admin", "wrong")
        self.auth.logout(token)
        with self.assertRaises(AuthError):
            self.auth.authenticate(token)

    def test_duplicate_and_bad_role_rejected(self):
        with self.assertRaises(AuthError):
            self.auth.create_user("admin", "x", "admin")
        with self.assertRaises(AuthError):
            self.auth.create_user("new", "x", "superuser")


class RBACTests(SchoolTestCase):
    def setUp(self):
        super().setUp()
        self.mine = self.make_student(tag="m")
        self.other = self.make_student(tag="o")
        self.student_u = self.link_student_user("student", self.mine["id"])
        self.parent_u = self.link_student_user("parent", self.mine["id"])
        self.staff = self.store.get("users", self.users["staff"]["id"])
        cid = self.class_rec["id"]
        for s in (self.mine, self.other):
            self.svc.enroll(self.admin, s["id"], cid)

    def test_student_sees_only_own_record(self):
        got = self.svc.get_student(self.student_u, self.mine["id"])
        self.assertEqual(got["id"], self.mine["id"])
        with self.assertRaises(AuthError):
            self.svc.get_student(self.student_u, self.other["id"])
        rows = self.svc.list_students(self.student_u)
        self.assertEqual([r["id"] for r in rows], [self.mine["id"]])

    def test_student_cannot_write(self):
        with self.assertRaises(AuthError):
            self.svc.create_student(self.student_u, first_name="X",
                                    last_name="Y", email="x@y.co",
                                    grade_level=3)
        with self.assertRaises(AuthError):
            self.svc.record_grade(self.student_u, self.mine["id"],
                                  self.class_rec["id"], "Q", 100)

    def test_parent_scoped_to_linked_student(self):
        gpa = self.svc.gpa(self.parent_u, self.mine["id"])
        self.assertEqual(gpa["assignments"], 0)
        with self.assertRaises(AuthError):
            self.svc.gpa(self.parent_u, self.other["id"])

    def test_teacher_marks_own_class_only(self):
        cid = self.class_rec["id"]
        rec = self.svc.mark_attendance(self.teacher, self.mine["id"], cid,
                                       "2026-04-01", "present")
        self.assertEqual(rec["status"], "present")
        other_t = self.svc.create_teacher(self.admin, first_name="O",
                                          last_name="T", email="o@t.co",
                                          subject="Art")
        other_c = self.svc.create_class(self.admin, name="Art", grade_level=9,
                                        teacher_id=other_t["id"])
        self.svc.enroll(self.admin, self.mine["id"], other_c["id"])
        with self.assertRaises(AuthError):
            self.svc.mark_attendance(self.teacher, self.mine["id"],
                                     other_c["id"], "2026-04-01", "present")
        with self.assertRaises(AuthError):
            self.svc.create_teacher(self.teacher, first_name="N",
                                    last_name="T", email="n@t.co",
                                    subject="X")

    def test_staff_manages_fees_not_grades(self):
        inv = self.svc.issue_invoice(self.staff, self.mine["id"], "Books",
                                     50, "2026-12-01")
        paid = self.svc.pay_invoice(self.staff, inv["id"], 50)
        self.assertEqual(paid["status"], "paid")
        with self.assertRaises(AuthError):
            self.svc.record_grade(self.staff, self.mine["id"],
                                  self.class_rec["id"], "Q", 90)

    def test_admin_can_do_everything(self):
        self.svc.create_teacher(self.admin, first_name="A", last_name="B",
                                email="adm@t.co", subject="S")
        rep = self.svc.revenue_summary(self.admin)
        self.assertIn("collected", rep)
