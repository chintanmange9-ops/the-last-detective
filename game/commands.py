"""
Player commands (build spec section 4).

`execute()` is the single entry point used by both the interactive game
loop and the replay system, so recorded replays exercise exactly the same
code path as live play.
"""

from typing import Tuple

from evidence import system as evidence_system
from characters import interrogation
from ui.formatting import bullet_list
from ui.terminal import bold, yellow, red, green, dim, cyan


HELP_TEXT = """Available commands:
  new                     Start a new generated case (only via CLI restart)
  inspect <location>      Inspect a location
  examine <target>        Examine collected evidence or an object at your location
  suspects                List suspects
  question <name>         Interrogate a suspect
  present <evidence id>   Present evidence to the suspect you're questioning
  <category>              While questioning: location/timeline/victim/other/
                          evidence/motive/relationship/weapon
  done                    Stop questioning the current suspect
  timeline                Review the known (visible) timeline
  evidence                List discovered evidence
  notes                   View detective notes
  note <text>             Add a detective note
  map                     Show the location graph
  status                  Show case/player status
  accuse <name>           Accuse a suspect
  save <file>             Save game
  load <file>             Load game
  help                    Show this help
  quit                    Exit
"""


def _find_suspect(case, name: str):
    name_lower = name.strip().lower()
    for sname, suspect in case.suspects.items():
        if sname.lower() == name_lower:
            return suspect
    return None


def _find_evidence(case, token: str):
    token = token.strip()
    if token in case.evidence:
        ev = case.evidence[token]
        return ev if ev.discovered else None
    token_lower = token.lower()
    for ev in case.evidence.values():
        if ev.discovered and (ev.id == token_lower or token_lower in ev.description.lower()):
            return ev
    return None


def cmd_inspect(case, state, args) -> str:
    if not args:
        return red("Inspect where? Try: inspect <location>")
    location = " ".join(args).strip().title()
    loc = case.location_graph.get(location)
    if loc is None:
        return red(f"You don't know a location called '{location}'.")
    if not case.location_graph.is_connected(state.current_location, location) and location != state.current_location:
        return red(f"You can't get to {location} directly from {state.current_location}. Try 'map'.")

    state.current_location = location
    newly = evidence_system.discover_by_location(case, location)
    lines = [bold(f"You are now in the {location}."), loc.flavor]
    if loc.objects:
        lines.append("Objects here: " + ", ".join(loc.objects))
    if loc.connections:
        lines.append("Connected to: " + ", ".join(loc.connections))
    for ev in newly:
        lines.append(green(f"You found evidence #{ev.id}!"))
        lines.append(dim(ev.reveal_text()))
    return "\n".join(lines)


def cmd_examine(case, state, args) -> str:
    if not args:
        return red("Examine what?")
    target = " ".join(args)

    ev = _find_evidence(case, target)
    if ev is not None:
        return ev.reveal_text()

    obj = evidence_system.find_object(case, state.current_location, target)
    if obj is None:
        return red(f"There's nothing here called '{target}'.")

    lines = [obj.examine_text]
    newly = evidence_system.discover_by_object(case, state.current_location, target)
    for found in newly:
        lines.append(green(f"You found evidence #{found.id}!"))
        lines.append(dim(found.reveal_text()))
    if not newly:
        lines.append(dim("Nothing further of interest."))
    return "\n".join(lines)


def cmd_suspects(case, state, args) -> str:
    lines = [bold("Suspects:")]
    for name, s in case.suspects.items():
        lines.append(f"  {name} - {s.role}, {s.relationship_to_victim} of the victim. "
                      f"Mood: {s.interrogation.mood}. Demeanor: {s.personality.describe()}.")
    return "\n".join(lines)


def cmd_question(case, state, args) -> str:
    if not args:
        return red("Question who? Try: question <name>")
    name = " ".join(args)
    suspect = _find_suspect(case, name)
    if suspect is None:
        return red(f"There's no suspect named '{name}'.")
    state.current_suspect = suspect.name
    return (f'{bold("You begin questioning " + suspect.name + ".")}\n'
            f"Ask about: location, timeline, victim, other, evidence, motive, relationship, weapon.\n"
            f"Or 'present <evidence id>'. Type 'done' to stop.")


def cmd_category(case, state, category: str) -> str:
    if not state.current_suspect:
        return red("You're not questioning anyone. Try 'question <name>' first.")
    suspect = case.suspects[state.current_suspect]
    return interrogation.ask(case, suspect, category)


def cmd_present(case, state, args) -> str:
    if not state.current_suspect:
        return red("You're not questioning anyone. Try 'question <name>' first.")
    if not args:
        return red("Present what? Try: present <evidence id>")
    token = args[0]
    ev = _find_evidence(case, token)
    if ev is None:
        return red("You haven't discovered that evidence yet.")
    suspect = case.suspects[state.current_suspect]
    response = interrogation.present_evidence(case, suspect, ev)
    prefix = yellow(f"You present evidence #{ev.id} to {suspect.name}.")
    return prefix + "\n" + response


def cmd_timeline(case, state, args) -> str:
    events = case.timeline.sorted_events(include_hidden=False)
    if not events:
        return dim("Nothing is known about the timeline yet.")
    lines = [bold("Known timeline:")]
    for e in events:
        lines.append("  " + e.describe())
    return "\n".join(lines)


