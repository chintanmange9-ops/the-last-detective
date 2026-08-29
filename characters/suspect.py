"""Suspect model (build spec section 11)."""

from dataclasses import dataclass, field
from typing import List, Optional
from characters.personality import Personality
from evidence.models import Fact


@dataclass
class InterrogationState:
    """Tracks what has happened between the player and this suspect."""
    topics_asked: List[str] = field(default_factory=list)
    evidence_presented: List[str] = field(default_factory=list)
    confessed: bool = False
    mood: str = "calm"  # calm, defensive, angry, afraid, cornered


@dataclass
class Suspect:
    name: str
    role: str
    personality: Personality
    relationship_to_victim: str
    is_killer: bool  # HIDDEN - never surfaced directly to the UI layer
    motive_possibility: str
    alibi_location: str
    alibi_start: int
    alibi_end: int
    known_facts: List[Fact] = field(default_factory=list)   # what they'll truthfully reveal
    secret_facts: List[Fact] = field(default_factory=list)  # only revealed under pressure
    interrogation: InterrogationState = field(default_factory=InterrogationState)

    @property
    def truthfulness(self) -> float:
        return self.personality.honesty

    def alibi_statement(self) -> str:
        from evidence.models import format_time
        return (f'"I was in the {self.alibi_location} from '
                f'{format_time(self.alibi_start)} to {format_time(self.alibi_end)}."')

    def alibi_fact(self) -> Fact:
        """The suspect's *claimed* whereabouts, as a structured Fact.

        NOTE: for the killer (and any suspect with a low-honesty lie
        pinned to their alibi) this claim may not match the ground-truth
        facts produced by evidence - that gap is exactly what the
        contradiction engine is meant to surface.
        """
        return Fact(
            subject=self.name,
            property="location",
            value=self.alibi_location,
            start_time=self.alibi_start,
            end_time=self.alibi_end,
            source=f"statement:{self.name}",
            reliability=self.personality.honesty,
        )
