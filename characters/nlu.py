"""
Natural-language interpretation for interrogation (build spec section 12).

Maps free-form questions the player types while questioning a suspect onto
the engine's structured category words, so phrases like "where were you?"
work exactly like the `location` keyword. Uses only the standard-library
`re` module - no ML, no third-party NLP.

Patterns are checked in priority order: more specific phrases are matched
before generic ones so that e.g. "why were you there" resolves to `motive`
(why) rather than `location` (were/where), while "where" phrases still hit
`location` via their own patterns.
"""

import re
from typing import Optional


PATTERNS = [
    (re.compile(r"\bwhere\b.*\b(?:were|was|go|going|went)\b", re.I), "location"),
    (re.compile(r"\bwhere\b.*\b(?:at|be|standing|alone)\b", re.I), "location"),
    (re.compile(r"\bwhat\b.*\blocation\b", re.I), "location"),
    (re.compile(r"\bwhat happened\b", re.I), "timeline"),
    (re.compile(r"\bwhat time\b", re.I), "timeline"),
    (re.compile(r"\btimeline\b", re.I), "timeline"),
    (re.compile(r"\bwhat (?:happened|went on|occurred)\b", re.I), "timeline"),
    (re.compile(r"\bwhy\b", re.I), "motive"),
    (re.compile(r"\bmotive\b", re.I), "motive"),
    (re.compile(r"\breason\b", re.I), "motive"),
    (re.compile(r"\b(?:intent|intention)\b", re.I), "motive"),
    (re.compile(r"\bweapon\b", re.I), "weapon"),
    (re.compile(r"\bhow did you\b.*\b(?:do|use|kill|plan|carry)\b", re.I), "weapon"),
    (re.compile(r"\b(?:knife|gun|paperweight|scalpel|candlestick|wire)\b", re.I), "weapon"),
    # "how did you know the victim" is a relationship question, not a
    # victim question - the know/verb phrasing is more specific, so it is
    # matched before the bare "victim" word below.
    (re.compile(r"\b(?:know|knew)\b.*\b(?:victim|him|her|them)\b", re.I), "relationship"),
    (re.compile(r"\bvictim\b", re.I), "victim"),
    (re.compile(r"\bdeceased\b", re.I), "victim"),
    (re.compile(r"\bwho\b.*\bkilled\b", re.I), "victim"),
    (re.compile(r"\bbody\b", re.I), "victim"),
    (re.compile(r"\brelationship\b", re.I), "relationship"),
    (re.compile(r"\b(?:friend|friends|enemy|related)\b", re.I), "relationship"),
    (re.compile(r"\banyone else\b", re.I), "other"),
    (re.compile(r"\bsomeone else\b", re.I), "other"),
    (re.compile(r"\bothers\b", re.I), "other"),
    (re.compile(r"\beveryone\b", re.I), "other"),
    (re.compile(r"\bevidence\b", re.I), "evidence"),
    (re.compile(r"\bwhat did you find\b", re.I), "evidence"),
]

SUGGESTION_LINE = (
    "I'm not sure what you're asking. Try a question like "
    "'where were you?', 'why?', 'what weapon?', 'tell me about the victim', "
    "or one of: location, timeline, victim, other, evidence, motive, "
    "relationship, weapon. Or type 'done' to stop."
)


def interpret(phrase: str) -> Optional[str]:
    """Return the interrogation category a phrase maps to, or None."""
    text = phrase.strip()
    if not text:
        return None
    for pattern, category in PATTERNS:
        if pattern.search(text):
            return category
    return None