import unittest
from characters import nlu
from mystery.generator import generate_case
from game.state import GameState
from game import commands


class TestNLUInterpret(unittest.TestCase):
    def test_location_phrases(self):
        for phrase in ["where were you?", "where did you go", "where was I",
                       "what was your location"]:
            self.assertEqual(nlu.interpret(phrase), "location", phrase)

    def test_timeline_phrases(self):
        for phrase in ["what happened?", "what time did that happen",
                       "what went on that night", "tell me the timeline"]:
            self.assertEqual(nlu.interpret(phrase), "timeline", phrase)

    def test_motive_phrases(self):
        for phrase in ["why?", "why did you do it", "what was your motive",
                       "give me a reason"]:
            self.assertEqual(nlu.interpret(phrase), "motive", phrase)

    def test_weapon_phrases(self):
        for phrase in ["what weapon?", "how did you do it", "was it a knife",
                       "tell me about the weapon"]:
            self.assertEqual(nlu.interpret(phrase), "weapon", phrase)

    def test_victim_phrases(self):
        for phrase in ["who was the victim?", "tell me about the deceased",
                       "did you see the body", "who killed them?"]:
            self.assertEqual(nlu.interpret(phrase), "victim", phrase)

    def test_relationship_phrases(self):
        for phrase in ["how did you know the victim", "were you friends",
                       "what was your relationship"]:
            self.assertEqual(nlu.interpret(phrase), "relationship", phrase)

    def test_other_phrases(self):
        for phrase in ["was anyone else around", "did you see someone else",
                       "any others involved", "was everyone else there"]:
            self.assertEqual(nlu.interpret(phrase), "other", phrase)

    def test_evidence_phrases(self):
        for phrase in ["what did you find", "any evidence against me",
                       "show me evidence"]:
            self.assertEqual(nlu.interpret(phrase), "evidence", phrase)

    def test_why_beats_where(self):
        self.assertEqual(nlu.interpret("why were you there?"), "motive")

    def test_gibberish_returns_none(self):
        self.assertIsNone(nlu.interpret("garbled nonsense zzz"))
        self.assertIsNone(nlu.interpret(""))
        self.assertIsNone(nlu.interpret("   "))

    def test_case_insensitive(self):
        self.assertEqual(nlu.interpret("WHY DID YOU DO IT?"), "motive")


class TestNLUInGame(unittest.TestCase):
    def test_question_phrase_returns_location(self):
        case = generate_case(48291)
        queryable = next(iter(case.suspects.keys()))
        state = GameState(seed=48291, current_location=case.truth.location)
        output, _ = commands.execute(f"question {queryable}", case, state)
        self.assertIn(queryable, output)
        output, _ = commands.execute("where were you?", case, state)
        self.assertIn("says:", output)
        self.assertIn("I was in the", output)

    def test_unrecognized_phrase_suggests_options(self):
        case = generate_case(48291)
        queryable = next(iter(case.suspects.keys()))
        state = GameState(seed=48291, current_location=case.truth.location)
        commands.execute(f"question {queryable}", case, state)
        output, _ = commands.execute("qwerty bubble", case, state)
        self.assertIn("I'm not sure what you're asking", output)


if __name__ == "__main__":
    unittest.main()