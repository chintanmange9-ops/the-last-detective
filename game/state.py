"""
Player-visible game state (build spec section 20: keep this separate
from the hidden Truth/Case internals). This is the only object the UI
layer should read from directly for "where am I / what have I found"
questions.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class GameState:
    seed: int
    current_location: str
    current_suspect: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    accusation_attempts: List[str] = field(default_factory=list)
    action_log: List[str] = field(default_factory=list)  # for replay recording
    hints_used: int = 0
    game_over: bool = False
    won: bool = False
    turn: int = 0

    def add_note(self, text: str) -> None:
        self.notes.append(text)

    def record_action(self, raw_line: str) -> None:
        self.action_log.append(raw_line)
