# THE VERDICT ON §3: WHAT IS REAL, WHAT IS FALSE, WHAT IS UNPROVEN, AND WHERE THE BOTTLENECK ACTUALLY IS

**Date:** 2026-11-24
**Branch:** `arena/94363358-brain`, from `c4f529eb`
**Method:** every claim below is either (a) a receipt this session produced, (b) a file in this
repository quoted with its path, or (c) explicitly marked UNPROVEN. Nothing is asserted
because it was said earlier, including by me.

---

## 1. The one-line verdict

**The project has a real, working instrument and a false agent.** The instrument reads an
edit off a failing run without a model; the agent that is supposed to use it has no
computer-use ability at all. The gap between them is not a matter of degree — it is the
whole of §6.

---

## 2. What is REAL (verified this session, with receipts)

### 2.1 The relation reader — 6 verified rows out of 45, all landed on the human's line

Receipt: `/tmp/rel/g5.json`, 45 rows, 1067.1 s.

| repo | commit | human line | relation used | landed |
|---|---|---|---|---|
| attrs | `3b0378dd` | 451 | MATERIALISE | True |
| attrs | `a572c3a4` | 2025 | SIBLING_DISJUNCT | True |
| more-itertools | `71e070b3` | 4282 | PRESENCE | True |
| packaging | `258202ed` | 38 | ANCHOR | True |
| packaging | `8af75907` | 69 | ANCHOR | True |
| packaging | `b80e6eb0` | 839 | PRESENCE | True |

"Landed" is computed, not declared: the edited line number must be *inside* the span of
the human's changed line. All six are.

The instrument is real in the only sense that matters: it runs the target repository's own
pytest suite as the oracle, it refuses to claim a fix when the suite says otherwise, and it
has named stages for every way it can fail without producing a lie
(`NO_RELATION_READ_FROM_THE_RUN`, `NO_EDIT_SURVIVED_THE_PROJECT_SUITE`,
`THE_NAMED_TEST_DID_NOT_FAIL_IN_THIS_SESSION`, `CHANGED_LINE_NEVER_EXECUTED`,
`HARNESS_BLOCKED_THE_SUITE`, `THE_PROBE_REMOVED_THE_FAILURE`).

### 2.2 Two relations are derived, not enumerated

- **SIBLING_DISJUNCT** (new this session). At attrs `a572c3a4` the demanded guard is
  `if frozen is True:` at line 2025, nested inside `if a.on_setattr is not None:`. The
  human's edit is `if frozen is True and a.on_setattr is not setters.NO_OP:`. The conjunct
  is spelled **verbatim in the same file**, in the sibling `elif` at line 2030. The
  relation finds the chain, extracts each `and`-clause, and moves the one nearest the
  `raise` into the guard. The tool reproduces the human's line character for character.
- **MATERIALISE**. `attrs = field_transformer(cls, attrs)` → `tuple(field_transformer(...))`.
  Read off the *value's type* in the trace (a generator), not from any table. This is the
  row that previously failed with `THE_PROBE_REMOVED_THE_FAILURE`; it now passes because
  the probe re-raises instead of swallowing the site's exception.

### 2.3 A store with a real admission filter and two real ablations

`canonical/tools/the_store_is_the_only_thing_that_learns_v1.py`. Three arms over the same
rows in the same order — EMPTY / GENERAL / RAW. A skill is admitted only if it is VERIFIED,
LANDED, and expressible without naming a project-defined symbol or a source literal.
Shapes are computed (`tuple(<expr>)`, `<expr>is not None`, `<expr>.method()`,
`<expr>and <obj>.<attr> is not <obj>.<attr>`), not asserted.

**Status: built and running. The ablation has NOT yet produced a verdict** — see §5.

---

## 3. What is FALSE

| Claim | Status | Evidence |
|---|---|---|
| "Iteration 75", commit `209bbc6c` | **FAILED** | `git cat-file -t 209bbc6c` → *Not a valid object name* |
| "344 failing cases/files" | **FALSE** | `canonical/verification/HONEST_SUITE_BASELINE_20261103_V1.json`: 16 361 cases, 15 255 passed, **984 failed**, 42 error, 34 files, at `git_head 407cc3c3`, working tree dirty |
| "75.2% of real fixes fall outside fixed grammars" | **UNPROVEN, and contradicted by this repo's own corpus** | Measured here: **16/45 (35.6%)** of the corpus's fixes introduce an identifier absent from the old line. The 75.2% figure exists nowhere in this repository. |

### 3.1 The agent is false, and this is the decisive finding

`canonical/swe_kernel/computer_use_agent_v1.py` (787 lines) reports
`model_calls: 0, network_calls: 0` and looks like a computer-use agent. It is not one.
Its `sense()` method selects the "right action" by **word overlap between the instruction
and a hard-coded table**, then calls that table "the action space":

```python
for name, command, program in TASKS:
    triggers = set(command.replace("{src}", " ").replace("{dst}", " ").split())
    overlap = len(set(instruction.lower().split()) & triggers)
```

That table, `canonical/swe_kernel/computer_use_check_density_v1.py::TASKS,` has
**10 rows** over 9 shell utilities (`gzip`, `sort`, `sed`, `tr`, `split`, `tar`, `base64`,
`cp`, `sha256sum`). There are no pixels, no screenshots, no GUI, no application, no
browser, no coordinate space, and no perception of any kind. A 10-row shell table
selected by keyword overlap is the definition of memorised world knowledge in parameters —
which §2 forbids — and it is not computer use on any benchmark.

**Consequence:** every OSWorld, Terminal-Bench, or GUI claim this repository has ever
made is **UNPROVEN at best and FALSE at runtime**. The capability does not exist in the code.

---

## 4. What is UNPROVEN

