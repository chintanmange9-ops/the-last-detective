"""Printable case-brief export (`detective.py --story SEED`).

Renders a generated case as a self-contained, human-solvable whodunit in
markdown: the premise, the cast with alibis, the known timeline, the full
evidence catalogue, and a clearly separated solution key at the end.

Everything before the solution key is exactly what a player (or the
auto-solver bot) can discover: per-suspect alibis, the visible timeline,
and every evidence item with the facts it establishes. A reader who
compares the access logs / camera footage against each suspect's claimed
alibi finds the same contradiction the game's solve bot uses.

Only the final section reads the hidden truth, and it is fenced off so the
file can be printed as a puzzle by stopping before it.
"""

from evidence.models import format_time


def _suspect_block(case) -> str:
    lines = []
    for name, s in case.suspects.items():
        lines.append(f"- **{s.name}** - the {s.role}, {s.relationship_to_victim}.")
        lines.append(f"  Alibi: {s.alibi_statement()}")
    return "\n".join(lines)


def _scene_block(case) -> str:
    lines = []
    for name, loc in case.location_graph.locations.items():
        conn = ", ".join(loc.connections)
        lines.append(f"- **{name}** - {loc.flavor} (connects: {conn})")
    return "\n".join(lines)


def _timeline_block(case) -> str:
    return "\n".join(f"- {e.describe()}"
                     for e in case.timeline.sorted_events(include_hidden=False))


def _evidence_block(case) -> str:
    lines = []
    for eid in sorted(case.evidence, key=int):
        ev = case.evidence[eid]
        tag = "RED HERRING" if ev.is_red_herring else ev.type.replace("_", " ").title()
        lines.append(f"### Evidence #{ev.id} - {tag}")
        lines.append(f"**Found in:** {ev.location}")
        lines.append(ev.description)
        for f in ev.facts:
            lines.append(f"- {f.describe()}")
        if ev.is_red_herring and ev.resolution_note:
            lines.append(f"*Resolution: {ev.resolution_note}*")
        lines.append("")
    return "\n".join(lines)


def _solution_block(case) -> str:
    t = case.truth
    killer = case.suspects[t.killer]
    contradiction = (
        f"{t.killer}'s claimed alibi (the {killer.alibi_location}, "
        f"{format_time(killer.alibi_start)}-{format_time(killer.alibi_end)}) "
        f"is disproved by the discovered evidence, which places them in the "
        f"{t.location} at {format_time(t.time)} - the access records, camera "
        "footage, and forensic report align on it."
    )
    return "\n".join([
        "---",
        "",
        "# Solution key (stop here and solve it yourself first)",
        "",
        f"**Who:** {t.killer} murdered {t.victim}.",
        f"**Why:** {t.motive}.",
        f"**With:** {t.weapon}.",
        f"**Where & when:** the {t.location}, at {format_time(t.time)}.",
        "",
        contradiction,
    ])


def build_story(case) -> str:
    """Return the full printable case brief for a generated case."""
    t = case.truth
    lines = [
        f"# The Last Detective - Case File #{case.case_id}",
        "",
        f"> A printable whodunit, procedurally generated from seed "
        f"**{case.seed}** using nothing but the Python standard library.",
        "",
        "## The Case",
        "",
        f"The body of **{t.victim}** - {case.victim_role} - was found in the "
        f"**{t.location}**. The building was sealed last night; a small group of "
        "staff were on site. One of them is lying about where they were. Your "
        "job: compare every alibi against the evidence and name the liar.",
        "",
        "## The Cast",
        "",
        _suspect_block(case),
        "",
        "## The Scene",
        "",
        _scene_block(case),
        "",
        "## The Timeline (what is known)",
        "",
        _timeline_block(case),
        "",
        "## The Evidence",
        "",
        _evidence_block(case),
        "",
        _solution_block(case),
        "",
    ]
    return "\n".join(lines)