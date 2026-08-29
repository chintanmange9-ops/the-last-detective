import unittest

from mystery.generator import generate_case
from game.state import GameState
from game.engine import Engine
from tools import solver


class TestSolverWins(unittest.TestCase):
    def test_solver_wins_on_seed_range(self):
        for seed in range(1, 51):
            case = generate_case(seed)
            won, _ = solver.solve(case, seed)
            self.assertTrue(won, f"solver failed to solve seed {seed}")

    def test_solver_truth_never_accessed(self):
        """The solver must solve cases without ever reading the hidden
        truth answer key (the same constraint the player is under)."""
        import inspect
        import tools.solver as solver_module
        source = inspect.getsource(solver_module)
        # Strip the module docstring (which explains the rule) so we only
        # check the actual code and comments.
        source = source.split('"""')[2:]
        source = "".join(source)
        self.assertNotIn("case.truth", source)
        self.assertNotIn(".truth.", source)

    def test_solver_actions_replay_cleanly(self):
        """The action log the solver produces is a valid recorded solution:
        replaying it against the same seed reaches CASE CLOSED."""
        seed = 48291
        case = generate_case(seed)
        won, actions = solver.solve(case, seed)
        self.assertTrue(won)
        self.assertIn(f"accuse {case.truth.killer}", actions)

        state = GameState(seed=seed, current_location=case.location_graph.names()[0])
        replay_engine = Engine(generate_case(seed), state, record=False)
        for action in actions:
            stop = replay_engine.process_line(action)
            if stop:
                break
        self.assertTrue(replay_engine.state.won)
        self.assertTrue(replay_engine.state.game_over)


if __name__ == "__main__":
    unittest.main()