import unittest
from mystery.generator import generate_case
from evidence import system as evidence_system
from evidence.models import Fact


class TestEvidenceDiscovery(unittest.TestCase):
    def setUp(self):
        self.case = generate_case(48291)

    def test_nothing_discovered_at_start(self):
        self.assertEqual(len(evidence_system.discovered_evidence(self.case)), 0)

    def test_inspect_location_discovers_evidence(self):
        found = evidence_system.discover_by_location(self.case, self.case.truth.location)
        self.assertGreater(len(found), 0)
        self.assertTrue(all(ev.discovered for ev in found))

    def test_examine_object_discovers_evidence(self):
        evidence_system.discover_by_location(self.case, self.case.truth.location)
        found = evidence_system.discover_by_object(self.case, self.case.truth.location, "murder weapon")
        self.assertGreater(len(found), 0)

    def test_discovery_is_idempotent(self):
        first = evidence_system.discover_by_location(self.case, self.case.truth.location)
        second = evidence_system.discover_by_location(self.case, self.case.truth.location)
        self.assertEqual(second, [])
        self.assertGreater(len(first), 0)


class TestFactOverlap(unittest.TestCase):
    def test_overlapping_ranges(self):
        a = Fact("Alice", "location", "Office", 100, 200)
        b = Fact("Alice", "location", "Library", 150, 250)
        self.assertTrue(a.overlaps(b))

    def test_non_overlapping_ranges(self):
        a = Fact("Alice", "location", "Office", 100, 150)
        b = Fact("Alice", "location", "Library", 200, 250)
        self.assertFalse(a.overlaps(b))

    def test_point_in_range(self):
        a = Fact("Alice", "location", "Office", 100, 200)
        b = Fact("Alice", "location", "Library", 150, 150)
        self.assertTrue(a.overlaps(b))


if __name__ == "__main__":
    unittest.main()
