"""
Mystery Validator (build spec section 15).

Runs a battery of consistency checks against a freshly generated case.
Deliberately does NOT import mystery.generator (that module imports this
one) - it works against duck-typed Case objects instead, so the two
modules stay decoupled.
"""

from dataclasses import dataclass, field
from typing import List
from collections import defaultdict

from deduction.contradictions import find_contradictions
from evidence.models import Fact


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str] = field(default_factory=list)


def _check_exactly_one_killer(case, errors):
    killers = [s for s in case.suspects.values() if s.is_killer]
    if len(killers) != 1:
        errors.append(f"expected exactly one killer, found {len(killers)}")
        return None
    return killers[0]


def _check_killer_is_suspect(case, killer, errors):
    if killer is None:
        return
    if killer.name not in case.suspects:
        errors.append("killer is not present in the suspect list")


def _check_victim_not_killer(case, errors):
    if case.truth.victim == case.truth.killer:
        errors.append("victim and killer must not be the same person")


def _check_weapon_and_motive(case, errors):
    if not case.truth.weapon:
        errors.append("no weapon defined")
    if not case.truth.motive:
        errors.append("no motive defined")


def _check_murder_event_exists(case, errors):
    murder_events = [e for e in case.timeline.all_events()
                      if e.action == "murder" and e.actor == case.truth.killer]
    if not murder_events:
        errors.append("no murder event found in the timeline for the killer")


def _check_opportunity(case, errors):
    loc = case.truth.location
    if loc not in case.location_graph.locations:
        errors.append(f"murder location '{loc}' does not exist in the location graph")
        return
    killer_events = [e for e in case.timeline.all_events()
                      if e.actor == case.truth.killer and e.location == loc]
    if not killer_events:
        errors.append("killer has no recorded presence at the murder location")


def _check_timeline_internal_consistency(case, errors):
    """No suspect should have two overlapping ground-truth location facts
    with different values (that would mean they were in two places at once)."""
    facts_by_subject = defaultdict(list)
    for fact in case.ground_truth_facts():
        if fact.property == "location":
            facts_by_subject[fact.subject].append(fact)

    for subject, facts in facts_by_subject.items():
        for i in range(len(facts)):
            for j in range(i + 1, len(facts)):
                a, b = facts[i], facts[j]
                if a.value != b.value and a.overlaps(b):
                    errors.append(
                        f"timeline inconsistency: {subject} appears in both "
                        f"{a.value} and {b.value} at overlapping times"
                    )


def _check_locations_reachable(case, errors):
    graph = case.location_graph
    all_names = set(graph.names())
    used_locations = set()
    for ev in case.evidence.values():
        used_locations.add(ev.location)
    used_locations.add(case.truth.location)

    unknown = used_locations - all_names
    if unknown:
        errors.append(f"evidence references unknown locations: {sorted(unknown)}")

    # Every used location must be reachable from the murder location, since
    # the map must be fully navigable during play.
    if case.truth.location in all_names:
        reachable = set(graph.reachable_from(case.truth.location))
        unreachable = (used_locations & all_names) - reachable
        if unreachable:
            errors.append(f"locations not reachable from the murder scene: {sorted(unreachable)}")


def _check_evidence_internally_consistent(case, errors):
    facts_by_subject = defaultdict(list)
    for ev in case.evidence.values():
        for fact in ev.facts:
            if fact.property == "location":
                facts_by_subject[fact.subject].append((fact, ev))

    for subject, entries in facts_by_subject.items():
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                fa, ev_a = entries[i]
                fb, ev_b = entries[j]
                if ev_a.is_red_herring or ev_b.is_red_herring:
                    continue
                if fa.value != fb.value and fa.overlaps(fb):
                    errors.append(
                        f"evidence #{ev_a.id} and #{ev_b.id} disagree about "
                        f"{subject}'s location at an overlapping time"
                    )


def _check_enough_clues(case, errors, minimum=5):
    if len(case.evidence) < minimum:
        errors.append(f"only {len(case.evidence)} evidence items generated (need at least {minimum})")


def _check_unique_solution(case, errors):
    """Exactly one suspect's claimed alibi should conflict with the
    evidence. If zero suspects conflict, the case is unsolvable; if more
    than one conflicts, the solution is ambiguous."""
    all_facts = case.ground_truth_facts()
    conflicted = set()
    for name, suspect in case.suspects.items():
        claim = [suspect.alibi_fact()]
        # Exclude facts sourced from red-herring evidence from this check -
        # those are allowed to look suspicious without being contradictions.
        non_herring_facts = [
            f for ev in case.evidence.values() if not ev.is_red_herring
            for f in ev.facts
        ]
        hits = find_contradictions(claim, non_herring_facts)
        if hits:
            conflicted.add(name)

    if len(conflicted) == 0:
        errors.append("no suspect's statement conflicts with the evidence - case is unsolvable")
    elif len(conflicted) > 1:
        errors.append(f"more than one suspect conflicts with the evidence: {sorted(conflicted)}")
    elif case.truth.killer not in conflicted:
        errors.append("the suspect who conflicts with the evidence is not the killer")


def _check_red_herrings_safe(case, errors):
    """A red herring must never itself create a location contradiction -
    it should only ever look suspicious, never actually break the timeline."""
    for ev in case.evidence.values():
        if not ev.is_red_herring:
            continue
        suspect = case.suspects.get(ev.facts[0].subject) if ev.facts else None
        if suspect is None:
            continue
        claim = [suspect.alibi_fact()]
        hits = find_contradictions(claim, ev.facts)
        if hits:
            errors.append(f"red herring evidence #{ev.id} creates a real contradiction (not allowed)")


def validate_case(case) -> ValidationResult:
    errors: List[str] = []
    killer = _check_exactly_one_killer(case, errors)
    _check_killer_is_suspect(case, killer, errors)
    _check_victim_not_killer(case, errors)
    _check_weapon_and_motive(case, errors)
    _check_murder_event_exists(case, errors)
    _check_opportunity(case, errors)
    _check_timeline_internal_consistency(case, errors)
    _check_locations_reachable(case, errors)
    _check_evidence_internally_consistent(case, errors)
    _check_enough_clues(case, errors)
    _check_unique_solution(case, errors)
    _check_red_herrings_safe(case, errors)
    return ValidationResult(valid=(len(errors) == 0), errors=errors)
