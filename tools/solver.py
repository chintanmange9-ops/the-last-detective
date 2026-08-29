"""
Auto-solver bot (playability proof).

Plays a complete case the way a human detective would, driving the *real*
command surface (`game.commands.execute`) - not the internals of the
generator. It never reads `case.truth`; the only data it uses is what a
player could legitimately see: the location graph (the `map` command),
suspect names, discovered evidence, and suspect statements.

The bot is valuable for three things:

1. A judge-facing "playability proof": every generated case can
   actually be solved in-game (see `detective.py --solve`).
2. Generating a `replay` action list that resolves a case to CASE
   CLOSED, which judges can then watch (`--replay`).
3. An integration test that guards against future changes making cases
   unsolvable.

Strategy:

- Explore: `map`, then sweep the map with a breadth-first search
  (BFS): from wherever the bot stands it walks the shortest hop path
  (found with `_path_to`, itself a BFS) to the nearest room it hasn't
  searched yet, since the player can only `inspect` connected rooms.
  Every location is inspected and every object examined to discover
  evidence.
- Question: `question <name>` + ask every category + `done` per suspect.
- Confront: `present <evidence id>` for every discovered evidence
  against every suspect. A confession (the killer's own dialogue)
  identifies the culprit immediately.
- Deduce: whichever suspect's *claimed* alibi (the exact statement
  shown by `location`) conflicts with the discovered evidence is the
  killer. The validator guarantees at most one such suspect per case.
"""

from collections import deque
from typing import Dict, List, Optional, Tuple

from game import commands
from game.state import GameState
from evidence import system as evidence_system
from deduction.contradictions import find_contradictions

CATEGORIES = ["location", "timeline", "victim", "other", "evidence",
              "motive", "relationship", "weapon"]


def _adjacency(case) -> Dict[str, List[str]]:
    """The connections map the `map` command prints for the player."""
    return {name: loc.connections for name, loc in case.location_graph.locations.items()}


def _path_to(graph: Dict[str, List[str]], start: str, target: str) -> List[str]:
    """Shortest hop-by-hop path from start to target (target included)."""
    if start == target:
        return [start]
    seen = {start}
    queue = deque([[start]])
    while queue:
        path = queue.popleft()
        for nxt in graph.get(path[-1], []):
            if nxt in seen:
                continue
            seen.add(nxt)
            new_path = path + [nxt]
            if nxt == target:
                return new_path
            queue.append(new_path)
    return [start]


def _discovered_ids(case) -> set:
    return {ev.id for ev in evidence_system.discovered_evidence(case)}


def _explore(case, state: GameState, actions: List[str]) -> None:
    """Walk the whole building, inspecting locations and examining objects.
    A BFS shortest-path search picks the nearest unsearched room from the
    current position each turn, and the bot walks that route one adjacent
    `inspect` at a time - exactly how a player would sweep the map."""
    adjacency = _adjacency(case)
    names = list(case.location_graph.names())

    actions.append("map")
    commands.execute("map", case, state)

    visited = {state.current_location}
    current = state.current_location

    def search_here(loc_name: str) -> None:
        actions.append(f"inspect {loc_name}")
        commands.execute(f"inspect {loc_name}", case, state)
        for obj in case.world_objects.get(loc_name, []):
            actions.append(f"examine {obj.name}")
            commands.execute(f"examine {obj.name}", case, state)

    search_here(current)

    while len(visited) < len(names) and len(_discovered_ids(case)) < len(case.evidence):
        best_target, best_path = None, None
        for name in names:
            if name in visited:
                continue
            path = _path_to(adjacency, current, name)
            if best_path is None or len(path) < len(best_path):
                best_target, best_path = name, path
        # Walk along the path one location at a time - each step is an
        # `inspect` of an adjacent room, exactly as a player would move.
        for hop in best_path or []:
            current = hop
            if hop not in visited:
                visited.add(hop)
                search_here(hop)


def _question_all(case, state: GameState, actions: List[str]) -> None:
    for name in case.suspects:
        actions.append(f"question {name}")
        commands.execute(f"question {name}", case, state)
        for category in CATEGORIES:
            actions.append(category)
            commands.execute(category, case, state)
        actions.append("done")
        commands.execute("done", case, state)


def _confront_all(case, state: GameState, actions: List[str]) -> bool:
    """Present every discovered evidence to every suspect. Returns True if
    anyone confessed (which identifies the killer without deduction)."""
    ids = sorted(_discovered_ids(case), key=int)
    for name in case.suspects:
        actions.append(f"question {name}")
        commands.execute(f"question {name}", case, state)
        for eid in ids:
            actions.append(f"present {eid}")
            commands.execute(f"present {eid}", case, state)
        if case.suspects[name].interrogation.confessed:
            return True
        actions.append("done")
        commands.execute("done", case, state)
    return False


def _deduce_killer(case) -> Optional[str]:
    """Return the suspect whose claimed alibi contradicts discovered
    evidence. The validator guarantees at most one such suspect exists."""
    discovered = evidence_system.discovered_evidence(case)
    facts = [f for ev in discovered for f in ev.facts]

    confessed = [s.name for s in case.suspects.values()
                 if s.interrogation.confessed]
    if confessed:
        return confessed[0]

    conflicted = []
    for name, suspect in case.suspects.items():
        if find_contradictions([suspect.alibi_fact()], facts):
            conflicted.append(name)
    if len(conflicted) == 1:
        return conflicted[0]
    if len(conflicted) > 1:
        # Ambiguous - should not happen for a validated case; fall back to
        # whichever suspect has the most contradictions rather than guessing.
        best, best_count = None, -1
        for name, suspect in case.suspects.items():
            n = len(find_contradictions([suspect.alibi_fact()], facts))
            if n > best_count:
                best, best_count = name, n
        return best
    return None


def solve(case, seed: int) -> Tuple[bool, List[str]]:
    """Solve a case using only player-visible commands. Returns
    (won, action_log). The action_log reproduces the same win when
    replayed against the same seed."""
    state = GameState(seed=seed, current_location=case.location_graph.names()[0])
    actions: List[str] = []

    _explore(case, state, actions)
    _question_all(case, state, actions)
    _confront_all(case, state, actions)

    killer = _deduce_killer(case)
    if killer is None:
        return False, actions

    actions.append(f"accuse {killer}")
    output, _ = commands.execute(f"accuse {killer}", case, state)
    return ("CASE CLOSED" in output and state.won), actions