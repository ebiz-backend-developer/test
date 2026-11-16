"""Shared fixtures: in-memory store with one account per role."""
import unittest

from school.auth import AuthService
from school.service import SchoolService
from school.store import Store


class SchoolTestCase(unittest.TestCase):
    def setUp(self):
        self.store = Store()  # in-memory, no file
        self.auth = AuthService(self.store)
        self.svc = SchoolService(self.store, self.auth)
        self.users = {}
        for role in ("admin", "teacher", "student", "parent", "staff"):
            self.users[role] = self.auth.create_user(
                f"{role}", f"{role}-pw", role)
        self.admin = self.store.get("users", self.users["admin"]["id"])
        self.teacher = self._make_teacher_with_class()

    def _make_teacher_with_class(self):
        t = self.svc.create_teacher(self.admin, first_name="Test",
                                    last_name="Teacher",
                                    email="t.teacher@school.edu",
                                    subject="Math")
        teach_user = self.store.get("users", self.users["teacher"]["id"])
        teach_user["link_id"] = t["id"]
        self.store.put("users", teach_user["id"], teach_user)
        cls = self.svc.create_class(self.admin, name="Math 101",
                                    grade_level=9, teacher_id=t["id"],
                                    room="A1", capacity=2)
        self.teacher_rec = t
        self.class_rec = cls
        return self.store.get("users", teach_user["id"])

    def make_student(self, tag="a", **over):
        fields = {"first_name": "Stu", "last_name": f"Dent{tag}",
                  "email": f"stu.{tag}@student.edu", "grade_level": 9}
        fields.update(over)
        return self.svc.create_student(self.admin, **fields)

    def link_student_user(self, role, student_id):
        u = self.store.get("users", self.users[role]["id"])
        u["link_id"] = student_id
        self.store.put("users", u["id"], u)
        return self.store.get("users", u["id"])
