"""Admissions + attendance behavior through the roleified API."""
from tests.helpers import DbTestCase


class AdmissionsTest(DbTestCase):
    def test_parent_applies_officer_admits(self):
        s, app = self.call("POST", "/api/applications", role="parent", body={
            "student_name": "Emeka Nwosu", "guardian_name": "Mrs Nwosu",
            "grade_applying": "JSS1"})
        self.assertEqual(s, 201)
        self.assertEqual(app["status"], "submitted")

        s, listed = self.call("GET", "/api/applications",
                              role="admissions_officer")
        self.assertEqual(s, 200)
        self.assertEqual(len(listed), 1)

        s, decided = self.call(
            "POST", f"/api/applications/{app['id']}/decide",
            role="admissions_officer",
            body={"decision": "admitted", "notes": "passed interview"})
        self.assertEqual(s, 200)
        self.assertEqual(decided["status"], "admitted")

    def test_student_cannot_decide(self):
        s, app = self.call("POST", "/api/applications", role="parent", body={
            "student_name": "A", "grade_applying": "JSS1"})
        s, err = self.call("POST", f"/api/applications/{app['id']}/decide",
                           role="student", body={"decision": "admitted"})
        self.assertEqual(s, 403)

    def test_double_decision_rejected(self):
        _, app = self.call("POST", "/api/applications", role="parent", body={
            "student_name": "B", "grade_applying": "JSS1"})
        self.call("POST", f"/api/applications/{app['id']}/decide",
                  role="admissions_officer", body={"decision": "rejected"})
        s, err = self.call("POST", f"/api/applications/{app['id']}/decide",
                           role="admissions_officer",
                           body={"decision": "admitted"})
        self.assertEqual(s, 400)

    def test_validation(self):
        s, _ = self.call("POST", "/api/applications", role="parent",
                         body={"student_name": "", "grade_applying": "JSS1"})
        self.assertEqual(s, 400)
        s, _ = self.call("GET", "/api/applications/999", role="admin")
        self.assertEqual(s, 404)


class AttendanceTest(DbTestCase):
    def test_mark_and_summarize(self):
        _, stu = self.call("POST", "/api/students", role="teacher", body={
            "full_name": "Amina Diallo", "class_name": "JSS1"})
        self.assertEqual(stu["created"], True)
        for day, status in (("2026-11-09", "present"),
                            ("2026-11-10", "late"),
                            ("2026-11-11", "absent")):
            s, rec = self.call("POST", "/api/attendance", role="teacher", body={
                "student_id": stu["id"], "class_date": day, "status": status})
            self.assertEqual(s, 201)
        s, summ = self.call("GET", f"/api/attendance?student_id={stu['id']}",
                            role="teacher")
        self.assertEqual(s, 200)
        self.assertEqual(summ["counts"],
                         {"present": 1, "absent": 1, "late": 1, "excused": 0})
        self.assertAlmostEqual(summ["attendance_rate"], 2 / 3, places=2)

    def test_remark_same_day_updates(self):
        _, stu = self.call("POST", "/api/students", role="teacher", body={
            "full_name": "C", "class_name": "JSS1"})
        self.call("POST", "/api/attendance", role="teacher", body={
            "student_id": stu["id"], "class_date": "2026-11-09",
            "status": "absent"})
        s, rec = self.call("POST", "/api/attendance", role="teacher", body={
            "student_id": stu["id"], "class_date": "2026-11-09",
            "status": "present"})
        self.assertEqual(rec["status"], "present")

    def test_day_roster(self):
        _, stu = self.call("POST", "/api/students", role="teacher", body={
            "full_name": "D", "class_name": "JSS2"})
        s, roster = self.call("GET", "/api/attendance?class_date=2026-11-09",
                              role="teacher")
        self.assertEqual(s, 200)
        self.assertEqual(roster[0]["status"], None)

    def test_student_cannot_mark(self):
        s, _ = self.call("POST", "/api/attendance", role="student",
                         body={"student_id": 1, "class_date": "2026-11-09",
                               "status": "present"})
        self.assertEqual(s, 403)

    def test_unknown_student_404(self):
        s, _ = self.call("POST", "/api/attendance", role="teacher",
                         body={"student_id": 999, "class_date": "2026-11-09",
                               "status": "present"})
        self.assertEqual(s, 404)
