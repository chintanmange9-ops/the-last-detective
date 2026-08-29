"""
Interrogation system (build spec section 12).

All dialogue is generated from deterministic templates - there is no
external LLM/API call at runtime. Phrasing is chosen with a small
per-question Random instance seeded from (case seed, suspect, category,
ordinal) so that the *same* sequence of actions on the *same* seed always
produces the *same* dialogue (needed for save/replay fidelity), while
different questions/suspects/seeds naturally vary.
"""

import random
from dataclasses import dataclass
from typing import Optional, List

from characters.suspect import Suspect
from deduction.contradictions import find_contradictions
from evidence.models import Evidence

CATEGORIES = ["location", "timeline", "victim", "other", "evidence",
              "motive", "relationship", "weapon"]

CONFESSION_THRESHOLD = 2  # distinct pieces of conflicting evidence needed


def _rng_for(case_seed, suspect_name, category, ordinal) -> random.Random:
    from mystery.data import combine_seed
    return random.Random(combine_seed(case_seed, suspect_name, category, ordinal))


def _mood_escalate(current: str) -> str:
    order = ["calm", "defensive", "angry", "afraid", "cornered"]
    idx = order.index(current) if current in order else 0
    return order[min(idx + 1, len(order) - 1)]


def ask(case, suspect: Suspect, category: str) -> str:
    """Handle a non-evidence interrogation question."""
    category = category.lower()
    ordinal = suspect.interrogation.topics_asked.count(category)
    suspect.interrogation.topics_asked.append(category)
    rng = _rng_for(case.seed, suspect.name, category, ordinal)

    if category == "location":
        return f'{suspect.name} says: {suspect.alibi_statement()}'

    if category == "timeline":
        options = [
            f"{suspect.name} says: \"That's really the only part of the evening I can account for clearly.\"",
            f"{suspect.name} says: \"Before and after that, I honestly wasn't watching the clock.\"",
            f"{suspect.name} says: \"You'd have to ask someone else what happened outside that window.\"",
        ]
        return rng.choice(options)

    if category == "victim":
        options = [
            f'{suspect.name} says: "It\'s a terrible loss. We worked together as {suspect.role}s, but I didn\'t know every detail of their life."',
            f'{suspect.name} says: "I still can\'t believe it happened. We weren\'t especially close."',
            f'{suspect.name} says: "I have nothing but respect for them. I don\'t know who would want to do this."',
        ]
        return rng.choice(options)

    if category == "other":
        others = [n for n in case.suspects if n != suspect.name]
        if not others:
            return f'{suspect.name} says: "There was no one else worth mentioning."'
        other = rng.choice(others)
        options = [
            f'{suspect.name} says: "{other}? I saw them around earlier, nothing unusual."',
            f'{suspect.name} says: "I try not to speculate about {other}. That wouldn\'t be fair."',
            f'{suspect.name} says: "Ask {other} yourself. I only know what I saw."',
        ]
        return rng.choice(options)

    if category == "evidence":
        return f'{suspect.name} says: "If you have something to show me, go ahead. I\'ll explain whatever I can."'

    if category == "motive":
        if suspect.is_killer:
            options = [
                f'{suspect.name} says: "Motive? I had no reason at all. This is absurd."',
                f'{suspect.name} says: "I don\'t see why you\'d even ask me that."',
            ]
        else:
            options = [
                f'{suspect.name} says: "I had no reason to want them harmed."',
                f'{suspect.name} says: "Whatever disagreements we had were minor."',
            ]
        return rng.choice(options)

    if category == "relationship":
        return f'{suspect.name} says: "My relationship to them was that of a {suspect.relationship_to_victim}."'

    if category == "weapon":
        options = [
            f'{suspect.name} says: "I wouldn\'t know the first thing about that."',
            f'{suspect.name} says: "That\'s not something I keep track of."',
        ]
        return rng.choice(options)

    return f'{suspect.name} looks at you, unsure what you\'re asking.'


def _conflicting_evidence_ids(case, suspect: Suspect) -> List[str]:
    claim = [suspect.alibi_fact()]
    ids = []
    for eid in suspect.interrogation.evidence_presented:
        ev = case.evidence.get(eid)
        if ev is None or ev.is_red_herring:
            continue
        if find_contradictions(claim, ev.facts):
            ids.append(eid)
    return ids


def present_evidence(case, suspect: Suspect, evidence: Evidence) -> str:
    """Handle presenting a discovered piece of evidence to a suspect."""
    if evidence.id not in suspect.interrogation.evidence_presented:
        suspect.interrogation.evidence_presented.append(evidence.id)

    if evidence.is_red_herring:
        note = evidence.resolution_note or "There's a perfectly reasonable explanation."
        return f'{suspect.name} says: "Oh, that. {note}"'

    claim = [suspect.alibi_fact()]
    contradictions = find_contradictions(claim, evidence.facts)

    if not contradictions:
        return f'{suspect.name} says: "That doesn\'t change anything I told you."'

    suspect.interrogation.mood = _mood_escalate(suspect.interrogation.mood)
    conflicting_ids = _conflicting_evidence_ids(case, suspect)

    if suspect.is_killer and len(conflicting_ids) >= CONFESSION_THRESHOLD:
        suspect.interrogation.confessed = True
        suspect.interrogation.mood = "cornered"
        from evidence.models import format_time
        return (
            f'{suspect.name} goes quiet, then says: "...Fine. You\'re right. I was in the '
            f'{case.truth.location} at {format_time(case.truth.time)}. It was me. '
            f'I used the {case.truth.weapon}. It was about {case.truth.motive}. '
            f'I never meant for it to go this far."'
        )

    ordinal = len(conflicting_ids)
    rng = _rng_for(case.seed, suspect.name, "confront", ordinal)
    mood = suspect.interrogation.mood
    if mood == "defensive":
        options = [
            f'{suspect.name} stiffens. "That... doesn\'t mean what you think it means."',
            f'{suspect.name} says: "There has to be some mistake in that record."',
        ]
    elif mood == "angry":
        options = [
            f'{suspect.name} snaps: "Are you accusing me of something? Choose your words carefully."',
            f'{suspect.name} says sharply: "I don\'t appreciate being cornered like this."',
        ]
    elif mood == "afraid":
        options = [
            f'{suspect.name}\'s hands shake. "I... I can explain. Just give me a moment."',
            f'{suspect.name} says quietly: "This isn\'t what it looks like. Please."',
        ]
    else:
        options = [
            f'{suspect.name} hesitates. "Alright, maybe I wasn\'t exactly where I said."',
            f'{suspect.name} says: "Fine - I moved around more than I let on. That\'s all."',
        ]
    return rng.choice(options)
