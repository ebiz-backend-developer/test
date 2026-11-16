"""c1: scope and user roles."""
import unittest

from delivery import seed, service
from delivery.models import Scope
from delivery.store import connect, migrate


def fresh():
    conn = connect(":memory:")
    migrate(conn)
    seed.seed(conn)
    return conn


class RolesTest(unittest.TestCase):
    def test_five_roles_with_descriptions(self):
        roles = service.list_roles(fresh())
        self.assertEqual(
            sorted(r["name"] for r in roles),
            ["admin", "developer", "product_owner", "stakeholder", "tech_lead"],
        )
        for r in roles:
            self.assertTrue(r["description"])

    def test_unknown_role_rejected(self):
        with self.assertRaises(service.AuthError):
            service.require_role("janitor")


class ScopeTest(unittest.TestCase):
    def test_seeded_scope_readable(self):
        scope = service.get_scope(fresh())
        self.assertTrue(scope["vision"])
        self.assertGreaterEqual(len(scope["in_scope"]), 1)

    def test_owner_can_save_scope(self):
        conn = fresh()
        saved = service.save_scope(
            conn,
            Scope(vision="V", in_scope=["a"], out_of_scope=["b"]),
            role="product_owner",
        )
        self.assertEqual(saved["vision"], "V")
        self.assertEqual(service.get_scope(conn)["vision"], "V")

    def test_stakeholder_and_developer_cannot_write_scope(self):
        conn = fresh()
        scope = Scope(vision="V", in_scope=["a"])
        for role in ("stakeholder", "developer", "tech_lead"):
            with self.assertRaises(service.AuthError, msg=role):
                service.save_scope(conn, scope, role=role)

    def test_scope_validation(self):
        conn = fresh()
        with self.assertRaises(service.ValidationError):
            service.save_scope(conn, Scope(vision=" ", in_scope=["a"]), role="admin")
        with self.assertRaises(service.ValidationError):
            service.save_scope(conn, Scope(vision="V", in_scope=[]), role="admin")
        with self.assertRaises(service.ValidationError):
            service.save_scope(
                conn, Scope(vision="V", in_scope=["a"], out_of_scope=["a"]), role="admin"
            )


if __name__ == "__main__":
    unittest.main()
