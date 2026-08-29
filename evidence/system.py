"""
Evidence system (build spec section 8).

Handles turning discover_condition descriptors on Evidence items into
actual discovery events as the player inspects locations and examines
objects. Evidence never spontaneously appears - the player has to look
for it.
"""

from typing import List
from evidence.models import Evidence


def discover_by_location(case, location: str) -> List[Evidence]:
    """Reveal any not-yet-discovered evidence whose condition is simply
    'be in this location and look around'."""
    newly = []
    for ev in case.evidence.values():
        if ev.discovered:
            continue
        cond = ev.discover_condition
        if cond.get("type") == "inspect_location" and cond.get("location") == location:
            ev.discovered = True
            newly.append(ev)
    return newly


def discover_by_object(case, location: str, obj_name: str) -> List[Evidence]:
    """Reveal evidence gated behind examining a specific object."""
    newly = []
    obj_name_lower = obj_name.strip().lower()
    for ev in case.evidence.values():
        if ev.discovered:
            continue
        cond = ev.discover_condition
        if (cond.get("type") == "examine_object"
                and cond.get("location") == location
                and cond.get("object", "").lower() == obj_name_lower):
            ev.discovered = True
            newly.append(ev)
    return newly


def discovered_evidence(case) -> List[Evidence]:
    return [ev for ev in case.evidence.values() if ev.discovered]


def find_object(case, location: str, obj_name: str):
    obj_name_lower = obj_name.strip().lower()
    for obj in case.world_objects.get(location, []):
        if obj.name.lower() == obj_name_lower:
            return obj
    return None
