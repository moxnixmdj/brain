# The plan for being ahead of the frontier

**Date:** 2026-11-24 · **Base:** `0b5ede3b` · **Authority:** NONE — sandbox measurement, not independent verification

You said the repo has already solved this under non-obvious names, and that it needs
to be at the unified runtime and the unified model. I measured that claim before
planning on it. It is **more true than you said, and worse than you think** — the
solutions exist *and* the key that unlocks them is itself locked.

---

## Part 1 — What I measured

### 1.1 The hidden capability pool is real

Compiled from `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` (`source_index`,
2,024 rows):

| Classification | Count | Meaning |
|---|---|---|
| ORPHAN | **1,519** | nothing imports it |
| ENTRY_POINT | 462 | has a `main` |
| INTERNAL_HELPER | 41 | composed into something else |
| UNPARSEABLE | 2 | |

- **760 orphans** match at least one capability axis you named.
- **959 orphans have a same-named test on disk.**
- Import fan-in across the whole repository: **max = 8**. Median = 0.

### 1.2 The pool is implemented, not stubbed

I spot-checked with line counts and stub counts, then ran tests:

| Module | Lines | `NotImplementedError` | Test result |
|---|---|---|---|
| `runtime/computer_env_v1.py` | 3,036 | 0 | — |
| `swe_kernel/sentient_cognitive_core_v1.py` | 2,444 | 0 | 37/39 pass |
| `runtime/transfer_learning_v1.py` | 967 | 0 | 125/138 pass |
| `runtime/associative_memory_v1.py` | 304 | 0 | **17/17 pass** |
| `runtime/curriculum_v1.py` | 465 | 0 | — |

`ComputerEnv` instantiates and runs end to end on the sandbox (snapshot → restore →
state hash `input.txt:26:4575a05f63b3`).

### 1.3 The crown jewels are the ones nobody imports

| Module | Classification | `imported_by_count` |
|---|---|---|
| `runtime/associative_memory_v1.py` | **ORPHAN** | 0 |
| `runtime/confinement_v1.py` | **ORPHAN** | 0 |
| `runtime/curriculum_v1.py` | **ORPHAN** | 0 |
| `runtime/transfer_learning_v1.py` | **ORPHAN** | 0 |
| `runtime/computer_env_v1.py` | **ORPHAN** | 0 |
| `swe_kernel/sentient_cognitive_core_v1.py` | **NOT_INDEXED** | — |

**`confinement_v1.py` is the substrate that the entire refusal wall demands.** It
implements `admit()`, `execute()`, `verify_effects()` — list-argv, no shell, worktree-bounded,
effects verified inside the clone. Its own docstring says it exists because
`computer_execution_boundary_v1.py` refuses everything with:

```
FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT
```

**That module is imported by nothing.** The key is in the same locked box as the door.

And `sentient_cognitive_core_v1.py` — 2,444 lines, sleep–wake consolidation,
epistemic self-belief, causal world graph, macro-abstraction — **is not in the source
index at all.** It is not hidden under a non-obvious name. It is absent from the unified model.

### 1.4 Two walls, one of them fake

**Wall A — the refusal wall.** Measured with `canonical/tools/lift_the_refusal_and_see_what_remains_v1.py`:

- `S0_baseline`: 17 arms refuse; 1 arm executes (`python.source.symbols.index.ast`, PASS).
- `S1_boundary_refusal_lifted`: **the same arms still fail**, but with *different*
  statuses — `FAIL_CLOSED__NO_OBSERVED_EFFECT`, `FAIL_CLOSED__STEP_RAISED_OUTCOME_UNKNOWN`,
  `FAIL_CLOSED__EFFECT_DIRECTED_CONFINED_RUN_DID_NOT_VERIFY`.

Lifting the refusal does not unblock anything. It converts one refusal into five
different ones. The refusal was **not** the blocker; it was the symptom of a
missing effect-verification path.

Worse: `curriculum_v1.py` contains **five hardcoded stub functions** — `_try_with`,
`_try_synthesize`, `_try_explore`, `_try_documentation` — each returning
`{"closed": False, ... "requires admitted confinement."}` as a literal. That is why
13 curriculum/transfer tests fail. The "channel" does not refuse because a boundary
said no; it refuses because someone wrote the refusal as a constant and never replaced it.

**Wall B — the namespace wall.** `sentient_cognitive_core_v1.py` fails 2/39 with
`CONFINED_WORKER_ERROR:NamespaceConfinementError`. That is `zero_ambient_namespace_launcher_v1.py`
failing at `MOUNTINFO_UNAVAILABLE`. This container cannot create namespaces. This
wall is **real for this environment** and is a genuine substrate limit, not a stub.

