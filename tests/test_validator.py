import unittest
from mystery.generator import generate_case
from mystery.validator import validate_case


class TestValidator(unittest.TestCase):
    def test_generated_cases_are_valid(self):
        for seed in range(30):
            case = generate_case(seed)
            result = validate_case(case)
            self.assertTrue(result.valid, f"seed {seed} invalid: {result.errors}")

    def test_exactly_one_killer(self):
        case = generate_case(7)
        killers = [s for s in case.suspects.values() if s.is_killer]
        self.assertEqual(len(killers), 1)

    def test_killer_is_a_suspect(self):
        case = generate_case(7)
        self.assertIn(case.truth.killer, case.suspects)

    def test_victim_is_not_killer(self):
        case = generate_case(7)
        self.assertNotEqual(case.truth.victim, case.truth.killer)

    def test_unique_solution_conflict_is_only_killer(self):
        from deduction.contradictions import find_contradictions
        case = generate_case(7)
        non_herring_facts = [f for ev in case.evidence.values() if not ev.is_red_herring for f in ev.facts]
        conflicted = set()
        for name, suspect in case.suspects.items():
            hits = find_contradictions([suspect.alibi_fact()], non_herring_facts)
            if hits:
                conflicted.add(name)
        self.assertEqual(conflicted, {case.truth.killer})


class TestStress(unittest.TestCase):
    def test_stress_generate_many_cases(self):
        failures = []
        for seed in range(200):
            case = generate_case(seed)
            result = validate_case(case)
            if not result.valid:
                failures.append((seed, result.errors))
        self.assertEqual(failures, [], f"{len(failures)} invalid cases out of 200")


if __name__ == "__main__":
    unittest.main()
