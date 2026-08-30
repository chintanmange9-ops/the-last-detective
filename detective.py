#!/usr/bin/env python3
"""
The Last Detective - entry point.

    python detective.py --seed 48291
    python detective.py --load save.json
    python detective.py --replay run.json
    python detective.py --stress 2000        (developer/test command)
    python detective.py --solve 1000         (auto-solve seeds 0..999)
    python detective.py --solve 1000-1100    (auto-solve just that range)
    python detective.py --solve-seed 21321   (auto-solve exactly one seed)
    python detective.py --solve-seed 21321 --solve-verbose
                                         (same, and print the revealed solution)
    python detective.py --story 21321      (print a printable case brief:
                                         a human-solvable whodunit in markdown)

Zero third-party runtime dependencies: standard library only.
"""

import argparse
import sys

from mystery.generator import generate_case
from mystery.validator import validate_case
from game.state import GameState
from game.engine import Engine
from storage import save as save_module
from storage import replay as replay_module
from tools import solver


def _run_new_case(seed: int, record: bool = True) -> Engine:
    case = generate_case(seed)
    state = GameState(seed=seed, current_location=case.truth.location)
    return Engine(case, state, record=record)


def _run_solver_test(start_seed: int, count: int, label: str = "",
                     verbose: bool = False) -> int:
    """Developer command: auto-solve `count` cases with the solver bot,
    starting at `start_seed`, and report any that the bot fails to solve.
    Proof of playability. With verbose=True, also print the revealed
    solution (killer / motive / weapon / location / time / steps) for
    every case that was solved."""
    solved = 0
    for seed in range(start_seed, start_seed + count):
        case = generate_case(seed)
        won, actions = solver.solve(case, seed)
        if won:
            solved += 1
        else:
            print(f"seed {seed}: NOT SOLVED")
            continue
        if verbose:
            t = case.truth
            from evidence.models import format_time
            print(f"seed {seed}: {t.killer} | {t.motive} | {t.weapon} "
                  f"| {t.location} | {format_time(t.time)} | {len(actions)} steps")
    span = label or f"seeds {start_seed}..{start_seed + count - 1}"
    print(f"\nSolver solved {solved}/{count} cases ({span}).")
    return 0 if solved == count else 1


def _run_story(seed: int) -> int:
    """Developer command: print a printable, human-solvable case brief for
    one generated case (a whodunit in markdown). The doc doubles as a
    proof that a case is solvable from the player-visible info alone."""
    from tools import story
    case = generate_case(seed)
    print(story.build_story(case))
    return 0


def _parse_solve_spec(spec: str) -> tuple:
    """Parse the --solve argument. Accepts either a plain count N (solves
    seeds 0..N-1) or a range 'start-end' (solves exactly those seeds,
    both endpoints inclusive). Returns (start_seed, count)."""
    if "-" in spec:
        start, end = spec.split("-", 1)
        return int(start), int(end) - int(start) + 1
    count = int(spec)
    return 0, count


def _run_stress_test(count: int) -> int:
    """Developer/test command: generate `count` cases and report any
    validation failures (build spec section 15 / 23)."""
    failures = 0
    max_attempts = 0
    for seed in range(count):
        try:
            case = generate_case(seed)
        except RuntimeError as exc:
            failures += 1
            print(f"seed {seed}: FAILED - {exc}")
            continue
        result = validate_case(case)
        max_attempts = max(max_attempts, case.attempts)
        if not result.valid:
            failures += 1
            print(f"seed {seed}: INVALID after generation - {result.errors}")
    print(f"\nGenerated {count} cases. Failures: {failures}. "
          f"Max attempts needed for any single case: {max_attempts}.")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="detective.py",
        description="The Last Detective - a procedurally generated murder-mystery game.",
    )
    parser.add_argument("--seed", type=int, default=None,
                         help="Deterministic integer seed for a new case.")
    parser.add_argument("--load", type=str, default=None,
                         help="Load a saved game from the given file.")
    parser.add_argument("--replay", type=str, default=None,
                         help="Replay a recorded action file against its original seed.")
    parser.add_argument("--stress", type=int, default=None, metavar="N",
                         help="Developer command: generate N cases and report validation failures.")
    parser.add_argument("--solve", type=str, default=None, metavar="N|A-B",
                         help="Developer command: auto-solve cases with the solver bot and "
                         "report failures. N = seeds 0..N-1, or A-B = just that inclusive range.")
    parser.add_argument("--solve-seed", type=int, default=None, metavar="SEED",
                         help="Developer command: auto-solve exactly one seed with the solver bot.")
    parser.add_argument("--solve-verbose", action="store_true",
                         help="With --solve/--solve-seed: print the revealed solution "
                         "for every solved case.")
    parser.add_argument("--story", type=int, default=None, metavar="SEED",
                         help="Developer command: print a printable, human-solvable "
                         "case brief (whodunit in markdown) for one seed.")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.stress is not None:
        return _run_stress_test(args.stress)

    if args.solve is not None:
        start, count = _parse_solve_spec(args.solve)
        return _run_solver_test(start, count, label=f"spec {args.solve}",
                                verbose=args.solve_verbose)

    if args.solve_seed is not None:
        return _run_solver_test(args.solve_seed, 1,
                                label=f"single seed {args.solve_seed}",
                                verbose=args.solve_verbose)

    if args.story is not None:
        return _run_story(args.story)

    if args.replay:
        seed, actions = replay_module.load_replay(args.replay)
        engine = _run_new_case(seed, record=False)
        engine.run_replay(actions)
        return 0

    if args.load:
        try:
            case, state = save_module.load_game(args.load)
        except FileNotFoundError:
            print(f"No save file found at {args.load}.")
            return 1
        engine = Engine(case, state)
        engine.run_interactive()
        return 0

    seed = args.seed if args.seed is not None else 1
    engine = _run_new_case(seed)
    engine.run_interactive()
    return 0


if __name__ == "__main__":
    sys.exit(main())
