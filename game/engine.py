"""Game engine: ties the case, state, commands, and UI together."""

import sys

from game import commands
from game.state import GameState
from evidence import system as evidence_system
from storage import save as save_module
from storage import replay as replay_module
from ui import terminal
from mystery.generator import generate_case


class Engine:
    def __init__(self, case, state: GameState, record: bool = True):
        self.case = case
        self.state = state
        self.record = record

    def _handle_save(self, args):
        if not args:
            return terminal.red("Save where? Try: save <file>")
        path = args[0]
        save_module.save_game(path, self.case, self.state)
        return terminal.green(f"Game saved to {path}.")

    def _handle_load(self, args):
        if not args:
            return terminal.red("Load from where? Try: load <file>")
        path = args[0]
        try:
            case, state = save_module.load_game(path)
        except FileNotFoundError:
            return terminal.red(f"No save file found at {path}.")
        self.case = case
        self.state = state
        return terminal.green(f"Game loaded from {path}.")

    def process_line(self, line: str) -> bool:
        """Process one line of input. Returns True if the game should stop."""
        if self.record:
            self.state.record_action(line)
        self.state.turn += 1

        parts = line.strip().split()
        if parts and parts[0].lower() == "save":
            print(self._handle_save(parts[1:]))
            return False
        if parts and parts[0].lower() == "load":
            print(self._handle_load(parts[1:]))
            return False

        output, should_quit = commands.execute(line, self.case, self.state)
        if output:
            print(output)
        if self.state.game_over:
            return True
        return should_quit

    def print_intro(self):
        terminal.print_banner()
        total = len(self.case.evidence)
        discovered = len(evidence_system.discovered_evidence(self.case))
        terminal.print_status_box(self.case, self.state, discovered, total)
        print(terminal.dim(f"A body has been found: {self.case.victim_name}, "
                            f"{self.case.victim_role}. Somewhere in this building is the "
                            f"person responsible. Type 'help' to see what you can do."))
        print(terminal.dim("Start with 'map', then 'inspect <location>' to search rooms."))

    def run_interactive(self):
        self.print_intro()
        while True:
            try:
                line = input(terminal.cyan("\n> "))
            except (EOFError, KeyboardInterrupt):
                print()
                break
            stop = self.process_line(line)
            if stop:
                break

    def run_replay(self, actions):
        self.print_intro()
        for line in actions:
            print(terminal.cyan(f"\n> {line}"))
            stop = self.process_line(line)
            if stop:
                break
