# Scan, diff against memory, and be honest about what is new

**Round 10. The owner's idea, tested rather than adopted. The mechanism works. Two defects had to be found first, and the strongest claim I made about it was wrong.**

Date: 2026-11-24 · Base: `0514dc57` (PR #7058) · Branch: `arena/4b0f723b-brain`

---

## 1. The idea, and what it collides with

> enter any new environment, scan everything, diff the scan against what memory knows, and everything left over is what to go and learn.

The project already had the three ends of this and never joined them:

| piece | what it does | what it lacks |
|---|---|---|
| `environment_probe_v1` | `snapshot(root)` → path/(size,mtime) | no notion of *kind* |
| `discover_v1` | `binaries()`, `entrypoints()` | what exists, not what it can *read* |
| `ignorance_ledger_v1` | `value = p_useful/(1+cost)` | nothing feeds it a scan |
| `jit_knowledge_v1` | instant-knowledge, needs ≥2 independent sources | needs a gap to aim at |

Nothing joined **scan → diff → ranked gap**. That join is this round.

The frontier agrees the direction is right and warns about the shape:

- **Look Before You Leap (2605.16143):** task-oriented training does *not* reliably produce exploration, and **naive exploration can hurt** performance.
- **Studying Without a Syllabus (2609.10824):** a meta-agent that studies an environment without knowing the downstream task, and *chooses its own artifacts*, beats fixed preprocessing on **5 of 6** benchmarks. That is the owner's idea, validated.
- **AgentCL (2606.02461):** continual learning is **not solved by storing more trajectories** — the hard problem is deciding what to abstract, retrieve, or ignore.

## 2. The naive version is worthless, and the project had already paid for it

A directory can always be "recognised": that is a `.json`, that is a `.png`. An agent that calls those KNOWN has learned nothing.

This repository already contains `cli_contract_inference.py` with `MAGIC_BY_SUFFIX` — a suffix→magic table. That is guess-shaped knowledge wearing knowing's clothes. A `.json` that does not parse is "known" under it and fails on use.

So identity here is **what a program that declares the kind actually accepts**. Seven validators, each one *rejecting* what is not its kind — `cat` is deliberately excluded because it accepts everything and therefore tells you nothing.

## 3. Two defects found by measuring, both mine

**Defect 1 — the scanner changed the thing it measured.** The python validator was `python3 -m py_compile`, which **writes `__pycache__` next to the file**. A scan of `intake/` then read the `.pyc` files its own validator had just created and reported markdown as `json+python+utf8_text`. Fixed with `ast.parse`, which judges the same property and writes nothing.

**Defect 2 — absence was learned as a kind.** Every file nothing can read shares the signature `()`. Learning it made the *first* unreadable file teach memory that unreadable bytes are a known kind, so **every later unknown file was reported KNOWN** — the machine confidently claiming to know exactly the things it did not know. The test caught it; `()` is now never learned.

Both are pinned by tests so they cannot return.

## 4. The claim I made and withdrew

My first transfer test showed signature keying 0.8 against suffix keying 0.6, and I nearly built on it. It came from **nine hand-made files in two tiny directories**.

Leave-one-out over **100 real files** from this repository:

| keying | recognised |
|---|---|
| signature | 100/100 |
| suffix | 100/100 |
| **signatures buy** | **0** |

The repo holds only three signature classes, so any key that has seen a `.json` recognises the next one. **Signature keying does not transfer better here, and I say so in the receipt and pin it with a test.**

What it does buy is **lying names**. Three of seven test files declare a kind their bytes are refused by:

```
lying.json   .json   ('utf8_text',)   does not parse as JSON
lying.py     .py     ('utf8_text',)   does not parse as Python
lying.png    .png    ('utf8_text',)   is not a PNG
```

A suffix rule calls all three known. The content signature catches all three.

## 5. Measured

| | |
|---|---|
| scan cost | 40 files: **5.1 s → 1.9 s** after necessary-magic skipping (`unzip -t` was ~0.2 s/file) |
| real transfer | learned on `canonical/verification` + `canonical/action_intents`, scanned `intake/`: 40 files, **27 KNOWN, 13 UNKNOWN** |
| ranked gaps | unaccepted kind **0.250** vs half-known **0.167** — from `ignorance_ledger_v1`'s own formula, not a rule I wrote |

Memory records a **signature**, never a path — asserted by a test, because a path in memory turns transfer into memorisation.

## 6. What this does not do

- It transfers only among kinds that have a **declared validator**. A kind with no validator stays UNKNOWN until one exists — and **that is the ceiling**, not the scan.
- Seven validators is a seed. The repo's own kinds (`docx`, `xlsx`, `pdf`) are uncovered.
- The **automatic scan → `jit_knowledge_v1` → verify round trip was not measured.** The scan produces the gap list and the ledger ranks it; the loop is not closed.
- No benchmark task was run.

## 7. The next bottleneck

**The validator set is the ceiling.** How much of an unseen environment can honestly be called known is decided by how many kinds have something that can read them — so the thing to make cheap is *adding validators automatically*, from a program's own declaration of what it accepts. That is the same join as round 9's declared producer, one level up: round 9 asked "what can produce this kind", round 10 asks "what can judge this kind", and both answers are sentences the program printed about itself.

Authority `NONE`, sandbox only, independent verification **OPEN**.
