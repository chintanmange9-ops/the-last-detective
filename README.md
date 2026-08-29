# The Last Detective

> "Every clue tells a story. Every suspect tells a lie. Find the contradiction."

A complete, playable, procedurally generated murder-mystery game for the
terminal. Built for the Zero Dependency 2026 Hackathon (Track F — Open /
Wildcard).

**Zero third-party runtime dependencies.** Python standard library only.
No pygame, no rich, no click, no numpy/pandas, no network access, no
external LLM/API calls during gameplay.

## Quick start

```bash
python detective.py --seed 48291
```

That's it — one command, and you're dropped into a fully generated
murder case: a victim, a handful of suspects, a killer hidden among
them, evidence scattered across a small building, and a truth only you
can uncover.

## How to play

Move around, look for evidence, and question suspects. Run `help`
in-game for the full command list:

```
new                     Start a new generated case (restart the CLI with a new --seed)
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
notes / note <text>     View or add detective notes
map                     Show the location graph
status                  Show case/player status
accuse <name>           Accuse a suspect (ends the case)
save <file>             Save game
load <file>             Load game
help                    Show this help
quit                    Exit
```

A typical session:

```
> inspect Laboratory
> examine murder weapon
> inspect Hallway
> examine security camera
> question Daniel
> location
> present 8
> accuse Daniel
```

### Startup options

```bash
python detective.py --seed 48291       # play a specific case
python detective.py --load save.json   # resume a saved game
python detective.py --replay run.json  # replay a recorded set of actions
python detective.py --stress 2000      # developer command: generate 2000
                                        # cases and report any that fail validation
```

## Why it feels different every time

Every case is generated from an integer seed using `random.Random(seed)`
— never the global `random` module — so:

- **The same seed always produces the same case.** Victim, suspects,
  killer, motive, weapon, murder location, timeline, evidence, and red
  herrings are all fully determined by the seed.
- **A different seed normally produces a different case.**
- Before a case is shown to the player, it runs through
  `mystery/validator.py`, which checks (among other things) that there
  is exactly one possible killer, the timeline is internally consistent,
  every location is reachable, there's enough evidence to work with, and
  no red herring accidentally creates a second valid solution. If a
  generated case fails any check, it's discarded and regenerated
  automatically using the next deterministic sub-seed — so a top-level
  seed still always resolves to the same final, valid case.

## Architecture

```
the-last-detective/
├── main.py                 # thin wrapper around detective.py
├── detective.py             # CLI entry point (argparse)
├── game/                    # game loop, player-visible state, command dispatch
├── mystery/                 # the generator, the hidden Truth Engine, the timeline, the validator
├── evidence/                 # Fact/Evidence data models + discovery system
├── characters/               # suspects, personality traits, interrogation dialogue
├── world/                    # location graph + examinable objects
├── deduction/                # the contradiction engine
├── storage/                  # save/load (JSON) and replay
├── ui/                       # ANSI-based terminal rendering
└── tests/                    # unittest suite
```

The most important architectural rule in the project (see build spec
section 20): **the hidden truth is never exposed directly to the UI
layer.** `mystery/truth.py` holds the answer key; `game/state.py` holds
only what the player has actually discovered. Everything the player sees
- evidence, suspect statements, the timeline - is derived from the truth
by the generator, but the truth object itself is never printed or
compared against anything except an explicit `accuse` command.

## Running the tests

```bash
python -m unittest discover -s tests
```

34 tests cover deterministic generation, the validator's consistency
checks (including a 200-case stress pass), the timeline engine, evidence
discovery, the contradiction engine, save/load round-tripping, replay
fidelity, and both correct and incorrect accusations.

For a much larger stress run (generate thousands of cases and report any
validation failures), use the built-in developer command instead of the
test suite:

```bash
python detective.py --stress 5000
```

## Design notes

- **Hidden Truth Engine** (`mystery/truth.py`): the single source of
  truth for what actually happened. Evidence, statements, and the final
  accusation check are all derived from or validated against it.
- **Fact model** (`evidence/models.py`): every claim in the game -
  whether it comes from a suspect's mouth or a piece of evidence - is a
  structured `Fact(subject, property, value, start_time, end_time,
  source, reliability)` rather than free text. This is what lets the
  contradiction engine reason about the case instead of doing string
  matching.
- **Contradiction Engine** (`deduction/contradictions.py`): never tells
  the player who's lying. It only ever reports "these two facts don't
  fit together" - drawing the conclusion is left entirely to the player.
- **Red herrings**: exactly one non-killer suspect in every case carries
  a suspicious-looking but ultimately innocent piece of evidence. The
  validator explicitly checks that red herrings never create a genuine,
  provable contradiction - they can only ever look suspicious.
- **No external LLM/API dependency for dialogue.** All suspect dialogue
  is generated from deterministic templates, selected with a small
  per-question seeded RNG so that dialogue is stable across replays of
  the same seed and action sequence.

See `STDLIB.md` for a full list of third-party packages this project
deliberately avoided and what standard-library code replaced them.

## Dependency proof

```bash
pip install -r requirements.txt   # installs nothing - the file is empty by design
python detective.py --seed 1      # still runs
```

The game imports only: `argparse`, `random`, `dataclasses`, `json`,
`pathlib`, `sys`, `hashlib`, `collections`, `shutil`, `textwrap`,
`typing`, and `unittest` (tests only) - all standard library.
