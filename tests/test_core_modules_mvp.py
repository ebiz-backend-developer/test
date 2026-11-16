"""Task 4 coverage check: core modules & MVP definition (c1-c4).

Stdlib-only. Verifies the definition doc exists and covers every
acceptance criterion: scope + roles (c1), modules + MVP (c2),
architecture + stack (c3), milestones + approval (c4).
"""
import unittest
from pathlib import Path

DOC = Path(__file__).resolve().parent.parent / "docs" / "core-modules-mvp.md"
MODULES = ["admissions", "attendance", "grades", "timetable", "fees", "communication"]
ROLES = ["administrator", "principal", "registrar", "teacher", "accountant",
         "student", "parent", "guardian"]


class TestCoreModulesMvp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert DOC.exists(), f"missing definition doc: {DOC}"
        cls.text = DOC.read_text(encoding="utf-8")
        cls.lower = cls.text.lower()

    def test_doc_is_substantive(self):
        self.assertGreater(len(self.text), 3000, "doc looks like a stub")

    def test_c1_scope(self):
        for term in ["in scope", "out of scope", "assumption"]:
            self.assertIn(term, self.lower, f"c1 scope missing: {term}")

    def test_c1_roles(self):
        for role in ROLES:
            self.assertIn(role, self.lower, f"c1 role missing: {role}")
        self.assertIn("permission", self.lower, "c1 missing permission rules")

    def test_c2_modules_and_mvp(self):
        for module in MODULES:
            self.assertIn(module, self.lower, f"c2 module missing: {module}")
        for term in ["mvp", "must", "phase 2"]:
            self.assertIn(term, self.lower, f"c2 prioritization missing: {term}")

    def test_c3_architecture_and_stack(self):
        for term in ["architecture", "tech stack", "database", "auth"]:
            self.assertIn(term, self.lower, f"c3 missing: {term}")

    def test_c4_milestones_and_approval(self):
        for term in ["milestone", "exit criteria", "approval"]:
            self.assertIn(term, self.lower, f"c4 missing: {term}")
        for milestone in ["m0", "m1", "m2", "m3", "m4"]:
            self.assertIn(milestone, self.lower, f"c4 milestone missing: {milestone}")


if __name__ == "__main__":
    unittest.main()
