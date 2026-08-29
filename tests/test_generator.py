import unittest
from mystery.generator import generate_case


class TestDeterminism(unittest.TestCase):
    def test_same_seed_same_case(self):
        a = generate_case(48291)
        b = generate_case(48291)
        self.assertEqual(a.truth.killer, b.truth.killer)
        self.assertEqual(a.truth.victim, b.truth.victim)
        self.assertEqual(a.truth.weapon, b.truth.weapon)
        self.assertEqual(a.truth.motive, b.truth.motive)
        self.assertEqual(a.truth.location, b.truth.location)
        self.assertEqual(a.truth.time, b.truth.time)
        self.assertEqual(sorted(a.suspects.keys()), sorted(b.suspects.keys()))
        self.assertEqual(sorted(a.evidence.keys()), sorted(b.evidence.keys()))

    def test_different_seeds_usually_differ(self):
        seeds = range(20)
        keys = set()
        for s in seeds:
            case = generate_case(s)
            keys.add((case.truth.killer, case.truth.victim, case.truth.location, case.truth.time))
        # Not every seed needs to be unique, but 20 seeds should not all collapse to one case.
        self.assertGreater(len(keys), 1)


class TestCaseGeneration(unittest.TestCase):
    def setUp(self):
        self.case = generate_case(1234)

    def test_suspect_count_in_range(self):
        self.assertGreaterEqual(len(self.case.suspects), 3)
        self.assertLessEqual(len(self.case.suspects), 6)

    def test_has_evidence(self):
        self.assertGreaterEqual(len(self.case.evidence), 5)

    def test_has_timeline(self):
        self.assertGreater(len(self.case.timeline.all_events()), 0)


if __name__ == "__main__":
    unittest.main()
