"""Personality traits that drive interrogation dialogue selection."""

from dataclasses import dataclass


@dataclass
class Personality:
    honesty: float     # 0.0 (habitual liar) - 1.0 (always truthful)
    fear: float         # 0.0 (calm) - 1.0 (terrified)
    knowledge: float    # 0.0 (knows little) - 1.0 (knows a great deal)

    def describe(self) -> str:
        def band(v, low_word, mid_word, high_word):
            if v < 0.34:
                return low_word
            if v < 0.67:
                return mid_word
            return high_word

        h = band(self.honesty, "evasive", "guarded", "candid")
        f = band(self.fear, "composed", "uneasy", "visibly shaken")
        return f"{h}, {f}"