### 1.5 The unified model is a directory, not a composition

- 2024 indexed modules, but only **65 (3.2%) are imported by anything**, and
  **1,959 (96.8%) are imported by nothing.**
- 26 engines are flat labels (`engine:ADAPTIVE_SOLVER`, …), not composable objects.
- 447 capabilities, **153 bound**, and `source_index` carries `capability: false` on every row.
- Theory is explicit: `MUST_RUN_WITH_EVERY_OUTSIDE_MODEL_DELETED`,
  `producer_cognition_model_dependency_count: 0`, `NOT_A_TRAINED_NEURAL_NETWORK__CONTAINS_NO_WEIGHTS`.

---

## Part 2 — What the frontier actually looks like (2026-11)

Every number below is as-published, from the sources named; aggregators disagree by
20+ points, so harness and vendor are carried with each.

| Axis | Frontier, as published | Architecture it uses |
|---|---|---|
| Coding | SWE-bench Verified **95.0%** (Fable 5, vendor); **79.2%** independent board; SWE-bench Pro **61.5% ± 3.1** | scaffold + repo memory file + just-in-time `grep`/`glob` |
| Computer use | OSWorld-Verified **86.1%** (Qwen3.8-Max) vs human **72.36%**; OSWorld **2.0** binary **20.6%** / partial **54.8%** | screenshot loop, 500 steps, set-of-marks, OCR, action memory |
| Terminal | Terminal-Bench 4.0 **64.85% ± 3.11**; TB2.0 **82.7%** | shell + test-oracle loop |
| Long-horizon | METR **~12–17.4 h** at 50%; flags >16 h unreliable | — |
| Memory | LongMemEval: Zep **63.8%**, Mem0 **49.0%** | temporal KG / hybrid vector+graph+KV |
| Real-time learning | **weights stay frozen in production.** ICL best standalone: **28.8% → 49.4%** | TTT/TTT-E2E in research only; ~3.4× slower training |

### The four findings that matter

**1. The frontier's own agent-memory layer is *worse than nothing*.**
Gloaguen et al. 2026, 138 real repositories: **machine-generated context files
*reduced* task success** and raised inference cost 20–23%. Human-written,
constraint-focused files helped **~4%**. The frontier shipped an entire category —
`CLAUDE.md` / `AGENTS.md` / `GEMINI.md` — and the measurement says most of it is
net-negative. This is the weakest link in the frontier stack, and it is a *curation
and calibration* problem, which is precisely the class of problem this repo is built around.

**2. The frontier has no learning agent that knows when to learn.**
`Agentic-TTT` (Oct 2026) exists *because* "no fixed TTT method is broadly effective."
Its own result: 141 wrong→right versus 7 right→wrong, ~20:1. The frontier's real-time
learning is a per-query policy choice between five mechanisms, learned by RL, with no
memory of which choice worked last time.

**3. The frontier's computer use is a screenshot loop and is structurally broken on streaming.**
OSWorld 2.0 names it directly: tasks where the screen moves between observation and
action are **impossible** for screenshot-based agents. Streaming subset: GPT-5.5 scores
**57.8/50.0**, Claude Sonnet 4.6 scores **4.7/0.0**. That is not a capability gap, it is
an architectural impossibility. The same paper lists the fix: *"act on streaming,
continuously changing interfaces, keep a task-level model in memory across long
horizons, and catch and repair their own mistakes before they propagate."*

**4. Memory that decides what to keep is still an open problem.**
The 2026 memory race is explicit that "what to store / where / who decides" is
unresolved. Meanwhile `associative_memory_v1.py` — 304 lines, 17/17 passing — already
does exactly the thing the field is arguing about: associative partial-cue retrieval,
importance earned by whether retrieval *helped*, decay with disuse, emergent forgetting,
capacity 5,000, 7-day half-life.

---

## Part 3 — The plan

The asymmetry is not "we have more capability." We do not, and every measurement in
six passes says so. The asymmetry is that **the frontier's weakest three surfaces are
memory curation, knowing-when-to-learn, and streaming-state computer use — and this
repository has orphaned, tested implementations of all three.**

Being ahead does not come from adding capability. It comes from **composition
depth** — and the repo currently has a maximum fan-in of 8 and 96.8% dead weight.

### Track 0 — Unlock the key (1 day, highest value)

`confinement_v1.py` is ORPHAN. Wire it, and nothing else:

1. Replace the five hardcoded stubs in `curriculum_v1.py` with calls into
   `confinement_v1.admit/execute/verify_effects`.
2. Re-run the 13 failing tests. Expect: the refusal statuses change from
   `REQUIRES_ADMITTED_CONFINEMENT` to real effect verification — some pass, the rest
   fail for *reasons*, which is progress.
