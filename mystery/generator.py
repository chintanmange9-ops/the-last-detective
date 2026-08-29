"""
Procedural case generator (build spec section 5).

Pipeline:
  Seed -> Victim -> Suspects -> Relationships -> Killer -> Motive -> Weapon
       -> Locations -> Timeline -> World facts -> Evidence -> Statements
       -> Lies -> Red herrings -> Validation -> Final case

random.Random(seed) (never the global `random` module) is used so that
running the same seed always produces the same case, while a different
seed normally produces a different one. If a generated case fails
validation it is discarded and regenerated using a deterministic
follow-up seed derived from (seed, attempt) - so the *overall* result for
a given top-level seed is still 100% reproducible.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from mystery import data
from mystery.truth import Truth
from mystery.timeline import Timeline, Event
from mystery.validator import validate_case, ValidationResult
from characters.personality import Personality
from characters.suspect import Suspect
from world.locations import Location, LocationGraph
from world.objects import WorldObject
from evidence.models import Evidence, Fact

MAX_GENERATION_ATTEMPTS = 500
MURDER_CAPABLE_LOCATIONS = ["Laboratory", "Office", "Library"]


@dataclass
class Case:
    seed: int
    case_id: str
    attempts: int
    victim_name: str
    victim_role: str
    truth: Truth
    suspects: Dict[str, Suspect]
    location_graph: LocationGraph
    world_objects: Dict[str, List[WorldObject]]
    timeline: Timeline
    evidence: Dict[str, Evidence]
    validation: Optional[ValidationResult] = None

    def suspect_names(self) -> List[str]:
        return list(self.suspects.keys())

    def ground_truth_facts(self) -> List[Fact]:
        """All facts derivable from the hidden truth + evidence, used by
        the validator and by the contradiction engine once evidence has
        been discovered. This is NOT shown to the player directly."""
        facts: List[Fact] = []
        for ev in self.evidence.values():
            facts.extend(ev.facts)
        return facts


def _build_location_graph() -> LocationGraph:
    graph = LocationGraph()
    for name, connections in data.LOCATION_GRAPH.items():
        graph.add(Location(
            name=name,
            connections=list(connections),
            objects=list(data.LOCATION_OBJECTS.get(name, [])),
            flavor=data.LOCATION_FLAVOR.get(name, ""),
        ))
    return graph


def _build_world_objects(graph: LocationGraph) -> Dict[str, List[WorldObject]]:
    objects: Dict[str, List[WorldObject]] = {}
    for name, loc in graph.locations.items():
        objs = []
        for obj_name in loc.objects:
            objs.append(WorldObject(
                name=obj_name,
                location=name,
                examine_text=f"You examine the {obj_name}.",
            ))
        objects[name] = objs
    return objects


def _snap(minutes: int) -> int:
    """Snap a time to a 1-minute grid (kept as a hook for future tuning)."""
    return minutes


def _build_case(rng: random.Random, seed: int, attempt: int) -> Case:
    graph = _build_location_graph()
    world_objects = _build_world_objects(graph)

    victim_name = rng.choice(data.VICTIM_NAMES)
    victim_role = rng.choice(data.VICTIM_ROLES)

    num_suspects = rng.randint(3, 6)
    suspect_names = rng.sample(data.FIRST_NAMES, num_suspects)
    killer_index = rng.randrange(num_suspects)
    killer_name = suspect_names[killer_index]

    motive = rng.choice(data.MOTIVES)
    weapon = rng.choice(data.WEAPONS)
    murder_location = rng.choice(MURDER_CAPABLE_LOCATIONS)
    murder_time = _snap(rng.randint(21 * 60 + 30, 22 * 60 + 45))

    other_locations = [loc for loc in graph.names() if loc != murder_location]

    # Every murder-capable location needs something examinable that can
    # surface the forensic/weapon evidence, even if the static location
    # data (data.LOCATION_OBJECTS) didn't already include one.
    murder_loc_obj = graph.get(murder_location)
    if "murder weapon" not in murder_loc_obj.objects:
        murder_loc_obj.objects.append("murder weapon")
        world_objects.setdefault(murder_location, []).append(
            WorldObject(name="murder weapon", location=murder_location,
                        examine_text=f"You examine what appears to be the murder weapon.")
        )

    timeline = Timeline()
    evidence: Dict[str, Evidence] = {}
    suspects: Dict[str, Suspect] = {}
    next_evidence_id = [1]

    def new_evidence(ev_type, location, description, facts, discover_condition,
                      is_red_herring=False, resolution_note=None) -> Evidence:
        eid = str(next_evidence_id[0])
        next_evidence_id[0] += 1
        ev = Evidence(
            id=eid, type=ev_type, location=location, description=description,
            facts=facts, discover_condition=discover_condition,
            is_red_herring=is_red_herring, resolution_note=resolution_note,
        )
        evidence[eid] = ev
        graph.get(location).evidence_ids.append(eid)
        return ev

    # Pick one non-killer suspect to carry a red herring (build spec section 14).
    non_killer_names = [n for n in suspect_names if n != killer_name]
    red_herring_name = rng.choice(non_killer_names) if non_killer_names else None

    # Pick a "discoverer" (non-killer) who finds the body.
    discoverer_candidates = [n for n in non_killer_names if n != red_herring_name] or non_killer_names
    discoverer_name = rng.choice(discoverer_candidates) if discoverer_candidates else killer_name

    for name in suspect_names:
        role = rng.choice(data.SUSPECT_ROLES)
        relationship = rng.choice(data.RELATIONSHIPS_TO_VICTIM)
        honesty = round(rng.uniform(0.2, 0.95), 2)
        fear = round(rng.uniform(0.15, 0.9), 2)
        knowledge = round(rng.uniform(0.3, 1.0), 2)
        is_killer = (name == killer_name)

        if is_killer:
            honesty = round(rng.uniform(0.05, 0.35), 2)  # killers lie about their alibi
            true_location = murder_location
            enter_time = murder_time - rng.randint(4, 10)
            exit_time = murder_time + rng.randint(3, 8)
            true_start, true_end = enter_time, exit_time
            # The lie: claims to have been somewhere else the whole time.
            claimed_location = rng.choice(other_locations)
            claimed_start = murder_time - rng.randint(20, 40)
            claimed_end = murder_time + rng.randint(15, 30)
        elif name == red_herring_name:
            # Genuinely in the murder location, but hours before the murder -
            # consistent with an innocent explanation (e.g. an earlier experiment).
            true_location = murder_location if murder_location != "Parking" else rng.choice(other_locations)
            true_start = max(18 * 60, murder_time - rng.randint(150, 200))
            true_end = true_start + rng.randint(20, 40)
            claimed_location, claimed_start, claimed_end = true_location, true_start, true_end
        else:
            true_location = rng.choice(other_locations)
            true_start = murder_time - rng.randint(30, 60)
            true_end = true_start + rng.randint(10, 25)
            claimed_location, claimed_start, claimed_end = true_location, true_start, true_end

        personality = Personality(honesty=honesty, fear=fear, knowledge=knowledge)
        suspect = Suspect(
            name=name, role=role, personality=personality,
            relationship_to_victim=relationship, is_killer=is_killer,
            motive_possibility=motive if is_killer else rng.choice(
                [m for m in data.MOTIVES if m != motive] + [motive]
            ),
            alibi_location=claimed_location, alibi_start=claimed_start, alibi_end=claimed_end,
        )
        suspects[name] = suspect

        # Visible timeline events: entering and leaving their TRUE location.
        timeline.add(Event(time=true_start, actor=name, location=true_location,
                            action="enters", visibility="visible",
                            detail=f"{name} enters the {true_location}"))
        timeline.add(Event(time=true_end, actor=name, location=true_location,
                            action="leaves", visibility="visible",
                            detail=f"{name} leaves the {true_location}"))

        # An access-log evidence item recording the suspect's true whereabouts.
        # This is what the player will eventually compare against statements.
        new_evidence(
            "access_log", true_location,
            f"Access records for the {true_location}.",
            [Fact(subject=name, property="location", value=true_location,
                  start_time=true_start, end_time=true_end,
                  source="evidence:access_log", reliability=1.0)],
            discover_condition={"type": "inspect_location", "location": true_location},
        )

    # Hidden murder event.
    timeline.add(Event(time=murder_time, actor=killer_name, location=murder_location,
                        action="murder", visibility="hidden",
                        detail=f"{killer_name} murders {victim_name} in the {murder_location}"))

    # Victim enters the murder location shortly before the murder.
    victim_enter = murder_time - rng.randint(15, 30)
    timeline.add(Event(time=victim_enter, actor=victim_name, location=murder_location,
                        action="enters", visibility="visible",
                        detail=f"{victim_name} enters the {murder_location}"))

    # Security camera "goes offline" around the murder window - this is why
    # nobody has direct footage of the murder itself, only of comings and goings.
    camera_off = murder_time - rng.randint(2, 6)
    camera_on = murder_time + rng.randint(2, 8)
    timeline.add(Event(time=camera_off, actor="security system", location=murder_location,
                        action="goes offline", visibility="visible",
                        detail=f"Security camera near the {murder_location} goes offline"))
    timeline.add(Event(time=camera_on, actor="security system", location=murder_location,
                        action="comes back online", visibility="visible",
                        detail="Security camera comes back online"))

    # Body discovered.
    discover_time = max(t.time for t in timeline.all_events() if t.actor == killer_name) + rng.randint(2, 6)
    timeline.add(Event(time=discover_time, actor=discoverer_name, location=murder_location,
                        action="discovers the body", visibility="visible",
                        detail=f"{discoverer_name} discovers the body in the {murder_location}"))

    new_evidence(
        "witness_statement", murder_location,
        f"{discoverer_name}'s account of finding the body.",
        [Fact(subject=discoverer_name, property="location", value=murder_location,
              start_time=discover_time, end_time=discover_time,
              source="evidence:witness_statement", reliability=0.9)],
        discover_condition={"type": "inspect_location", "location": murder_location},
    )

    # Forensic evidence at the murder scene, tied to the weapon.
    new_evidence(
        "forensic", murder_location,
        f"Forensic analysis of the {weapon} found at the scene.",
        [Fact(subject=killer_name, property="location", value=murder_location,
              start_time=murder_time, end_time=murder_time,
              source="evidence:forensic", reliability=0.85)],
        discover_condition={"type": "examine_object", "location": murder_location, "object": "murder weapon"},
    )

    # Security footage in the Hallway records the killer's true movement
    # into and out of the murder location - the single strongest piece of
    # evidence that contradicts the killer's claimed alibi.
    killer = suspects[killer_name]
    killer_true_events = [e for e in timeline.by_actor(killer_name) if e.location == murder_location]
    killer_enter = min(e.time for e in killer_true_events)
    killer_exit = max(e.time for e in killer_true_events)
    if "Hallway" in world_objects:
        new_evidence(
            "security_footage", "Hallway",
            f"Hallway camera footage covering the approach to the {murder_location}.",
            [Fact(subject=killer_name, property="location", value=murder_location,
                  start_time=killer_enter, end_time=killer_exit,
                  source="evidence:security_footage", reliability=1.0)],
            discover_condition={"type": "examine_object", "location": "Hallway", "object": "security camera"},
        )

    # A document evidence establishing motive.
    motive_location = "Office"
    new_evidence(
        "document", motive_location,
        f"A document hinting at a motive: {motive}.",
        [Fact(subject=killer_name, property="motive", value=motive,
              start_time=None, end_time=None,
              source="evidence:document", reliability=0.75)],
        discover_condition={"type": "examine_object", "location": motive_location, "object": "appointment calendar"},
    )

    # Red herring: suspicious-looking forensic detail with an innocent explanation.
    if red_herring_name:
        rh_suspect = suspects[red_herring_name]
        rh_events = [e for e in timeline.by_actor(red_herring_name)]
        rh_start = min(e.time for e in rh_events)
        rh_end = max(e.time for e in rh_events)
        new_evidence(
            "forensic", rh_suspect.alibi_location,
            f"A suspicious stain is found on {red_herring_name}'s clothing.",
            [Fact(subject=red_herring_name, property="location", value=rh_suspect.alibi_location,
                  start_time=rh_start, end_time=rh_end,
                  source="evidence:red_herring", reliability=0.6)],
            discover_condition={"type": "inspect_location", "location": rh_suspect.alibi_location},
            is_red_herring=True,
            resolution_note=(
                f"{red_herring_name} was in the {rh_suspect.alibi_location} well before the murder "
                f"window; the stain traces back to routine work there, not the killing."
            ),
        )

    truth = Truth(killer=killer_name, victim=victim_name, weapon=weapon,
                   motive=motive, location=murder_location, time=murder_time)

    case_id = f"{seed}"
    case = Case(
        seed=seed, case_id=case_id, attempts=attempt + 1,
        victim_name=victim_name, victim_role=victim_role, truth=truth,
        suspects=suspects, location_graph=graph, world_objects=world_objects,
        timeline=timeline, evidence=evidence,
    )
    return case


def generate_case(seed: int) -> Case:
    """Generate a fully validated case for the given seed. Deterministic:
    the same seed always yields the same final case."""
    attempt = 0
    last_result = None
    while attempt < MAX_GENERATION_ATTEMPTS:
        rng = random.Random(data.combine_seed(seed, attempt))
        case = _build_case(rng, seed, attempt)
        result = validate_case(case)
        if result.valid:
            case.validation = result
            case.attempts = attempt + 1
            return case
        last_result = result
        attempt += 1
    raise RuntimeError(
        f"Could not generate a valid case for seed {seed} after "
        f"{MAX_GENERATION_ATTEMPTS} attempts. Last errors: {last_result.errors if last_result else '?'}"
    )
