import unittest

from school import milestones


class MilestoneTests(unittest.TestCase):
    def test_all_milestones_delivered_and_approved(self):
        progress = milestones.overall_progress()
        self.assertEqual(progress["milestones_total"], 4)
        self.assertEqual(progress["milestones_delivered"], 4)
        self.assertEqual(progress["percent"], 100.0)
        self.assertTrue(progress["all_approved"])
        for ms in progress["milestones"]:
            self.assertEqual(ms["status"], "delivered")
            self.assertEqual(ms["missing_modules"], [])

    def test_module_registry_covers_mvp(self):
        self.assertGreaterEqual(len(milestones.MODULES), 7)
        prios = {m["mvp_priority"] for m in milestones.MODULES.values()}
        self.assertEqual(prios, {1, 2, 3})


if __name__ == "__main__":
    unittest.main()
