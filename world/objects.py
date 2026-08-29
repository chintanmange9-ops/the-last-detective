"""Examinable objects (build spec section 13 / 8)."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class WorldObject:
    name: str
    location: str
    examine_text: str
    evidence_id: Optional[str] = None  # examining this may reveal evidence
