# A refusal must learn

Result note, 2026-11-04. Base `0827db4e`, branch `arena/f28951fa-brain`.
Pre-registration: `PREREG_A_REFUSAL_MUST_LEARN_20261104_V1.md`.

---

## First, a correction to my own last report

Last round I reported 700/700 held-out accuracy on the `x mod k` family and merged it. Then I measured
what the **creature** could do, as opposed to what a helper function could do:

```
grep settlement_v1 outside its own module and tests:
  VersionSpace      0 hits
  settle(           0 hits
  derive_probe_space 3 hits   <- all the organ graph ever used
```

`synthesize_periodic_organ` and `ConventionMemory` — the machinery behind that 700/700 — were called by
**no production code at all**. And the real path, `synthesize_or_disambiguate_skill`, returned:

```
k=4   HELD_OUT_REFUTED  no organ | helper=100/100
k=15  HELD_OUT_REFUTED  no organ | helper=100/100
```

So the honest summary of that round is: **I closed the door on confident lying and produced no
capability.** The creature became able to say "I can't", and stopped there. The 700/700 described a
function nothing called.

That is the defect this round repairs, and it is a deeper one than any frozen list, because it is the
difference between *reporting* honesty and *being* capable.

## The second correction: a constant was capping the structure

While wiring the growth loop I fixed the same defect three times in one afternoon, each time because a
number I had chosen was quietly deciding an answer:

| where it appeared | what it did |
|---|---|
| `acquire_period` accepting one agreeing point | `floor(x/3)` promoted to "period 2" from a single coincidence |
| `diagnose_structure` span test | four points at 1,2,3,−40 span 43, pass a span test for period 4, and agree vacuously |
| `diagnose_structure` provisional bound = 16 | collection stopped at sixteen consecutive points, so **period 20 was reported as a confirmed straight line forever** |

The last one is the important one. A fixed threshold is not a safety margin, it is a **ceiling on what
the creature can ever learn**. It is the frozen-table defect one level up: not a table of functions, but
a table of *how much evidence is enough*.

## What changed

**`canonical/runtime/settlement_v1.py`**

- `diagnose_structure` — classifies evidence as `PERIODIC` / `AFFINE` / `UNEXPLAINED` from the numbers
  alone. No name list, no template table, no branch on what the caller says the family is called.
  It diagnoses on the **densest contiguous run**, because evidence legitimately mixes probes from
  unrelated places and judging on the union makes a stray point look like a counterexample.
- `acquire_period` — **buys** the period with questions instead of reading it from a table, and verifies
  it at `2p` and `3p` before believing it.
- Affine readings are now `provisional` when the evidence is short. A short linear stretch is exactly
  what the first period of a cycle looks like; calling it a confirmed line is the same error as calling
  a sparse probe list a complete one.

**`canonical/swe_kernel/meta_circular_organ_graph_v1.py`**

- `_grow_operator_from_evidence` — the branch where failure becomes structure. Runs on evidence the
  run already paid for, then spends a **budgeted** number of questions before concluding nothing is
  there. Running out of budget is a refusal, not a licence.
- **`VersionSpace` / `settle` are wired into the real disambiguation decision.** Before this, the tree
  had two definitions of "settled" and exercised only one.

## Measured, through the real path, from three seeds

| period k | status | questions | held-out |
|---|---|---|---|
| 4 | INDUCED_OPERATOR_CRYSTALLIZED | 14 | 150/150 |
| 5 | INDUCED_OPERATOR_CRYSTALLIZED | 17 | 150/150 |
| 7 | INDUCED_OPERATOR_CRYSTALLIZED | 22 | 150/150 |
| 8 | INDUCED_OPERATOR_CRYSTALLIZED | 26 | 150/150 |
| 10 | INDUCED_OPERATOR_CRYSTALLIZED | 32 | 150/150 |
| 11 | INDUCED_OPERATOR_CRYSTALLIZED | 34 | 150/150 |
| **15** | INDUCED_OPERATOR_CRYSTALLIZED | 46 | **150/150** |
| 20 / 30 / 44 | INDUCED_OPERATOR_CRYSTALLIZED | 62 / 91 / 133 | 150/150 each |

Held-out inputs include negatives (`-90..-1`) and far positives (`200..259`), none of which the evidence
contains. `%` is still absent from the organ grammar; the operator is induced, not looked up.

And the refusals that *should* stay refusals do:

```
x*x          NO_CONSISTENT_HYPOTHESIS
x^3          NO_CONSISTENT_HYPOTHESIS
floor(x/7)   HELD_OUT_REFUTED_STRUCTURE_UNDIAGNOSED
```

## Pre-registration scored

| prediction | result |
|---|---|
| **P1** real path ≥95% on all seven instances from 3 seeds | **PASS** — 150/150 each |
| **P2** refusal no longer terminal | **PASS** — `INDUCED_OPERATOR_CRYSTALLIZED` with a `growth` record |
| **P3** one definition of settled | **PASS** — `VersionSpace` now on the real path |
| **P4** diagnosis is evidence, not names | **PASS** — 5/5 structural cases |
| **P5** no timidity | **PASS** — `x*y` 40/40, `7x-2y+12` = 76 |
| **P6** cost bounded and honestly reported | **PASS** — reported ≤ actually asked, bounded |

**Falsified during the round, and kept:** I first believed a threshold sweep showing "threshold 16 →
5/7". It was a stale-`.pyc` artifact; the true result was 7/7, and re-running deterministically three
times confirmed it. I also wrote a rule tying `provisional` to a span ratio which *reopened* the period-20
trap — the measurement caught it and the rule was replaced.

## The honest limit

The period is not free. Cost grows with structure: roughly `3k` questions for period `k` through this
path (k=4 → 14, k=44 → 133). This is **evidence proportional to the size of the structure**, and no
amount of prior experience reduces it: learning `mod 4` does not make `mod 44` cheap. What experience
buys is the operator's **existence** — before periodicity is induced, no budget suffices, because no
body in the grammar can express it.

Diagnosis covers periodicity and affineness. `floor(x/7)` and `x*x` currently refuse, which is the
correct behaviour for structures this creature cannot acquire, not a claim that they are unknowable.

## Non-claims

- Nothing here is sentience and I am not going to imply it is.
- `INDUCED_OPERATOR_CRYSTALLIZED` means *induced from this run's evidence and verified on held-out
  inputs it never saw*. It is not truth, and a family whose structure lies outside the diagnosed set
  still refuses.
- The previous round's 700/700 number described a helper nothing called. Where it is re-measured here,
  it is measured **through the real path** and labelled as such.
- `truth.achieved` false, `authority: NONE`, $0, no neural weights, no external model calls, no dynamic
  code execution in result-bearing paths.