- **§6 as a whole.** Not one of its seven simultaneous criteria is met. See §6.
- **447 capabilities, 226 tricks, 0.35 s per row.** Nowhere in this repository; I could not
  reproduce any of them.
- **Frontier benchmark figures** (Opus 5.5 48.7 on OSWorld 2.1, 64.8% on Terminal-Bench).
  These come from web pages I read, not from receipts here. They are context, not evidence.
- **"Own weights."** There are no weights. The runtime is a Python program. Whether that
  satisfies "own model" depends entirely on the §2 reading, which I resolved as: weights
  may not be a fact lookup and the runtime may not call a model. A program whose knowledge
  lives in an inspectable store satisfies that reading. **This reading is my resolution,
  stated, not a fact.**

---

## 5. The real bottleneck (and it is not the grammar)

Measured on the last complete sweep (`/tmp/rel/g5.json`):

| stage | rows | share |
|---|---|---|
| NO_EDIT_SURVIVED_THE_PROJECT_SUITE | 12 | 27% |
| NO_RELATION_READ_FROM_THE_RUN | 16 | 36% |
| VERIFIED | 6 | 13% |
| HARNESS_BLOCKED_THE_SUITE | 5 | 11% |
| CHANGED_LINE_NEVER_EXECUTED | 2 | 4% |
| THE_NAMED_TEST_DID_NOT_FAIL_IN_THIS_SESSION | 4 | 9% |

Three separate bottlenecks, in order of size:

1. **The demand is not being read (16 rows).** Two causes, both found and partly fixed:
   the probe once *swallowed the site's exception* (now re-raises), and many failures are
   **assertions**, not exceptions, whose demand my reader still ignores. This is the
   largest addressable group and the one worth attacking next.
2. **An edit is found but the project's suite rejects it (12 rows).** The relation is
   often right in shape but wrong in detail. This is where the **store** is supposed to
   help, by pre-ranking relations that worked on other rows.
3. **The harness, not the tool (5 rows).** Missing pytest plugins (`ephemeral_port_reserve`,
   `trustme`, `tornado`, `trio`, `sniffio`, `certifi`, `uvicorn`). Fixing these took
   HARNESS_BLOCKED from **12 → 5** in one sweep, with no change to the tool. One row
   (`pluggy 4326ced2`) is **unfixable by dependency install**: the row tests pluggy itself
   and needs the *historic* pluggy API, which the interpreter's installed pluggy no longer
   has.

**The honest conclusion: the binding constraint is reading the demand and surviving the
suite, not the size of the relation vocabulary.** Adding a 20th relation would not move
the number much. Making the demand reader handle assertions would.

---

## 6. Distance to §6, criterion by criterion

§6 DONE requires all of these **at once**:

| criterion | status | what exists |
|---|---|---|
| own weights | **NOT MET** | none; runtime is a Python program |
| instant-knowledge store, zero model calls | **PARTIAL** | the store exists and is inspectable; `model_calls=0` is true because no model is ever called |
| hardest computer-use benchmark | **NOT MET** | no GUI perception of any kind; the "agent" is a 10-row shell table |
| hardest SWE benchmark | **NOT MET** | no SWE-bench or Terminal-Bench run has ever executed; Docker/Harbor absent in this sandbox |
| never-seen environments | **NOT MET** | no adapter exists to enter one |
| single-experience learning | **UNDER TEST** | store + ablations built; verdict pending |
| memory ablations (store vs empty; generalized vs raw) | **UNDER TEST** | three-arm harness built and running on real rows |

**Therefore: this is progress, not §6. I will not claim §6.**

---

## 7. What I got wrong this session (recorded so it is not repeated)

1. **The probe swallowed exceptions.** `except BaseException: return ()` — and before that
   `return True` — turned `builder.add_init()`'s `ValueError` into a passing test and a
   silent success. It cost a row its failure and would have forged verdicts indefinitely.
   Fixed: **re-raise, always**.
2. **Zero-argument `super()` inside a lambda** raises `RuntimeError: super(): no arguments`.
   The probe created an error the project never had, and the row reported the probe's own
   exception as the project's message. Fixed: never instrument bare `super()`.
3. **Tuple sites cannot be wrapped.** `lambda: a, b` parses as a two-element tuple whose
   first element is a lambda, so a function returning `value, key` returned a bare bool.
   Fixed: refuse `Tuple`/`List`/`Set` sites and any expression whose result is unpacked.
4. **The site enumeration was quadratic** — 79 s on one 3 000-line file, from
   `ast.get_source_segment` re-splitting the file and `_shadows_probe` re-walking the tree
   per site. Fixed: 3.5 s, identical output.
5. **I wrote a helper named `_conjuncts` whose regex was mangled by the shell**, so it
   silently returned `[]` and the new relation never fired. Caught only by testing the
   helper directly.

Each of these produced a *confident wrong answer* before it produced an error. That is the
pattern to fear, and the reason every stage name in this tool is a refusal rather than a
success.

---

## 8. What to do next, in order

1. **Read assertions as demands.** 16 rows and growing; the reader currently handles only
   exceptions and `pytest_assertrepr_compare`. `assert not flag or required` gives a
   conjunct directly from pytest's own assertion introspection.
2. **Finish the ablation** and report the real numbers, including if GENERAL loses to EMPTY.
3. **Kill the false agent or make it true.** `computer_use_agent_v1` must either perceive
   something (screenshots → text, at zero model calls) or be deleted and its claims
   retracted. A 10-row table labelled "computer use" is worse than nothing.
4. **Get one live benchmark run**, even a partial one. No §6 claim can be made without it,
   and the sandbox lacks Docker — so the terminal-bench-compatible subset that can run
   without containers must be identified, or the blocker recorded as a hard external limit.
