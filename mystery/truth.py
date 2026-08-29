"""
The Truth Engine (build spec section 6).

This holds the single, authoritative answer to "what actually happened".
Nothing in the UI layer should ever read from a Truth object directly -
only the generator (to build the rest of the case) and the validator /
accusation-checker (to grade the player) are allowed to touch it.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Truth:
    killer: str
    victim: str
    weapon: str
    motive: str
    location: str
    time: int  # minutes since midnight

    def matches_accusation(self, suspect_name: str) -> bool:
        return suspect_name.strip().lower() == self.killer.strip().lower()
