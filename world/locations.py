"""Location graph (build spec section 13)."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import deque


@dataclass
class Location:
    name: str
    connections: List[str] = field(default_factory=list)
    objects: List[str] = field(default_factory=list)
    flavor: str = ""
    evidence_ids: List[str] = field(default_factory=list)  # evidence discoverable here


class LocationGraph:
    def __init__(self):
        self.locations: Dict[str, Location] = {}

    def add(self, location: Location) -> None:
        self.locations[location.name] = location

    def get(self, name: str) -> Optional[Location]:
        return self.locations.get(name)

    def names(self) -> List[str]:
        return list(self.locations.keys())

    def is_connected(self, a: str, b: str) -> bool:
        loc = self.get(a)
        return loc is not None and b in loc.connections

    def reachable_from(self, start: str) -> List[str]:
        """BFS reachability check - used by the validator to make sure
        every location a case depends on is actually accessible."""
        if start not in self.locations:
            return []
        seen = {start}
        q = deque([start])
        while q:
            cur = q.popleft()
            for nxt in self.locations[cur].connections:
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        return list(seen)

    def path_exists(self, a: str, b: str) -> bool:
        return b in self.reachable_from(a)
