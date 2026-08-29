"""
Structured data models for facts and evidence.

Representing information as structured Fact objects (rather than free
text) is what lets the contradiction engine reason about the case instead
of doing string comparison. See build spec section 9.
"""

from dataclasses import dataclass, field
from typing import Optional, List


def format_time(minutes: int) -> str:
    """Convert minutes-since-midnight to an HH:MM display string."""
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}"


def parse_time(text: str) -> int:
    """Convert an HH:MM string to minutes-since-midnight."""
    h, m = text.split(":")
    return int(h) * 60 + int(m)


@dataclass
class Fact:
    """
    A single structured claim about the world.

    subject:     who/what the fact is about (usually a suspect's name)
    property:    the kind of claim ("location", "action", "relationship", ...)
    value:       the claimed value (e.g. a location name)
    start_time:  minutes-since-midnight the fact begins to hold (or None)
    end_time:    minutes-since-midnight the fact stops holding (or None)
    source:      where this fact came from ("evidence:17", "statement:Alice", "truth")
    reliability: 0.0-1.0 confidence in the fact (evidence can be unreliable)
    """
    subject: str
    property: str
    value: str
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    source: str = "unknown"
    reliability: float = 1.0

    def overlaps(self, other: "Fact") -> bool:
        """Whether this fact's time window overlaps another's."""
        if self.start_time is None or other.start_time is None:
            return False
        a_end = self.end_time if self.end_time is not None else self.start_time
        b_end = other.end_time if other.end_time is not None else other.start_time
        return self.start_time <= b_end and other.start_time <= a_end

    def describe(self) -> str:
        when = ""
        if self.start_time is not None and self.end_time is not None:
            when = f" from {format_time(self.start_time)} to {format_time(self.end_time)}"
        elif self.start_time is not None:
            when = f" at {format_time(self.start_time)}"
        return f"{self.subject} — {self.property}: {self.value}{when}"


@dataclass
class Evidence:
    """A discoverable piece of evidence tying facts to the physical world."""
    id: str
    type: str
    location: str
    description: str
    facts: List[Fact] = field(default_factory=list)
    reliability: float = 1.0
    discover_condition: dict = field(default_factory=dict)
    discovered: bool = False
    is_red_herring: bool = False
    resolution_note: Optional[str] = None  # explains a red herring once resolved

    def reveal_text(self) -> str:
        lines = [f"Evidence #{self.id}", f"Type: {self.type.replace('_', ' ').title()}",
                 f"Location: {self.location}", self.description]
        for f in self.facts:
            lines.append("  " + f.describe())
        return "\n".join(lines)
