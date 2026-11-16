"""Grades + timetable behavior through the roleified API."""
from tests.helpers import DbTestCase


class GradesTest(DbTestCase):
    def test_assessment_scores_average(self):
        _, a1 = self.call("POST", "/api/assessments", role="teacher", body={
            "title": "Mid-term", "subject": "Maths", "max_score": 100})
        _, a2 = self.call("POST", "/api/assessments", role="teacher", body={
            "title": "Quiz", "subject": "Maths", "max_score": 20})
        self.call("POST", "/api/scores", role="teacher", body={
            "assessment_id": a1["id"], "student_name": "Amina", "score": 80})
        self.call("POST", "/api/scores", role="teacher", body={
            "assessment_id": a2["id"], "student_name": "Amina", "score": 15})
        s, avg = self.call("GET", "/api/scores?student_name=Amina",
                           role="parent")
        self.assertEqual(s, 200)
        self.assertEqual(avg["assessments"], 2)
        self.assertAlmostEqual(avg["average_pct"], 77.5)

    def test_score_above_max_rejected(self):
        _, a = self.call("POST", "/api/assessments", role="teacher", body={
            "title": "T", "subject": "S", "max_score": 10})
        s, _ = self.call("POST", "/api/scores", role="teacher", body={
            "assessment_id": a["id"], "student_name": "X", "score": 11})
        self.assertEqual(s, 400)

    def test_student_cannot_edit_grades(self):
        s, _ = self.call("POST", "/api/assessments", role="student", body={
            "title": "T", "subject": "S", "max_score": 10})
        self.assertEqual(s, 403)

    def test_average_with_no_scores_is_zero(self):
        s, avg = self.call("GET", "/api/scores?student_name=Ghost",
                           role="teacher")
        self.assertEqual((avg["assessments"], avg["average_pct"]), (0, 0.0))


class TimetableTest(DbTestCase):
    def slot(self, **kw):
        base = {"weekday": "Mon", "starts_at": "08:00", "ends_at": "09:00",
                "class_name": "JSS1", "subject": "Maths",
                "teacher": "Mr Ade", "room": "R1"}
        base.update(kw)
        return self.call("POST", "/api/slots", role="admin", body=base)

    def test_add_and_list(self):
        s, slot = self.slot()
        self.assertEqual(s, 201)
        s, slots = self.call("GET", "/api/slots?weekday=Mon", role="student")
        self.assertEqual(len(slots), 1)

    def test_room_clash_rejected(self):
        self.slot()
        s, err = self.slot(class_name="JSS2", teacher="Ms Bello",
                           starts_at="08:30", ends_at="09:30")
        self.assertEqual(s, 400)
        self.assertIn("clash", err["error"])

    def test_teacher_clash_rejected(self):
        self.slot()
        s, _ = self.slot(class_name="JSS2", room="R2",
                         starts_at="08:30", ends_at="09:30")
        self.assertEqual(s, 400)

    def test_non_overlapping_slot_ok(self):
        self.slot()
        s, _ = self.slot(starts_at="09:00", ends_at="10:00")
        self.assertEqual(s, 201)

    def test_delete(self):
        _, slot = self.slot()
        s, out = self.call("DELETE", f"/api/slots/{slot['id']}", role="admin")
        self.assertEqual(out, {"deleted": slot["id"]})
        s, _ = self.call("DELETE", f"/api/slots/{slot['id']}", role="admin")
        self.assertEqual(s, 404)

    def test_bad_time_range_rejected(self):
        s, _ = self.slot(starts_at="10:00", ends_at="09:00")
        self.assertEqual(s, 400)
