"""
Terminal UI (build spec section 18).

Uses only sys, ANSI escape sequences, textwrap, and shutil - no
colorama, no rich. Degrades gracefully: if a terminal doesn't support
ANSI colors the box-drawing characters and plain text still render fine.
"""

import sys
from ui.formatting import terminal_width

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
CYAN = "\x1b[36m"
YELLOW = "\x1b[33m"
RED = "\x1b[31m"
GREEN = "\x1b[32m"

_COLOR_ENABLED = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if not _COLOR_ENABLED:
        return text
    return f"{code}{text}{RESET}"


def cyan(text):
    return _c(CYAN, text)


def yellow(text):
    return _c(YELLOW, text)


def red(text):
    return _c(RED, text)


def green(text):
    return _c(GREEN, text)


def bold(text):
    return _c(BOLD, text)


def dim(text):
    return _c(DIM, text)


def print_banner():
    print(bold(cyan("=" * 44)))
    print(bold(cyan("        THE LAST DETECTIVE")))
    print(bold(cyan("=" * 44)))


def print_status_box(case, state, discovered_count: int, total_count: int) -> None:
    width = min(terminal_width(), 60)
    inner = width - 2
    lines = [
        "THE LAST DETECTIVE",
        "-" * inner,
        f"CASE #{case.case_id}",
        "",
        f"Victim: {case.victim_name}",
        f"Location: {state.current_location}",
        "",
        f"Suspects: {len(case.suspects)}",
        f"Evidence discovered: {discovered_count} / {total_count}",
        "",
        "> ",
    ]
    top = "+" + "-" * inner + "+"
    print(cyan(top))
    for line in lines:
        print(cyan("|") + f" {line}".ljust(inner) + cyan("|"))
    print(cyan("+" + "-" * inner + "+"))
