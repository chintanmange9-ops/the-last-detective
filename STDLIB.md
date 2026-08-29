# STDLIB.md — Standard Library Substitutions

The Last Detective has a hard requirement: **zero third-party runtime
dependencies**. Everything the game does at runtime is built from the
Python standard library. This document lists the meaningful places where
a third-party package would normally be reached for, why it was avoided,
and what standard-library approach replaced it.

---

### 1. Command-line parsing
**Normally:** `click` or `typer`
**Instead:** `argparse`
**Purpose:** Parsing `--seed`, `--load`, `--replay`, and `--stress`
startup options in `detective.py`. `argparse` ships with Python and
covers everything the CLI needs: typed arguments, defaults, and
auto-generated `--help` output.

### 2. Terminal formatting and color
**Normally:** `rich` or `colorama`
**Instead:** raw ANSI escape sequences + `sys.stdout.isatty()`
**Purpose:** `ui/terminal.py` prints bold/colored text and a box-drawn
status panel by writing ANSI codes directly, and disables color entirely
when output isn't a real terminal (e.g. when piped to a file). No
external terminal-styling library is required.

### 3. Text wrapping and layout
**Normally:** a UI/templating library
**Instead:** `textwrap` + `shutil.get_terminal_size()`
**Purpose:** `ui/formatting.py` wraps long lines to the actual terminal
width without pulling in any layout engine.

### 4. Structured data validation
**Normally:** `pydantic`
**Instead:** `dataclasses` + explicit validation logic
**Purpose:** `Fact`, `Evidence`, `Suspect`, `Location`, and `Truth` are
all plain `@dataclass` definitions. Validation of the *generated case*
(not just field types) is handled explicitly and deliberately by
`mystery/validator.py`, which is a better fit than schema validation for
checking things like "exactly one killer" or "timeline is internally
consistent."

### 5. Tabular / data-science style manipulation
**Normally:** `pandas` / `numpy`
**Instead:** plain `dict`/`list` structures and `random.uniform` /
`random.Random`
**Purpose:** Suspect personality traits (honesty, fear, knowledge) and
fact collections are small enough that Python's own data structures and
the standard `random` module are simpler and just as fast as pulling in
an array/dataframe library for this scale of data.

### 6. Graph modeling
**Normally:** `networkx`
**Instead:** a small hand-rolled `LocationGraph` (`world/locations.py`)
with breadth-first search
**Purpose:** The location map only needs adjacency storage and
reachability checks (`reachable_from`, `path_exists`). A ~30-line BFS is
far lighter than a full graph library for this use case.

### 7. Object persistence (save/load)
**Normally:** `pickle`, or a database via `sqlalchemy`
**Instead:** `json` + `pathlib` + `dataclasses`
**Purpose:** `storage/save.py` serializes only the *mutable* game state
(discovered evidence IDs, interrogation progress, notes, player
location) to plain JSON. This is safer than `pickle` (no arbitrary code
execution on load) and human-readable, and avoids depending on any
database engine.

### 8. Procedural / fake data generation
**Normally:** `faker`
**Instead:** hand-curated content pools in `mystery/data.py` combined
with `random.Random(seed)`
**Purpose:** Deterministic, game-appropriate names, roles, motives, and
weapons don't need a general-purpose fake-data library; a curated pool
sampled with a seeded RNG gives full control over tone and reproducibility.

### 9. Dialogue / text templating
**Normally:** `jinja2`
**Instead:** plain Python f-strings and small template-selection
functions
**Purpose:** `characters/interrogation.py` builds all suspect dialogue
from f-string templates chosen deterministically via a per-question
seeded `random.Random`. No templating engine or external LLM/API call is
used at runtime.

### 9b. Natural-language command interpretation
**Normally:** a small NLP library (e.g. `spacy`, `nltk`) or an LLM API
**Instead:** hand-written regular expressions from the standard `re`
module
**Purpose:** `characters/nlu.py` maps free-form player questions ("why?",
"where were you?") onto the game's interrogation categories with a
prioritised pattern list. No ML, no NLP framework, no network call.

### 9c. Typo-tolerant command matching
**Normally:** a fuzzy-matching package (e.g. `fuzzywuzzy`) or an
autocomplete library
**Instead:** `difflib.get_close_matches` from the standard library
**Purpose:** `game/commands.py` suggests the intended command when the
player mistypes one (e.g. `timelime` -> `timeline`), keeping the CLI
forgiving without adding a dependency.

### 9d. Automated playtesting / solvability proof
**Normally:** a game-testing or bot framework (e.g. `gymnasium`, a UI
automation library) or an RL library
**Instead:** a hand-written deterministic solver (`tools/solver.py`)
driving the exact same command entry point the human player uses
**Purpose:** `detective.py --solve N` auto-solves N generated cases with
nothing but `collections.deque` (BFS pathfinding) and the game's own
command functions - proving every generated case is solvable without
adding a testing/bot dependency.

### 10. HTTP / network access
**Normally:** `requests`
**Instead:** not used at all — the game is 100% offline. If a future
stretch feature genuinely needed HTTP (it currently doesn't), the
standard-library `urllib.request` or `http.client` would be used instead
of adding a dependency.

### 11. Progress bars for the stress-test command
**Normally:** `tqdm`
**Instead:** plain `print()` status lines
**Purpose:** `detective.py --stress N` reports failures as it goes and a
one-line summary at the end; generation is fast enough (thousands of
cases in seconds) that a progress bar isn't needed.

### 12. CLI colorization on Windows
**Normally:** `colorama` (to make ANSI codes work on legacy Windows
terminals)
**Instead:** ANSI codes are only emitted when `sys.stdout.isatty()` is
true, and modern Windows Terminal / PowerShell already understand ANSI
natively, so no compatibility shim is required.

---

Every substitution above was implemented because the feature was
actually needed for gameplay — none of these are placeholder stand-ins
for missing functionality.
