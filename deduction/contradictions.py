"""
Contradiction Engine (build spec section 10).

Compares a suspect's *claimed* facts (their statement / alibi) against
*evidenced* facts (derived from discovered evidence, the timeline, and
location constraints) and reports structured contradictions. The engine
never announces who the killer is - it only reports that two facts don't
fit together. It is up to the player to draw conclusions.
"""

from dataclasses import dataclass
from typing import List, Optional
from evidence.models import Fact


CATEGORY_TEMPORAL = "temporal"
CATEGORY_LOCATION = "location"
CATEGORY_ACCESS = "access"
CATEGORY_IDENTITY = "identity"
CATEGORY_RELATIONSHIP = "relationship"


@dataclass
class Contradiction:
    category: str
    claim: Fact
    fact: Fact
    description: str


def _temporal_or_location(claim: Fact, fact: Fact) -> Optional[Contradiction]:
    """Claimed and evidenced whereabouts overlap in time but disagree
    on location. If the evidenced fact is a single instant inside the
    claimed window, we call it a location contradiction (a precise,
    unambiguous "you were seen elsewhere at this exact minute"). If both
    are ranges, we call it a temporal contradiction (the claimed window
    overlaps a time when evidence puts them elsewhere)."""
    if claim.subject != fact.subject:
        return None
    if claim.property != "location" or fact.property != "location":
        return None
    if claim.value == fact.value:
        return None
    if not claim.overlaps(fact):
        return None
    if fact.start_time == fact.end_time or fact.end_time is None:
        return Contradiction(
            CATEGORY_LOCATION, claim, fact,
            f"{claim.subject} claimed to be in {claim.value} at that time, "
            f"but evidence places them in {fact.value} instead.",
        )
    return Contradiction(
        CATEGORY_TEMPORAL, claim, fact,
        f"{claim.subject}'s claimed timeframe in {claim.value} overlaps a "
        f"time when evidence shows them in {fact.value}.",
    )


def _access(claim: Fact, fact: Fact) -> Optional[Contradiction]:
    """The suspect's statement never mentions a location that an access
    record proves they entered."""
    if claim.subject != fact.subject:
        return None
    if fact.property != "access":
        return None
    if fact.value == claim.value:
        return None
    return Contradiction(
        CATEGORY_ACCESS, claim, fact,
        f"{claim.subject} never mentioned visiting {fact.value}, but an "
        f"access record shows they entered it.",
    )


def _identity(claim: Fact, fact: Fact) -> Optional[Contradiction]:
    if claim.subject != fact.subject:
        return None
    if claim.property != "identity" or fact.property != "identity":
        return None
    if claim.value == fact.value:
        return None
    return Contradiction(
        CATEGORY_IDENTITY, claim, fact,
        f"{claim.subject}'s account of who was present doesn't match "
        f"what the evidence shows.",
    )


def _relationship(claim: Fact, fact: Fact) -> Optional[Contradiction]:
    if claim.subject != fact.subject:
        return None
    if claim.property != "relationship" or fact.property != "relationship":
        return None
    if claim.value == fact.value:
        return None
    return Contradiction(
        CATEGORY_RELATIONSHIP, claim, fact,
        f"{claim.subject} described their relationship to the victim as "
        f"'{claim.value}', but evidence suggests '{fact.value}'.",
    )


_DETECTORS = (_temporal_or_location, _access, _identity, _relationship)


def find_contradictions(claims: List[Fact], facts: List[Fact]) -> List[Contradiction]:
    """Compare every claim against every fact and return all contradictions found."""
    results: List[Contradiction] = []
    for claim in claims:
        for fact in facts:
            for detector in _DETECTORS:
                hit = detector(claim, fact)
                if hit is not None:
                    results.append(hit)
    return results
