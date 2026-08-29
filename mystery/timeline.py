"""
Timeline engine (build spec section 7).

Events are structured data, not text, so the game can sort them, query
them by actor/location, and check time ranges programmatically.
"""

from dataclasses import dataclass
from typing import List, Optional
from evidence.models import format_time


@dataclass
class Event:
    time: int  # minutes since midnight
    actor: str
    location: str
    action: str
    visibility: str = "visible"  # "visible" or "hidden"
    detail: str = ""

    def describe(self) -> str:
        prefix = f"{format_time(self.time)} "
        if self.detail:
            return prefix + self.detail
        return prefix + f"{self.actor} {self.action} at {self.location}"


class Timeline:
    """Container for all events in a case (both visible and hidden)."""

    def __init__(self):
        self._events: List[Event] = []

    def add(self, event: Event) -> None:
        self._events.append(event)

    def all_events(self) -> List[Event]:
        return list(self._events)

    def sorted_events(self, include_hidden: bool = False) -> List[Event]:
        events = self._events if include_hidden else [e for e in self._events if e.visibility == "visible"]
        return sorted(events, key=lambda e: e.time)

    def by_actor(self, actor: str, include_hidden: bool = False) -> List[Event]:
        return [e for e in self.sorted_events(include_hidden) if e.actor == actor]

    def by_location(self, location: str, include_hidden: bool = False) -> List[Event]:
        return [e for e in self.sorted_events(include_hidden) if e.location == location]

    def in_range(self, start: int, end: int, include_hidden: bool = False) -> List[Event]:
        return [e for e in self.sorted_events(include_hidden) if start <= e.time <= end]

    def actors(self) -> List[str]:
        seen = []
        for e in self._events:
            if e.actor not in seen:
                seen.append(e.actor)
        return seen
