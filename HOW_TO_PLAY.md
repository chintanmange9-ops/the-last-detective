# The Last Detective — How to Play

> **Zero-dependency procedural murder-mystery · Track F · Python stdlib only**  
> Updated 2026-08-30 — matches code at commit `a5e5b62` (`b293698` + LICENSE) · 73 tests · `deps-proof.txt` · `--story`

---

## Your Mission

You are a detective investigating a murder. One person in a small group on site is lying about where they were.

Your goal is **not** simply to guess the killer. Prove **WHO** killed the victim, **HOW** (weapon), **WHY** (motive), **WHEN** (time), and **WHERE** (location) — with evidence and contradictions.

Every case is procedurally generated and deterministic: the same `--seed` always creates the same case.

---

## Starting the Game

Run from inside `the-last-detective/`:

```bash
python detective.py --seed 48291
```

The integer after `--seed` picks a unique mystery. Example (seed `48291`, the default in this doc):

```
CASE #48291
Victim: Chairman Elliot Grey (estate owner)
Location: Library
Suspects (5): Simon, Claire, Louis, Nathan, Grace
```

You are **not** told who the killer is.

Other useful flags (for reviewers / power users):

```bash
python detective.py --story 48291                          # printable case brief (markdown, ASCII-clean)
python detective.py --solve-seed 48291 --solve-verbose     # auto-solve one seed and print solution
python detective.py --solve 2000                           # auto-solve 2000 cases, report failures
python detective.py --stress 500                           # generation stress test
python tools/deps_proof.py                                 # verify zero third-party imports
```

---

## The World

Every case uses the same building. What changes is who was where, when, and what evidence was left behind.

### Locations and connections (use `map` in-game)

| Location | Flavor | Connects to |
|---|---|---|
| **Library** | Rows of quiet shelving. A single reading lamp is still on. | Office |
| **Office** | Papers are neatly stacked; a computer screen glows on standby. | Library, Hallway |
| **Hallway** | A long corridor connecting the building's main rooms. | Office, Laboratory, Cafeteria |
| **Laboratory** | Workbenches, locked cabinets, and the smell of chemicals. | Hallway |
| **Cafeteria** | A handful of tables, a coffee machine still warm. | Hallway, Parking |
| **Parking** | A small lot behind the building, mostly empty at night. | Cafeteria |

Movement is **one adjacent room at a time**: `inspect <location>` moves you only if that room is directly connected. If you try a distant room you will see:

```
You can't get to Cafeteria directly from Laboratory. Try 'map'.
```

### Objects you can examine

Varies slightly by murder location; the murder location always has `murder weapon`:

- **Library:** reading lamp, checkout ledger, murder weapon (if murder was there)
- **Office:** desk computer, appointment calendar
- **Hallway:** security camera, keycard reader
- **Laboratory:** workbench, chemical cabinet, murder weapon (if murder was there)
- **Cafeteria:** coffee machine, cafeteria access log
- **Parking:** parking gate log

---

## Basic Commands

Type `help` in-game to see this list. Commands are **typo-tolerant** (e.g. `timline` suggests `timeline`) and **natural-language** questions work while interrogating (`where were you?` → `location`).

```
inspect <location>      Move to a location and search it for evidence
examine <target>        Examine evidence or an object where you are
                        (you can also "examine <location>" - treated like inspect)
suspects                List all suspects
question <name>         Interrogate a suspect (e.g. question Simon)
present <evidence id>   Present evidence while questioning (e.g. present 8)
<category>              While questioning: location / timeline / victim / other /
                        evidence / motive / relationship / weapon
                        Natural language also works: "where were you?", "why?"
done                    Stop questioning the current suspect
timeline                Review the known (visible) timeline
evidence                List discovered evidence
notes / note <text>     View notes / add a detective note
map                     Show the location graph (with "you are here")
status                  Show case/player status (evidence found, notes, accusations)
hint                    Nudge toward undiscovered evidence (costs final rank)
accuse <name>           Make the final accusation (ends the case)
save <file> / load <file>  Save / load a .json investigation
help / quit             Show this help / exit
```

Source: `game/commands.py:19-44` (`HELP_TEXT`).

