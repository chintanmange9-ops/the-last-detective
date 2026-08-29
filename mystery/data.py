"""
Static content pools used by the procedural case generator.

Keeping flavor content (names, locations, motives, weapons, etc.) separate
from generation *logic* (generator.py) makes the generator easier to read
and makes it easy to expand the pool of possible cases later without
touching the algorithm itself.
"""

import hashlib


def combine_seed(*parts) -> int:
    """Deterministically combine several values (ints/strs) into a single
    integer seed. random.Random() only accepts None/int/float/str/bytes,
    so this is how we derive reproducible sub-seeds from a tuple of
    context (e.g. (top_level_seed, attempt) or (seed, suspect, category))."""
    text = "|".join(str(p) for p in parts)
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


FIRST_NAMES = [
    "Alice", "Brian", "Claire", "Daniel", "Elena", "Franklin", "Grace",
    "Henry", "Isabel", "Jonas", "Karen", "Louis", "Miriam", "Nathan",
    "Olivia", "Patrick", "Rosa", "Simon", "Tessa", "Victor",
]

VICTIM_NAMES = [
    "Dr. Robert Anderson", "Dr. Helen Voss", "Professor Adrian Kane",
    "Mr. Walter Higgins", "Ms. Diane Cortez", "Dr. Marcus Feld",
    "Ambassador Nora Lang", "Chairman Elliot Grey",
]

VICTIM_ROLES = [
    "lead researcher", "museum curator", "company director",
    "university dean", "estate owner", "senior partner",
]

SUSPECT_ROLES = [
    "lab assistant", "business partner", "personal secretary",
    "head of security", "junior researcher", "family member",
    "housekeeper", "accountant", "rival colleague", "old friend",
]

RELATIONSHIPS_TO_VICTIM = [
    "employee", "business partner", "romantic rival", "sibling",
    "creditor", "former mentee", "estranged friend", "in-law",
    "subordinate", "long-time collaborator",
]

MOTIVES = [
    "research theft", "financial fraud", "inheritance dispute",
    "blackmail", "professional betrayal", "jealousy", "revenge",
    "silencing a whistleblower", "a broken business deal",
    "a hidden affair",
]

WEAPONS = [
    "laboratory knife", "letter opener", "blunt candlestick",
    "poisoned tea", "length of wire", "fire poker",
    "surgical scalpel", "heavy paperweight",
]

# A fixed location graph loosely matching the layout suggested in the
# build spec. Every case uses this same physical map; what varies is who
# was where, and when. Keys are canonical location names; values are the
# list of directly connected locations (reachability graph).
LOCATION_GRAPH = {
    "Library": ["Office"],
    "Office": ["Library", "Hallway"],
    "Hallway": ["Office", "Laboratory", "Cafeteria"],
    "Laboratory": ["Hallway"],
    "Cafeteria": ["Hallway", "Parking"],
    "Parking": ["Cafeteria"],
}

LOCATION_FLAVOR = {
    "Library": "Rows of quiet shelving. A single reading lamp is still on.",
    "Office": "Papers are neatly stacked; a computer screen glows on standby.",
    "Hallway": "A long corridor connecting the building's main rooms.",
    "Laboratory": "Workbenches, locked cabinets, and the smell of chemicals.",
    "Cafeteria": "A handful of tables, a coffee machine still warm.",
    "Parking": "A small lot behind the building, mostly empty at night.",
}

# Objects found at each location. Some are tied to evidence generation.
LOCATION_OBJECTS = {
    "Library": ["reading lamp", "checkout ledger"],
    "Office": ["desk computer", "appointment calendar"],
    "Hallway": ["security camera", "keycard reader"],
    "Laboratory": ["workbench", "chemical cabinet", "murder weapon"],
    "Cafeteria": ["coffee machine", "cafeteria access log"],
    "Parking": ["parking gate log"],
}

EVIDENCE_FLAVOR = {
    "access_log": "An access log records entries and exits by keycard.",
    "security_footage": "Security footage shows movement on camera.",
    "witness_statement": "A witness statement describing what someone saw.",
    "forensic": "A forensic detail recovered from the scene.",
    "document": "A document found among the victim's or a suspect's papers.",
    "phone_record": "A phone record showing calls or messages.",
}
