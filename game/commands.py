"""
Player commands (build spec section 4).

`execute()` is the single entry point used by both the interactive game
loop and the replay system, so recorded replays exercise exactly the same
code path as live play.
"""

import difflib
from typing import Tuple

from evidence import system as evidence_system
from characters import interrogation, nlu
from game import scoring
from ui.formatting import bullet_list
from ui.terminal import bold, yellow, red, green, dim, cyan


HELP_TEXT = """Available commands:
  new                     Start a new generated case (only via CLI restart)
  inspect <location>      Move to a location and search it for evidence
  examine <target>        Examine evidence or an object where you are
                          (locations are accepted too - treated like inspect)
  suspects                List suspects
  question <name>         Interrogate a suspect
  present <evidence id>   Present evidence to the suspect you're questioning
  <category>              While questioning: location/timeline/victim/other/
                          evidence/motive/relationship/weapon.
                          Natural-language questions also work, e.g.
                          "where were you?" or "why?".
  done                    Stop questioning the current suspect
  timeline                Review the known (visible) timeline
  evidence                List discovered evidence
  notes                   View detective notes
  note <text>             Add a detective note
  map                     Show the location graph
  status                  Show case/player status
  hint                    Get a nudge toward undiscovered evidence (costs rank)
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
        # If the target names a location the player actually knows, treat
        # "examine <location>" as "inspect <location>" - the behaviour they
        # clearly expect (move there and search it).
        target_lower = target.strip().lower()
        for loc_name in case.location_graph.names():
            if loc_name.lower() == target_lower:
                return cmd_inspect(case, state, [loc_name])
        return _examine_fallback(case, state, target)

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


def cmd_hint(case, state, args) -> str:
    """Costly nudge: point at the nearest location hiding undiscovered
    evidence. Deducts from the end-of-case rank (see game/scoring.py)."""
    if state.game_over:
        return dim("The case is already closed.")
    undiscovered = [ev for ev in case.evidence.values() if not ev.discovered]
    if not undiscovered:
        return green("You've found every piece of evidence. Accuse your prime suspect.")
    # Deterministic, player-friendly hint: the undiscovered location with
    # the lowest evidence id that you can still reach.
    target = min(undiscovered, key=lambda ev: int(ev.id))
    state.hints_used += 1
    return (yellow(f"You consult your notes: \"There's more to find around the "
                   f"{target.location}.\"")
            + dim("\n(A hint like this counts against your final rank.)"))


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
        presented = interrogation.conflicting_evidence_ids(case, case.suspects[case.truth.killer])
        if presented:
            lines.append("Evidence used against them: #" + ", #".join(presented))
    else:
        lines = [
            bold(red("CASE FAILED.")),
            f"{suspect.name} was not the killer.",
            f"The real killer was {case.truth.killer}, who used the {case.truth.weapon} "
            f"in the {case.truth.location} at {format_time(case.truth.time)}, over {case.truth.motive}.",
        ]
    lines.append(dim(scoring.epilogue(case, state, correct)))
    return "\n".join(lines), True


CATEGORY_WORDS = {"location", "timeline", "victim", "other", "evidence",
                   "motive", "relationship", "weapon"}

KNOWN_COMMANDS = {
    "new", "inspect", "examine", "suspects", "question", "present",
    "done", "timeline", "evidence", "notes", "note", "map", "status",
    "hint", "accuse", "save", "load", "help", "quit", "exit",
} | CATEGORY_WORDS


def _suggest_command(cmd: str) -> str:
    """Suggest a nearby known command for a misspelled one, if any."""
    matches = difflib.get_close_matches(cmd, KNOWN_COMMANDS, n=1, cutoff=0.6)
    if matches:
        return f"Unknown command '{cmd}'. Did you mean '{matches[0]}'?"
    return f"Unknown command '{cmd}'. Type 'help' for a list of commands."


def _examine_fallback(case, state, target: str) -> str:
    """Friendly guidance when `examine` matches neither evidence nor an
    object in the current room."""
    loc = case.location_graph.get(state.current_location)
    obj_names = [o.name for o in case.world_objects.get(state.current_location, [])]
    loc_names = case.location_graph.names()
    target_lower = target.strip().lower()

    known_location = next((n for n in loc_names if n.lower() == target_lower), None)
    if known_location is not None:
        return red(f"{known_location} is a location. Use 'inspect {known_location}' "
                   f"to move there and search it.")

    if obj_names:
        return red(f"You can't examine '{target}'. Objects here you can examine: "
                   f"{', '.join(obj_names)}. To search another room, use: inspect <location>.")
    if loc is not None and loc.connections:
        return red(f"You can't examine '{target}'. Try 'inspect' on a connected "
                   f"room ({', '.join(loc.connections)}) and look around.")
    return red(f"You can't examine '{target}'. Try 'question <suspect>' or "
               f"'suspects' to talk to people.")


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
    if cmd == "hint":
        return cmd_hint(case, state, args), False
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

    # Natural-language questions work while a suspect is being questioned:
    # "where were you?" maps straight onto the `location` category.
    if state.current_suspect:
        category = nlu.interpret(line)
        if category is not None:
            return cmd_category(case, state, category), False
        return red(nlu.SUGGESTION_LINE), False

    return _suggest_command(cmd), False
