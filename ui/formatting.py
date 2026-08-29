"""Small text formatting helpers used by the terminal UI."""

import shutil
import textwrap


def terminal_width(default: int = 78) -> int:
    try:
        return max(60, min(shutil.get_terminal_size((default, 24)).columns, 100))
    except Exception:
        return default


def wrap(text: str, width: int = None) -> str:
    width = width or terminal_width()
    return "\n".join(textwrap.wrap(text, width=width)) or ""


def bullet_list(items) -> str:
    return "\n".join(f"  - {item}" for item in items)
