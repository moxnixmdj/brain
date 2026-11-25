# THE STATE OF THE BUILD: 8 ROWS, A NEGATIVE ABLATION, AND WHAT §6 ACTUALLY REQUIRES

**Date:** 2026-11-24
**Branch:** `arena/94363358-brain`, from `c4f529eb`
**Receipts:** `/tmp/rel/g11.json` (final sweep), `/tmp/rel/denominator_fixed.json` (denominator),
`/tmp/rel/ablation.json` (three-arm ablation)

---

## 1. The headline, with its denominator

**8 of 41 attemptable rows verified, every one landed inside the human's changed line.**

| repo | commit | human line | relation |
|---|---|---|---|
| attrs | `3b0378dd` | 451 | MATERIALISE |
| attrs | `a572c3a4` | 2025 | SIBLING_DISJUNCT |
| click | `1b0e19f5` | 2679 | GUARD_AGAINST_NONE |
| more-itertools | `71e070b3` | 4282 | PRESENCE |
| packaging | `189a76d5` | 92 | END_ANCHOR |
| packaging | `258202ed` | 38 | ANCHOR |
| packaging | `8af75907` | 69 | ANCHOR |
| packaging | `b80e6eb0` | 839 | PRESENCE |

**The denominator is 41, not 45, and it was measured, not assumed.** Four rows name a test
that does not exist at the parent commit even after the engine's own overlay protocol
(`TEST_ABSENT`). Counting them as misses would understate the tool; counting only the 8
would overstate it. 8/41 = 19.5%. The naive 8/45 = 17.8% is the number to quote if a
single figure is wanted, and both are reported.

---

## 2. The ablation is NEGATIVE, and that is the result

Three arms, same 8 rows, same order (`/tmp/rel/ablation.json`):

| arm | verified | skills admitted | verified rows that received a prior |
|---|---|---|---|
| EMPTY | 3/8 | 0 | 0 |
| GENERAL | 3/8 | 3 | 2 |
| RAW | 3/8 | 3 | 0 |

**Delta over EMPTY: +0 in both arms.**

The decisive detail: the two rows that received a `MATERIALISE` prior from the store
(`a572c3a4`, `1b0e19f5`) both verified — but **through relations the store never
suggested** (SIBLING_DISJUNCT, GUARD_AGAINST_NONE). The store's influence on the outcome
was exactly zero; the rows would have verified identically with the store empty.

**Therefore: single-experience learning is NOT demonstrated.** A store that admits skills
correctly, retrieves by shape, and still changes no outcome is a filing cabinet, not a
memory. This is the third §6 criterion to fail, and it must be stated plainly rather than
buried under the 8 verified rows.

Why it failed, concretely: the store ranks relations by the *demand shape* it saw before,
but the engine's difficulty is not in choosing among relations it already generates — it is
in **generating the right relation at all**. A prior cannot supply a relation that does not
exist. Making the store useful requires it to store the **generative move** (which fact in
the run licensed which edit), not the relation's name.

---

## 3. What the eight rows actually prove

Each is a genuine derivation from the failing run, not a table lookup:

- **SIBLING_DISJUNCT** (`a572c3a4`): the conjunct `a.on_setattr is not setters.NO_OP` is
  spelled out in a sibling `elif` six lines below the demanded guard. Found by walking the
  if-chain, extracting its `and`-clauses, and moving the clause nearest the `raise`.
- **END_ANCHOR** (`189a76d5`): `DID NOT RAISE InvalidMarker` + a `$`-anchored pattern.
  `$` matches before a trailing newline, so the rule accepts input it must reject.
- **GUARD_AGAINST_NONE** (`1b0e19f5`): the run renders `(env var: 'None')`; the guard's own
  body names `self.envvar`. The first hypothesis generated is character-for-character the
  human's edit.
- **MATERIALISE** (`3b0378dd`): the traced value is a generator where a sequence is
  required; `tuple(...)`.

None of these consult a model, a table of world knowledge, or a previous run.

---

## 4. The instrument's own defect ledger (this session)

Every one of these produced a **confident wrong answer** before it produced an error:

1. the probe swallowed the site's exception → a real `ValueError` became a passing test;
2. bare `super()` inside the probe's lambda → `RuntimeError: super(): no arguments`;
3. `lambda: a, b` parses as a tuple → a function returned a bare bool;
4. an unpacked expression was substituted → `cannot unpack non-iterable bool`;
5. `zip(...)` passed into a call was consumed by the probe → exhausted iterator;
6. a generator expression was consumed the same way → `1 == 2` instead of the real assertion;
7. f-string interior offsets are relative to the replacement field → source corruption,
   `'str' object has no attribute 'join__brain_rel__'`;
8. a `for` loop's iterable was assigned to a variable named `targets` and never checked →
   a pickle path died with `AttributeError: 'Attribute' object has no attribute 'init'`;
9. `return out` inside the ANCHOR branch made every later relation dead code for regex
   sites — END_ANCHOR was written, wired, ordered, and unreachable.

Six of the nine are the same law: **an observer that spends what it observes is not
observing.** The other three are "a branch that gives up must not give up for everyone."

---

## 5. §6, criterion by criterion — all seven

| criterion | status | evidence |
|---|---|---|
| own weights, zero model calls | **PARTIAL** | no model is called (`model_calls=0` is true because none exists); "own weights" is unresolved — the runtime is a Python program with an inspectable store |
| instant-knowledge store | **FAILS AS A MEMORY** | built, runs, and changes no outcome (§2 above) |
| hardest SWE benchmark | **NOT MET** | 8/41 on a 45-row corpus of real single-line fixes; no SWE-bench Pro or Terminal-Bench run has ever executed here |
| hardest computer-use benchmark | **NOT MET** | no GUI perception exists; `computer_use_agent_v1` selects from a 10-row shell table by keyword overlap |
| never-seen environments | **NOT MET** | no adapter exists |
| single-experience learning | **NOT DEMONSTRATED** | negative ablation |
| memory ablations | **DONE** | run, reported, negative |

**§6 is not met. This is progress.**

---

## 6. Where the remaining capability is, in order of size

From the final sweep's 45 rows:

1. **NO_EDIT_SURVIVED (16 rows, 36%)** — the largest group. An edit was generated and the
   project's suite rejected it. This is where the store *should* help and does not, because
   the store lacks the generative move.
2. **NO_RELATION_READ (12 rows, 27%)** — the run's facts did not license any relation I have.
   Requires new relations, each derived from a real row.
3. **THE_NAMED_TEST_DID_NOT_FAIL (4)** + **CHANGED_LINE_NEVER_EXECUTED (2)** — corpus and
   coverage limits, not tool defects.
4. **HARNESS_BLOCKED (2)**, **THE_PROBE_BROKE_THE_RUN (1)** — now small thanks to installing
   the missing test dependencies (12 → 2) and to the re-raise law.

**The binding constraint is generation, not retrieval.** That is the opposite of what the
store was built to fix, and it is why the ablation came back zero.

---

## 7. What I will not claim

- I will not claim §6.
- I will not claim single-experience learning; the ablation says no.
- I will not claim any benchmark number. None has been run.
- I will not claim the computer-use agent works. It does not exist as anything but a
  keyword search over ten shell commands.
- The "75.2% of hunks outside fixed grammars" figure from the prompt is **unverified and
  contradicted** by this repo's own corpus: measured correctly, **9/45 (20.0%)** of these
  fixes introduce an identifier absent from the old line. My own earlier figure of 16/45
  was wrong — a parsing bug in my measuring script, not a property of the corpus.
