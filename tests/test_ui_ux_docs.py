"""Task 6 acceptance guard: UI/UX flows doc must cover c1-c4.

Stdlib only (unittest). Run: python3 -m unittest discover -s tests -v
"""

import pathlib
import unittest

DOC = pathlib.Path(__file__).resolve().parent.parent / "docs" / "ui-ux-flows.md"


def read_doc() -> str:
    return DOC.read_text(encoding="utf-8")


class TestUiUxFlowsDoc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert DOC.is_file(), f"missing deliverable: {DOC}"
        cls.text = read_doc()
        cls.lower = cls.text.lower()

    def test_c1_scope_and_roles(self):
        for needle in ["## c1", "in scope", "out of scope",
                       "permission matrix", "admin", "manager",
                       "portal user", "viewer", "guest"]:
            self.assertIn(needle, self.lower, f"c1 missing: {needle}")

    def test_c2_modules_and_mvp(self):
        for needle in ["## c2", "mvp", "moscow", "p0",
                       "auth", "dashboard", "portal", "workflow"]:
            self.assertIn(needle, self.lower, f"c2 missing: {needle}")

    def test_c3_architecture_and_stack(self):
        for needle in ["## c3", "tech stack", "typescript",
                       "tailwind", "accessibility", "api"]:
            self.assertIn(needle, self.lower, f"c3 missing: {needle}")

    def test_c4_milestones(self):
        for needle in ["## c4", "milestone", "exit criteria",
                       "approval", "m1", "m4"]:
            self.assertIn(needle, self.lower, f"c4 missing: {needle}")

    def test_task_topics_covered(self):
        for needle in ["dashboard", "portal", "mobile",
                       "wireframe", "user flow", "breakpoint"]:
            self.assertIn(needle, self.lower, f"topic missing: {needle}")

    def test_no_placeholder(self):
        for needle in ["todo", "tbd", "lorem", "placeholder"]:
            self.assertNotIn(needle, self.lower, f"placeholder found: {needle}")


if __name__ == "__main__":
    unittest.main()
