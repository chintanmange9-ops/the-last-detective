import unittest

from deduction.contradictions import find_contradictions
from mystery.generator import generate_case
from game.state import GameState
from game import commands, scoring


class TestRankBoundaries(unittest.TestCase):
    def test_rank_boundaries(self):
        cases = {
            0: "Apprentice",
            399: "Apprentice",
            400: "Inspector",
            599: "Inspector",
            600: "Detective",
            749: "Detective",
            750: "Chief Inspector",
            899: "Chief Inspector",
            900: "The Last Detective",
            1000: "The Last Detective",
        }
        for score, expected in cases.items():
            self.assertEqual(scoring.rank_for(score), expected, f"score={score}")


class TestCaseScore(unittest.TestCase):
    def _state(self, seed, turn=0, hints=0, attempts=None):
        case = generate_case(seed)
        state = GameState(
            seed=seed,
            current_location=case.truth.location,
            turn=turn,
            hints_used=hints,
            accusation_attempts=list(attempts or []),
        )
        return case, state

    def test_hint_penalty(self):
        case, plain = self._state(48291)
        case2, hinted = self._state(48291, hints=1)
        self.assertEqual(
            scoring.case_score(case2, hinted, won=False),
            scoring.case_score(case, plain, won=False) - 75,
        )

    def test_wrong_accusation_penalty(self):
        case, exact = self._state(48291, attempts=["Simon", "Grace"])
        case2, loose = self._state(48291, attempts=["Grace"])
        exact_won = scoring.case_score(case, exact, won=True)
        loose_won = scoring.case_score(case2, loose, won=True)
        self.assertEqual(exact_won + 150, loose_won)

    def test_win_bonus(self):
        case, won = self._state(48291)
        case2, lost = self._state(48291)
        self.assertEqual(
            scoring.case_score(case, won, won=True),
            scoring.case_score(case2, lost, won=False) + 200,
        )

    def test_all_evidence_floor(self):
        """With every piece of evidence discovered, no wrong moves and no
        hints, the score can't drop below the evidence pool + win bonus."""
        case, state = self._state(48291, turn=0)
        for ev in case.evidence.values():
            ev.discovered = True
        state.accusation_attempts = ["Simon"]
        score = scoring.case_score(case, state, won=True)
        self.assertGreaterEqual(score, 500 + 200 + 100)  # evidence + win

    def test_perfect_solve_is_top_rank(self):
        case, state = self._state(48291, turn=0)
        for ev in case.evidence.values():
            ev.discovered = True
        state.accusation_attempts = [case.truth.killer]
        killer = case.suspects[case.truth.killer]
        killer.interrogation.confessed = True
        score = scoring.case_score(case, state, won=True)
        self.assertEqual(scoring.rank_for(score), "The Last Detective")


class TestHintCommand(unittest.TestCase):
    def test_hint_points_at_undiscovered_location(self):
        case = generate_case(48291)
        state = GameState(seed=48291, current_location=case.truth.location)
        output, _ = commands.execute("hint", case, state)
        self.assertIn("more to find", output)
        self.assertEqual(state.hints_used, 1)

    def test_hint_when_all_found(self):
        case = generate_case(48291)
        state = GameState(seed=48291, current_location=case.truth.location)
        for ev in case.evidence.values():
            ev.discovered = True
        output, _ = commands.execute("hint", case, state)
        self.assertIn("found every piece", output)
        self.assertEqual(state.hints_used, 0)

    def test_accuse_includes_rank_epilogue(self):
        case = generate_case(48291)
        state = GameState(seed=48291, current_location=case.truth.location)
        output, _ = commands.execute(f"accuse {case.truth.killer}", case, state)
        self.assertIn("Rank:", output)
        self.assertIn("Case score:", output)


class TestWinScreenEvidenceList(unittest.TestCase):
    """The win screen must only list evidence that genuinely contradicted
    the killer's alibi, not every piece of evidence presented."""

    def _killer_evidence_pair(self, case):
        killer = case.suspects[case.truth.killer]
        claim = [killer.alibi_fact()]
        conflicting, irrelevant = None, None
        for ev in case.evidence.values():
            if ev.is_red_herring:
                continue
            hits = find_contradictions(claim, ev.facts)
            if hits and conflicting is None:
                conflicting = ev
            elif not hits and irrelevant is None:
                irrelevant = ev
            if conflicting is not None and irrelevant is not None:
                break
        return conflicting, irrelevant

    def test_win_screen_only_lists_contradicting_evidence(self):
        case = generate_case(48291)
        state = GameState(seed=48291, current_location=case.truth.location)
        conflicting, irrelevant = self._killer_evidence_pair(case)
        if conflicting is None or irrelevant is None:
            self.fail("case should have both a contradicting and an "
                      "irrelevant evidence for the killer")

        commands.execute(f"question {case.truth.killer}", case, state)
        for ev in (conflicting, irrelevant):
            ev.discovered = True
            commands.execute(f"present {ev.id}", case, state)

        output, _ = commands.execute(f"accuse {case.truth.killer}", case, state)
        self.assertIn(f"Evidence used against them: #{conflicting.id}", output)
        self.assertNotIn(f"#{irrelevant.id}", output)

    def test_win_screen_omits_entry_when_nothing_contradicted(self):
        case = generate_case(48291)
        state = GameState(seed=48291, current_location=case.truth.location)
        output, _ = commands.execute(f"accuse {case.truth.killer}", case, state)
        self.assertNotIn("Evidence used against them", output)


class TestSaveHintsRoundTrip(unittest.TestCase):
    def test_hints_used_round_trips(self):
        import tempfile
        from pathlib import Path
        from storage.save import save_game, load_game

        case = generate_case(48291)
        state = GameState(seed=48291, current_location=case.truth.location,
                          hints_used=3)
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / "save.json")
            save_game(path, case, state)
            _, loaded = load_game(path)
        self.assertEqual(loaded.hints_used, 3)


if __name__ == "__main__":
    unittest.main()