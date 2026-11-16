"""c3: architecture and tech stack selected."""
import unittest

from tests.helpers import make_service


class TechStackTest(unittest.TestCase):
    def setUp(self):
        self.svc = make_service()

    def test_stack_covers_all_layers(self):
        stack = self.svc.architecture()["stack"]
        self.assertEqual(set(stack), {"language", "api", "datastore", "ui", "tests"})
        self.assertTrue(all(v.strip() for v in stack.values()))

    def test_components_defined(self):
        comps = self.svc.architecture()["components"]
        ids = {c["id"] for c in comps}
        self.assertEqual(ids, {"web-ui", "http-api", "service", "store"})
        for comp in comps:
            self.assertTrue(comp["responsibility"].strip())

    def test_data_flow_orders_components(self):
        arch = self.svc.architecture()
        self.assertEqual(arch["data_flow"], ["web-ui", "http-api", "service", "store"])

    def test_decisions_recorded_and_accepted(self):
        decisions = self.svc.architecture()["decisions"]
        self.assertGreaterEqual(len(decisions), 3)
        self.assertTrue(all(d["status"] == "accepted" for d in decisions))
        self.assertTrue(all(d["rationale"].strip() for d in decisions))


if __name__ == "__main__":
    unittest.main()
