"""
Replay system (build spec section 17).

Because the world is fully deterministic given a seed, replaying the same
sequence of player commands against the same seed reproduces the same
case and the same outcome.
"""

import json
from pathlib import Path
from typing import List


def save_replay(path: str, seed: int, actions: List[str]) -> None:
    data = {"version": 1, "seed": seed, "actions": actions}
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_replay(path: str):
    """Returns (seed, actions)."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return raw["seed"], list(raw.get("actions", []))
