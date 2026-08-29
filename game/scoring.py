"""
Post-case scoring and detective rank epilogue.

Runs when a case ends (win or loss) and turns how the case was played into
a single 0-1000 score and a rank title, giving the game a light
meta-progression layer without adding any dependencies.

Score components:

- evidence ratio (0-500): how much of the case's evidence was found.
- speed (0-300): fewer commands used means a sharper investigation.
- win (200): solving the case at all pays out.
- confession (100): getting the killer to admit it directly.
- wrong accusations (-150 each).
- hints used (-75 each), so the hint command has a real cost.
"""

from evidence import system as evidence_system


RAW_WEIGHTS = {
    "evidence_ratio": 500,
    "speed": 300,
    "win": 200,
    "confession": 100,
    "wrong_accusation": -150,
    "hint": -75,
}

RANKS = [
    (900, "The Last Detective"),
    (750, "Chief Inspector"),
    (600, "Detective"),
    (400, "Inspector"),
    (0, "Apprentice"),
]


def case_score(case, state, won: bool) -> int:
    total = len(case.evidence)
    discovered = len(evidence_system.discovered_evidence(case))
    ratio = discovered / total if total else 0.0

    score = 0
    score += ratio * RAW_WEIGHTS["evidence_ratio"]

    # Faster investigations score higher; every turn beyond the first
    # costs a little, capped so even thorough play keeps most of the pool.
    speed = max(0, RAW_WEIGHTS["speed"] - 4 * state.turn)
    score += speed

    if won:
        score += RAW_WEIGHTS["win"]

    killer = case.suspects.get(case.truth.killer)
    if killer is not None and killer.interrogation.confessed:
        score += RAW_WEIGHTS["confession"]

    wrong = 0
    if won:
        wrong = max(0, len(state.accusation_attempts) - 1)
    else:
        wrong = len(state.accusation_attempts)
    score += wrong * RAW_WEIGHTS["wrong_accusation"]

    score += state.hints_used * RAW_WEIGHTS["hint"]

    return max(0, min(1000, int(score)))


def rank_for(score: int) -> str:
    for threshold, title in RANKS:
        if score >= threshold:
            return title
    return RANKS[-1][1]


def epilogue(case, state, won: bool) -> str:
    """The closing lines shown on the case-close screen."""
    score = case_score(case, state, won)
    rank = rank_for(score)
    return (f"\nCase score: {score}/1000 - Rank: {rank}\n"
            f"Evidence found: {len(evidence_system.discovered_evidence(case))}/{len(case.evidence)}. "
            f"Turns used: {state.turn}. Wrong accusations: "
            f"{len(state.accusation_attempts) - (1 if won else 0)}. Hints used: {state.hints_used}.")