"""Task 5 coverage check: data model & architecture (c1-c4).

Stdlib-only. Verifies the design doc exists and covers every acceptance
criterion plus the Task 5 focus areas: entities, relationships, auth,
and multi-school support; and that the reference schema implements the
tenancy + relationship contract.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "data-model-architecture.md"
SCHEMA = ROOT / "db" / "schema.sql"

MODULES = ["admissions", "attendance", "grades", "timetable", "fees", "communication"]
ROLES = ["administrator", "principal", "registrar", "teacher", "accountant",
         "student", "parent", "guardian"]


class TestDataModelArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert DOC.exists(), f"missing design doc: {DOC}"
        assert SCHEMA.exists(), f"missing reference schema: {SCHEMA}"
        cls.text = DOC.read_text(encoding="utf-8")
        cls.lower = cls.text.lower()
        cls.schema = SCHEMA.read_text(encoding="utf-8")
        cls.schema_lower = cls.schema.lower()

    def test_doc_is_substantive(self):
        self.assertGreater(len(self.text), 5000, "doc looks like a stub")

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

    def test_c3_entities_and_relationships(self):
        for term in ["entit", "relationship", "foreign key", "cardinality"]:
            self.assertIn(term, self.lower, f"c3 data model missing: {term}")
        for table in ["students", "enrolments", "invoices", "scores", "lessons"]:
            self.assertIn(table, self.lower, f"c3 entity missing from doc: {table}")

    def test_c3_multischool(self):
        self.assertTrue(
            ("multi-school" in self.lower) or ("multischool" in self.lower),
            "c3 missing multi-school design",
        )
        for term in ["school_id", "tenant", "row-level", "isolation"]:
            self.assertIn(term, self.lower, f"c3 tenancy missing: {term}")

    def test_c4_milestones_and_approval(self):
        for term in ["milestone", "exit criteria", "approval"]:
            self.assertIn(term, self.lower, f"c4 missing: {term}")
        for milestone in ["m0", "m1", "m2", "m3", "m4"]:
            self.assertIn(milestone, self.lower, f"c4 milestone missing: {milestone}")

    def test_schema_tables_and_keys(self):
        tables = re.findall(r"create table (\w+)", self.schema_lower)
        self.assertGreaterEqual(len(tables), 25, f"schema has too few tables: {len(tables)}")
        for table in ["schools", "users", "students", "invoices", "scores",
                      "lessons", "attendance_entries", "audit_log"]:
            self.assertIn(table, tables, f"schema missing table: {table}")
        self.assertIn("references", self.schema_lower, "schema has no foreign keys")
        self.assertIn("school_id", self.schema_lower, "schema has no school_id tenancy column")

    def test_schema_tenancy_enforcement(self):
        self.assertIn("row level security", self.schema_lower,
                       "schema missing RLS tenancy enforcement")
        self.assertIn("app.current_school_id", self.schema,
                       "schema missing tenant session variable")


if __name__ == "__main__":
    unittest.main()
