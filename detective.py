#!/usr/bin/env python3
"""
The Last Detective - entry point.

    python detective.py --seed 48291
    python detective.py --load save.json
    python detective.py --replay run.json
    python detective.py --stress 2000        (developer/test command)

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


def _run_new_case(seed: int, record: bool = True) -> Engine:
    case = generate_case(seed)
    state = GameState(seed=seed, current_location=case.truth.location)
    return Engine(case, state, record=record)


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
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.stress is not None:
        return _run_stress_test(args.stress)

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
