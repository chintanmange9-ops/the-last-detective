import json
import tempfile
import unittest
from pathlib import Path

from mystery.generator import generate_case
from game.state import GameState
from game.engine import Engine
from game import commands
from storage.save import save_game, load_game
from storage.replay import save_replay, load_replay


class TestLocationReachability(unittest.TestCase):
    def test_all_locations_mutually_reachable(self):
        case = generate_case(1)
        graph = case.location_graph
        names = graph.names()
        for a in names:
            reachable = set(graph.reachable_from(a))
            for b in names:
                self.assertIn(b, reachable, f"{b} not reachable from {a}")


class TestSaveLoad(unittest.TestCase):
    def test_save_and_load_round_trip(self):
        case = generate_case(48291)
        state = GameState(seed=48291, current_location=case.truth.location)
        engine = Engine(case, state, record=True)
        engine.process_line("inspect " + case.truth.location)
        engine.process_line("note testing 123")

        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / "save.json")
            save_game(path, engine.case, engine.state)
            self.assertTrue(Path(path).exists())

            loaded_case, loaded_state = load_game(path)
            self.assertEqual(loaded_state.seed, 48291)
            self.assertEqual(loaded_state.notes, ["testing 123"])
            discovered_before = {e.id for e in engine.case.evidence.values() if e.discovered}
            discovered_after = {e.id for e in loaded_case.evidence.values() if e.discovered}
            self.assertEqual(discovered_before, discovered_after)


class TestReplay(unittest.TestCase):
    def test_replay_reproduces_same_outcome(self):
        case = generate_case(48291)
        killer = case.truth.killer
        murder_loc = case.truth.location

        actions = [f"inspect {murder_loc}", "examine murder weapon", f"accuse {killer}"]

        state1 = GameState(seed=48291, current_location=murder_loc)
        engine1 = Engine(generate_case(48291), state1, record=True)
        for a in actions:
            engine1.process_line(a)
        self.assertTrue(engine1.state.won)

        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / "run.json")
            save_replay(path, 48291, actions)
            seed, loaded_actions = load_replay(path)
            self.assertEqual(seed, 48291)

            state2 = GameState(seed=seed, current_location=murder_loc)
            engine2 = Engine(generate_case(seed), state2, record=False)
            for a in loaded_actions:
                engine2.process_line(a)
            self.assertTrue(engine2.state.won)
            self.assertEqual(engine1.case.truth.killer, engine2.case.truth.killer)


class TestAccusation(unittest.TestCase):
    def test_correct_accusation_wins(self):
        case = generate_case(48291)
        state = GameState(seed=48291, current_location=case.truth.location)
        engine = Engine(case, state, record=False)
        engine.process_line(f"accuse {case.truth.killer}")
        self.assertTrue(engine.state.won)
        self.assertTrue(engine.state.game_over)

    def test_incorrect_accusation_loses(self):
        case = generate_case(48291)
        wrong = next(n for n in case.suspects if n != case.truth.killer)
        state = GameState(seed=48291, current_location=case.truth.location)
        engine = Engine(case, state, record=False)
        engine.process_line(f"accuse {wrong}")
        self.assertFalse(engine.state.won)
        self.assertTrue(engine.state.game_over)


class TestTypoSuggestions(unittest.TestCase):
    def test_known_typo_suggests_timeline(self):
        case = generate_case(48291)
        state = GameState(seed=48291, current_location=case.truth.location)
        output, _ = commands.execute("timelime", case, state)
        self.assertIn("Did you mean 'timeline'", output)

    def test_unknown_command_plain_message(self):
        case = generate_case(48291)
        state = GameState(seed=48291, current_location=case.truth.location)
        output, _ = commands.execute("frobnicate the widget", case, state)
        self.assertIn("Unknown command 'frobnicate'", output)
        self.assertNotIn("Did you mean", output)


class TestExamineLocation(unittest.TestCase):
    def test_examine_connected_location_behaves_like_inspect(self):
        case = generate_case(48291)
        start = case.truth.location
        loc = case.location_graph.get(start)
        connected = loc.connections[0] if loc else start
        state = GameState(seed=48291, current_location=start)
        out_inspect, _ = commands.execute(f"inspect {connected}", case, state)
        state2 = GameState(seed=48291, current_location=start)
        out_examine, _ = commands.execute(f"examine {connected}", case, state2)
        self.assertEqual(state.current_location, connected)
        self.assertEqual(state2.current_location, connected)
        self.assertIn("You are now in", out_examine)
        self.assertIn("You are now in", out_inspect)

    def test_examine_unknown_target_lists_objects(self):
        case = generate_case(48291)
        state = GameState(seed=48291, current_location=case.truth.location)
        start_objs = [o.name for o in case.world_objects.get(state.current_location, [])]
        output, _ = commands.execute("examine building", case, state)
        self.assertIn("You can't examine 'building'", output)
        for obj in start_objs:
            self.assertIn(obj, output)

    def test_examine_unknown_target_offers_inspect_hint(self):
        case = generate_case(48291)
        state = GameState(seed=48291, current_location=case.truth.location)
        output, _ = commands.execute("examine parking lot", case, state)
        self.assertIn("inspect", output.lower())


if __name__ == "__main__":
    unittest.main()
