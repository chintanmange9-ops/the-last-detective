import unittest
from evidence.models import Fact
from deduction.contradictions import find_contradictions, CATEGORY_LOCATION, CATEGORY_TEMPORAL, CATEGORY_ACCESS


class TestContradictions(unittest.TestCase):
    def test_temporal_contradiction_detected(self):
        claim = Fact("Alice", "location", "Cafeteria", 100, 200)
        fact = Fact("Alice", "location", "Laboratory", 150, 250)
        hits = find_contradictions([claim], [fact])
        self.assertTrue(any(h.category == CATEGORY_TEMPORAL for h in hits))

    def test_location_point_contradiction_detected(self):
        claim = Fact("Alice", "location", "Cafeteria", 100, 200)
        fact = Fact("Alice", "location", "Laboratory", 150, 150)
        hits = find_contradictions([claim], [fact])
        self.assertTrue(any(h.category == CATEGORY_LOCATION for h in hits))

    def test_matching_claim_no_contradiction(self):
        claim = Fact("Alice", "location", "Cafeteria", 100, 200)
        fact = Fact("Alice", "location", "Cafeteria", 150, 160)
        hits = find_contradictions([claim], [fact])
        self.assertEqual(hits, [])

    def test_different_subject_no_contradiction(self):
        claim = Fact("Alice", "location", "Cafeteria", 100, 200)
        fact = Fact("Bob", "location", "Laboratory", 150, 160)
        hits = find_contradictions([claim], [fact])
        self.assertEqual(hits, [])

    def test_access_contradiction_detected(self):
        claim = Fact("Alice", "location", "Cafeteria", 100, 200)
        fact = Fact("Alice", "access", "Laboratory", 500, 500)
        hits = find_contradictions([claim], [fact])
        self.assertTrue(any(h.category == CATEGORY_ACCESS for h in hits))

    def test_non_overlapping_no_contradiction(self):
        claim = Fact("Alice", "location", "Cafeteria", 100, 120)
        fact = Fact("Alice", "location", "Laboratory", 500, 520)
        hits = find_contradictions([claim], [fact])
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