---

## Step 1 — Examine the Crime Scene

Start with `map`, then `inspect` each location and `examine` its objects. The murder location always contains the murder weapon object; examining it may reveal forensic evidence.

Example flow (**respects adjacency** — you cannot jump Laboratory → Cafeteria):

```
map
inspect Office       →  examine desk computer, examine appointment calendar
inspect Hallway      →  examine security camera, examine keycard reader
inspect Laboratory   →  examine workbench, examine chemical cabinet, examine murder weapon
inspect Hallway
inspect Cafeteria    →  examine coffee machine, examine cafeteria access log
inspect Parking      →  examine parking gate log
```

Do not assume the first suspicious object is the murder weapon. Some evidence is a red herring (see Step 6).

---

## Step 2 — Investigate Every Suspect

Use `suspects` to see names/roles, then `question <name>`. While questioning you can ask about any category:

```
question Simon
  location    —  "Where were you?"
  timeline    —  "Walk me through the evening."
  motive      —  "Why would you want them dead?"
  weapon      —  "Do you know the murder weapon?"
  victim / relationship / other / evidence
  present 8   —  confront with evidence #8
  done        —  stop questioning
```

Natural language works too: `"where were you?"`, `"why?"`, `"what about the weapon?"` Remember what each suspect claims — you will compare it to evidence next.

> Tip: characters have a personality/mood that affects how they answer, and the NLU is regex-based (`characters/nlu.py`) with typo tolerance via `difflib`.

---

## Step 3 — Verify Their Stories

Never automatically believe a suspect. Compare every alibi to the evidence and the visible timeline.

Example:

```
Simon: "I was in the Office from 21:53 to 22:42."
Access log (Library): Simon 22:07–22:22
Security footage (Hallway): Simon in Library 22:07–22:22
Forensic (Library, 22:16): heavy paperweight places Simon in Library at 22:16
```

This is a contradiction: Simon claims to be in the Office but three independent pieces of evidence place him in the Library at the murder window (22:16). However, a lie does **not** automatically mean the person is the killer — check the next steps.

---

## Step 4 — Collect Evidence

Search locations for these evidence types (**11 per case**, including one red herring):

- **Access logs** — keycard entries/exits (Library, Parking, etc.)
- **Security footage** — Hallway camera covering the approach to the murder location
- **Witness statement** — who discovered the body and when
- **Forensic analysis** — weapon/scene detail tying a suspect to the murder time
- **Document** — motive hint (Office, appointment calendar)
- **Phone record** — victim–suspect exchange before the murder (Office, desk computer)
- **Red herring** — suspicious-looking stain on an innocent suspect's clothing, with a written resolution note

Use `evidence` to see what you have found. Each item lists the fact it proves and, for red herrings, an explicit innocent resolution.

---

## Step 5 — Build the Timeline

Use `timeline`. It shows **only visible events** — the hidden `murder` event is never shown. Cross-reference it with alibis.

Example (seed `48291`, visible only):

```
19:40  Grace enters the Library
20:07  Grace leaves the Library
21:41  Nathan enters the Parking
21:44  Claire enters the Parking
21:47  Chairman Elliot Grey enters the Library
22:07  Simon enters the Library
22:12  Security camera near the Library goes offline
22:22  Simon leaves the Library
22:26  Claire discovers the body in the Library
```

Ask: Who could physically reach the crime scene? Who had enough time? Whose alibi covers the murder window and who is lying about their location? The camera "offline" window is why nobody has direct footage of the murder itself — only of comings and goings.

---

## Step 6 — Find Contradictions

Compare statements, evidence, timeline, and access records. A strong case needs multiple independent pieces of evidence that all point the same way.

Example:

```
Grace: "I was in the Library 19:40–20:07."  →  Access log confirms it,
red herring stain on her clothing is explained:
"was in the Library well before the murder window; the stain traces back
to routine work there, not the killing."  →  not the killer, despite
initial suspicion.
```

The win screen lists **only** evidence that actually contradicts the killer's alibi (honest win screen — no fake "confession"). If every evidence you found contradicted the same person, you have a strong theory.

---

