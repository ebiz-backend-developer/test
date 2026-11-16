"""Scope, stakeholders, users through the service layer. (c1)"""
import unittest

from app import service
from app.seed import seed
from app.store import Store


class TestScopeRoles(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")
        seed(self.store)

    def tearDown(self):
        self.store.close()

    def test_seed_scope_covers_all_kinds(self):
        kinds = {i["kind"] for i in service.list_scope(self.store)}
        self.assertEqual(
            kinds, {"in_scope", "out_of_scope", "assumption", "constraint"})

    def test_add_scope_item_and_filter(self):
        item = service.add_scope_item(
            self.store, "Ada", "principal", "in_scope", "Report cards",
            "Term report cards per class.")
        self.assertEqual(item["title"], "Report cards")
        kinds = [i["kind"]
                 for i in service.list_scope(self.store, kind="in_scope")]
        self.assertTrue(all(k == "in_scope" for k in kinds))
        self.assertIn("Report cards",
                      [i["title"] for i in service.list_scope(self.store)])

    def test_student_cannot_add_scope(self):
        with self.assertRaises(service.ServiceError) as ctx:
            service.add_scope_item(
                self.store, "Stacy", "student", "in_scope", "Games room")
        self.assertEqual(ctx.exception.status, 403)

    def test_stakeholders_map_to_roles_and_journeys(self):
        holders = service.list_stakeholders(self.store)
        self.assertGreaterEqual(len(holders), 7)
        for holder in holders:
            service.role_detail(self.store, holder["primary_role"])
            service.get_workflow(self.store, holder["journey_ref"])

    def test_update_stakeholder(self):
        updated = service.update_stakeholder(
            self.store, "Ada", "principal", "parents",
            interest="Track wards, pay fees, message teachers.")
        self.assertIn("pay fees", updated["interest"])
        with self.assertRaises(service.ServiceError):
            service.update_stakeholder(
                self.store, "Tom", "teacher", "parents", interest="x")

    def test_roles_carry_permissions(self):
        roles = {r["code"]: r for r in service.list_roles(self.store)}
        self.assertEqual(len(roles), 10)
        self.assertIn("milestones.approve",
                      roles["principal"]["permissions"])
        detail = service.role_detail(self.store, "student")
        self.assertEqual(detail["permissions"], ["workflows.run"])

    def test_add_user_validates_role_and_email(self):
        user = service.add_user(self.store, "Sam", "sysadmin", "Nina New",
                                "nina@school.example", "teacher")
        self.assertEqual(user["role"], "teacher")
        with self.assertRaises(service.ServiceError):
            service.add_user(self.store, "Sam", "sysadmin", "Bogus",
                             "bogus@school.example", "janitor")
        with self.assertRaises(service.ServiceError):
            service.add_user(self.store, "Sam", "sysadmin", "Dup",
                             "nina@school.example", "teacher")
        with self.assertRaises(service.ServiceError) as ctx:
            service.add_user(self.store, "Stacy", "student", "Sneaky",
                             "sneaky@school.example", "sysadmin")
        self.assertEqual(ctx.exception.status, 403)


if __name__ == "__main__":
    unittest.main()
