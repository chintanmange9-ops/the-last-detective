"""
Save/Load system (build spec section 16).

Only json, pathlib, and dataclasses (plus other stdlib) are used - no
pickle, no third-party serialization library. Because case generation is
fully deterministic from the seed, a save file only needs to record the
*mutable* parts of the game: what has been discovered/asked/said, plus
the player's own notes and location. On load we regenerate the case from
the seed and then replay the saved mutable state on top of it.
"""

import json
from pathlib import Path
from dataclasses import asdict

from mystery.generator import generate_case, Case
from game.state import GameState


def build_save_dict(case: Case, state: GameState) -> dict:
    suspects_state = {}
    for name, suspect in case.suspects.items():
        suspects_state[name] = {
            "topics_asked": suspect.interrogation.topics_asked,
            "evidence_presented": suspect.interrogation.evidence_presented,
            "confessed": suspect.interrogation.confessed,
            "mood": suspect.interrogation.mood,
        }

    discovered_ids = [eid for eid, ev in case.evidence.items() if ev.discovered]

    return {
        "version": 1,
        "seed": case.seed,
        "case_id": case.case_id,
        "discovered_evidence": discovered_ids,
        "suspects": suspects_state,
        "state": {
            "current_location": state.current_location,
            "current_suspect": state.current_suspect,
            "notes": state.notes,
            "accusation_attempts": state.accusation_attempts,
            "action_log": state.action_log,
            "hints_used": state.hints_used,
            "game_over": state.game_over,
            "won": state.won,
            "turn": state.turn,
        },
    }


def save_game(path: str, case: Case, state: GameState) -> None:
    data = build_save_dict(case, state)
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_game(path: str):
    """Returns (case, state) reconstructed from a save file."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    seed = raw["seed"]
    case = generate_case(seed)

    for eid in raw.get("discovered_evidence", []):
        if eid in case.evidence:
            case.evidence[eid].discovered = True

    for name, sdata in raw.get("suspects", {}).items():
        suspect = case.suspects.get(name)
        if suspect is None:
            continue
        suspect.interrogation.topics_asked = list(sdata.get("topics_asked", []))
        suspect.interrogation.evidence_presented = list(sdata.get("evidence_presented", []))
        suspect.interrogation.confessed = sdata.get("confessed", False)
        suspect.interrogation.mood = sdata.get("mood", "calm")

    s = raw.get("state", {})
    state = GameState(
        seed=seed,
        current_location=s.get("current_location", case.truth.location),
        current_suspect=s.get("current_suspect"),
        notes=list(s.get("notes", [])),
        accusation_attempts=list(s.get("accusation_attempts", [])),
        action_log=list(s.get("action_log", [])),
        hints_used=s.get("hints_used", 0),
        game_over=s.get("game_over", False),
        won=s.get("won", False),
        turn=s.get("turn", 0),
    )
    return case, state