## Step 7 — Find the Motive

Ask why the suspect would kill the victim. Pool of motives in this game:

> research theft, financial fraud, inheritance dispute, blackmail, professional betrayal, jealousy, revenge, silencing a whistleblower, a broken business deal, a hidden affair

Possible to find via the Office document (appointment calendar). A motive alone is never enough — look for motive + opportunity + forensic evidence that all align.

---

## Step 8 — Determine the Weapon

Pool:

> laboratory knife, letter opener, blunt candlestick, poisoned tea, length of wire, fire poker, surgical scalpel, heavy paperweight

Determine who had access to it, who touched it, and where it was. Forensic evidence at the murder location ties the weapon to a suspect at the murder time (e.g. `Forensic analysis of the heavy paperweight … Simon in Library at 22:16`).

---

## Step 9 — Build Your Theory

Before accusing, answer all five and check that evidence supports each:

```
WHO?   (e.g. Simon)
HOW?   (heavy paperweight)
WHY?   (inheritance dispute)
WHEN?  (22:16)
WHERE? (Library)
```

Example consistent theory (seed `48291`): **WHO** Simon, **HOW** heavy paperweight, **WHY** inheritance dispute, **WHEN** 22:16, **WHERE** Library — supported by access log, camera footage, and forensic report that all place Simon in the Library at 22:16, contradicting his Office alibi 21:53–22:42.

---

## Step 10 — Make the Accusation

When confident, use:

```
accuse Simon
```

A correct accusation shows `CASE CLOSED` with killer, motive, weapon, location, time, the list of contradicting evidence ids, and a rank/score epilogue (Apprentice → Chief Inspector → **The Last Detective**). A wrong accusation shows `CASE FAILED` and reveals the truth. Both end the game; accusation attempts and hints affect your final rank.

The case is scored `0–1000` (see `game/scoring.py`): evidence found, speed, wrong accusations, and hints all matter. Aim for **The Last Detective**.

---

## Important Rules

1. Do not guess randomly.
2. Suspicious does not mean guilty.
3. A lie does not automatically prove murder.
4. Look for multiple independent pieces of evidence.
5. Use the timeline — check physical opportunity.
6. Check adjacencies (`map`): you cannot jump distant rooms.
7. Use `examine <location>` if you type a location after examine — it is treated like `inspect`.
8. Consider red herrings: one per case, always with an innocent resolution note.
9. Explain the entire crime (who/how/why/when/where).
10. Use `hint` only if stuck — it costs rank.

---

## The Golden Rule

> Do not ask: **"Who looks most suspicious?"**
>
> Ask: **"Can I prove that this person committed the crime?"**

That is how you win *The Last Detective*.

---

## Appendix — For Reviewers & Judges

**Zero-dependency proof** (`STDLIB.md`, `deps-proof.txt`, `.zero-dep.toml`):

This game uses only the Python standard library. Verify with:

```bash
python tools/deps_proof.py                # scans 45 source files; "OK: every import is stdlib"
cat deps-proof.txt                         # written receipt of that scan
cat requirements.txt                       # empty (no third-party runtime deps)
cat STDLIB.md                              # 14 stdlib substitutions + Package Killer (colorama → raw ANSI)
```

**Deterministic & printable:**

```bash
python detective.py --story 48291 > case_48291.md   # complete human-solvable brief
# premise, cast alibis, scene, visible timeline, evidence incl. red-herring resolution,
# separated solution key — ASCII-clean for Windows console
```

**Automated verification:**

```bash
python -B -m unittest discover -s tests   # 73 tests
python detective.py --solve 2000          # auto-solve 2000 cases
python detective.py --stress 500          # stress 500 generations, 0 failures expected
```

**Track F thesis:** procedural mystery as a playable tool — idiomatic stdlib (`argparse`, `dataclasses`, `hashlib`, `unittest`, `difflib`, `zoneinfo`) and intentional design (honest win screen, red herring with resolution, adjacency-constrained movement, NLU via regex, BFS solver). No stunt imports.

*Mirrors `The_Last_Detective_How_To_Play.docx` (parent dir) — this `.md` is the in-repo, GitHub-rendered version.*