3. Run `lift_the_refusal_and_see_what_remains_v1.py` again and diff S0/S1.

**Stop condition:** S1 must show a *lower* count of `ADMITTED_CONFINEMENT` refusals
than S0. If it does not, the substrate is wrong and Track 0 is falsified.

### Track 1 — Make memory the product (the real moat)

The frontier argues about what memory should store. `associative_memory_v1.py` already
answers it and passes 17/17.

1. Register it in `source_index` with `capability: true` (it carries `false` today).
2. Give it a fan-in: `brain_unified_model_v1.solve(mode="RECALL")` should route through it.
3. **The unusual bet:** importance is learned from whether retrieval *helped*. That is a
   reward signal the frontier has no source for. Make it the currency: every capability
   invocation reports back whether the recalled memory helped, and memory decays without it.
4. Publish the forgetting curve as an artifact. Nobody in the field currently reports
   *what their agent forgot and why*.

### Track 2 — Composition depth, not surface area

96.8% of modules are imported by nothing. That is not an asset; it is a liability that
looks like one.

1. Rank the 959 tested orphans by fan-in potential and pick the **20** with the most
   distinct entry points.
2. For each, write the composition edge (one import) and a test that exercises the
   composition, not the module.
3. Measure fan-in at every step. **Target: max fan-in ≥ 5 on the 20 chosen modules.**
   Do not add a 2,025th module.

### Track 3 — Streaming computer use (the architectural opening)

OSWorld 2.0 states screenshot loops are structurally impossible on streaming tasks.
`computer_env_v1.py` is 3,036 lines with `act / snapshot / restore / state` and 0 stubs.

1. The bet: **state-based action instead of pixel-based.** Act on a hashed environment
   state (`input.txt:26:4575a05f63b3`), not a screenshot, so a state change between
   observation and action is *detected* rather than silently mis-clicked.
2. Every action carries a before/after state hash. A mismatch is a repair trigger.
3. This is checkable without a GUI: it is a property of the env substrate, and it is
   exactly the invariant OSWorld 2.0 says current agents lack.

### Track 4 — The unification (what you actually asked for)

The unified model must stop being a directory and become a composition:

1. Index `swe_kernel/` (it is absent — `sentient_cognitive_core_v1.py` is NOT_INDEXED).
2. Replace the 26 flat engine labels with objects that expose `act()`, so
   `engine:X` can call `engine:Y`.
3. Set `capability: true` from measured test evidence, not from presence on disk.
4. **Emit a composition graph** and make the digest depend on it. Today the digest
   depends on file hashes, so a module nobody can reach still changes the model.

---

## Part 4 — The honest risk

Three things could make this plan wrong, and I would rather name them than have you
discover them:

1. **The orphan pool may be mostly redundant.** 1,519 modules could be 1,519 variations
   on a theme. I sampled; I did not deduplicate. Track 2's first job is to measure
   novelty, not to wire things up.
2. **The confinement substrate may not work.** Its docstring claims effects are
   verified inside the clone. I have not run `admit()` end to end. If Track 0's stop
   condition fails, the substrate is a description, not an implementation.
3. **Composition is not capability.** Wiring 20 modules does not make the system 20×
   more capable. It makes the *existing* capability addressable, which is necessary
   and not sufficient — and the six-pass audit already established that the frontier
   wins task completion by 20–30×. Nothing here changes that number.

The plan does not claim we can out-complete the frontier. It claims we can be *ahead*
on the three axes where the frontier's own papers say it is architecturally stuck, and
where this repository already has tested, orphaned machinery.

---

## Appendix — Measurements and how to reproduce

```
# source index classification
python3 - <<'PY'
import json; m=json.load(open('canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json'))
import collections; print(collections.Counter(r['classification'] for r in m['source_index']))
PY

# fan-in
python3 -c "
import json;m=json.load(open('canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json'))
si=m['source_index'];print(sum(1 for r in si if (r.get('imported_by_count') or 0)>0),'/',len(si))"

# the refusal counterfactual (needs a clean tree)
python3 canonical/tools/lift_the_refusal_and_see_what_remains_v1.py

# memory + cognitive core
python3 -m pytest canonical/tests/test_associative_memory_v1.py -q
python3 -m pytest canonical/tests/test_sentient_cognitive_core_v1.py -q
```

**Falsifiers.** This document is falsified if: `confinement_v1.admit()` cannot execute
a list-argv command inside a worktree; if `associative_memory_v1`'s importance signal
turns out not to be outcome-driven on inspection; or if the 1,519 orphans deduplicate
to fewer than ~100 distinct mechanisms.