def cmd_evidence(case, state, args) -> str:
    discovered = evidence_system.discovered_evidence(case)
    if not discovered:
        return dim("You haven't discovered any evidence yet.")
    lines = [bold(f"Discovered evidence ({len(discovered)}/{len(case.evidence)}):")]
    for ev in sorted(discovered, key=lambda e: int(e.id)):
        lines.append(f"  #{ev.id} [{ev.type}] {ev.location} - {ev.description}")
    return "\n".join(lines)


def cmd_notes(case, state, args) -> str:
    if args and args[0].lower() != "add":
        text = " ".join(args)
        state.add_note(text)
        return green("Note added.")
    if not state.notes:
        return dim("No notes yet. Try: note <text>")
    lines = [bold("Detective notes:")]
    lines.extend(f"  {i+1}. {n}" for i, n in enumerate(state.notes))
    return "\n".join(lines)


def cmd_note(case, state, args) -> str:
    if not args:
        return red("Note what? Try: note <text>")
    state.add_note(" ".join(args))
    return green("Note added.")


def cmd_map(case, state, args) -> str:
    lines = [bold("Location map:")]
    for name, loc in case.location_graph.locations.items():
        marker = " (you are here)" if name == state.current_location else ""
        lines.append(f"  {name}{marker} -> {', '.join(loc.connections) if loc.connections else '(dead end)'}")
    return "\n".join(lines)


def cmd_status(case, state, args) -> str:
    discovered = len(evidence_system.discovered_evidence(case))
    lines = [
        bold(f"Case #{case.case_id}"),
        f"Victim: {case.victim_name} ({case.victim_role})",
        f"Your location: {state.current_location}",
        f"Currently questioning: {state.current_suspect or '(no one)'}",
        f"Evidence discovered: {discovered}/{len(case.evidence)}",
        f"Notes: {len(state.notes)}",
        f"Accusations made: {len(state.accusation_attempts)}",
    ]
    return "\n".join(lines)


def cmd_accuse(case, state, args) -> Tuple[str, bool]:
    """Returns (message, ends_game)."""
    if not args:
        return red("Accuse who? Try: accuse <name>"), False
    name = " ".join(args)
    suspect = _find_suspect(case, name)
    if suspect is None:
        return red(f"There's no suspect named '{name}'."), False

    state.accusation_attempts.append(suspect.name)
    correct = case.truth.matches_accusation(suspect.name)
    state.game_over = True
    state.won = correct

    from evidence.models import format_time
    if correct:
        lines = [
            bold(green("CASE CLOSED - You got it right.")),
            f"Killer: {case.truth.killer}",
            f"Motive: {case.truth.motive}",
            f"Weapon: {case.truth.weapon}",
            f"Location: {case.truth.location}",
            f"Time: {format_time(case.truth.time)}",
        ]
        presented = case.suspects[case.truth.killer].interrogation.evidence_presented
        if presented:
            lines.append("Evidence used against them: #" + ", #".join(presented))
    else:
        lines = [
            bold(red("CASE FAILED.")),
            f"{suspect.name} was not the killer.",
            f"The real killer was {case.truth.killer}, who used the {case.truth.weapon} "
            f"in the {case.truth.location} at {format_time(case.truth.time)}, over {case.truth.motive}.",
        ]
    return "\n".join(lines), True


CATEGORY_WORDS = {"location", "timeline", "victim", "other", "evidence",
                   "motive", "relationship", "weapon"}


def execute(line: str, case, state) -> Tuple[str, bool]:
    """Execute one command line. Returns (output, should_quit)."""
    line = line.strip()
    if not line:
        return "", False

    parts = line.split()
    cmd = parts[0].lower()
    args = parts[1:]

    if cmd in ("quit", "exit"):
        return dim("Farewell, detective."), True
    if cmd == "help":
        return HELP_TEXT, False
    if cmd == "inspect":
        return cmd_inspect(case, state, args), False
    if cmd == "examine":
        return cmd_examine(case, state, args), False
    if cmd == "suspects":
        return cmd_suspects(case, state, args), False
    if cmd == "question":
        return cmd_question(case, state, args), False
    if cmd == "present":
        return cmd_present(case, state, args), False
    if cmd == "timeline":
        return cmd_timeline(case, state, args), False
    if cmd == "evidence":
        return cmd_evidence(case, state, args), False
    if cmd == "notes":
        return cmd_notes(case, state, args), False
    if cmd == "note":
        return cmd_note(case, state, args), False
    if cmd == "map":
        return cmd_map(case, state, args), False
    if cmd == "status":
        return cmd_status(case, state, args), False
    if cmd == "accuse":
        return cmd_accuse(case, state, args)
    if cmd == "done":
        if state.current_suspect:
            name = state.current_suspect
            state.current_suspect = None
            return dim(f"You stop questioning {name}."), False
        return dim("You're not questioning anyone."), False
    if cmd in CATEGORY_WORDS:
        return cmd_category(case, state, cmd), False

    return red(f"Unknown command '{cmd}'. Type 'help' for a list of commands."), False
