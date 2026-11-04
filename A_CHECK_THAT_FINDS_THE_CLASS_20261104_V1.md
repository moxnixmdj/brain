# A check that finds the class, not the instance

Result note, 2026-11-04. Base `ebe3a1d5`, branch `arena/34a8f612-brain`.
Pre-registration: `PREREG_PROBE_RANGE_DECIDES_THE_VERDICT_20261104_V1.md`.

## Why this round was not instance eight

Eight defects on this project have had one shape: **a frozen list quietly deciding an answer that a
computation should have decided.**

| round | the frozen thing | what it was deciding |
|---|---|---|
| 11 | regime predicates | which families were admissible |
| 12 | vocabulary | which kinds could be named |
| 14 | rivals | whether an alternative was expressible |
| 14 | constant alphabet | which functions could be spelled |
| 14 | candidate budget | how many explanations exist |
| **now** | **the probe range** | **whether two programs are the same explanation** |

Every one was found by a person staring at a table. The move that matters is not finding the ninth;
it is asking whether the class can be **decided by a check**.

## The instance the check found

`demand_evidence` reports `DETERMINED` when all admissible programs are "the same explanation",
decided by comparing behaviour over a frozen list:

```python
DISAMBIGUATING_PROBES = (-5, -3.5, -3, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2, 2.5, 3, 4,
                         5, 6, 7, 10, 12, 20)
```

It runs to 20, and that reads like generous coverage. It is not — **it omits 8, 9, 11 and every
value from 13 to 19.** Two admissible bodies for `mod 2` agree at 20 of the 21 probes and disagree at
`x = 14`:

```
A: if x % 2 == 0: return (0 / x)      ->  0.0 at x = 14
B: if (100 % x) == 2: ...             ->  1.0 at x = 14
```

The system called them one explanation. So the number that decides `DETERMINED` was partly a
property of a 21-value list — the same structural error as the twelve-entry constant menu, and just
as invisible from the report.

**"Widen the range" would have been the wrong repair.** The list is sparse, not short; 14 is inside
the stated range. Probes are now derived from the literals the bodies themselves mention and from the
observed inputs, because those are the only places a piecewise body can change behaviour.

## The deliverable: `audit_frozen_dimensions`

For each frozen dimension in the decision path, recompute the answer with that dimension widened and
report whether the answer **moved**. Measured:

| dataset | load-bearing dimensions |
|---|---|
| `2x` (1..5) | probe_range, constant_alphabet, weight_bound |
| `3x+1` (1..5) | constant_alphabet, weight_bound |
| `mod 2` (1..9) | probe_range, weight_bound |
| `x*x` (1..5) | probe_range, weight_bound |

It rediscovers **without being told** both this round's defect (probe range) and last round's
(constant alphabet). That is the difference between fixing instance nine and removing the need to
find it.

"Load-bearing" is deliberately not the same as "wrong": a larger weight bound legitimately finds
heavier programs. What it means is that the reported verdict is a statement about the **frozen
value**, and must be reported that way rather than as a fact about the data.

## Pre-registration scored 5/5

| prediction | result |
|---|---|
| **P1** a verdict flips on real data | **PASS** — `mod 2`: 6 → 8 explanations |
| **P2** flips are monotone toward caution | **PASS** — 6→9, 1→1, 17→17; never a merge |
| **P3** a correct verdict is undisturbed | **PASS** — `3x+1` stays `DETERMINED`/1, split = 0 |
| **P4** the check generalises past probes | **PASS** — all four dimensions audited |
| **P5** the report does not overclaim | **PASS** — still "verified over the probe range" |

P1 was predicted with **low confidence and the prediction said so**. I had found zero flipped pairs in
a first pass over `2x` and wrote down that I did not know rather than guessing. The flip appeared only
on the third dataset I tried, and only over part of its domain — `mod 2` over 1..5 does **not**
over-merge; over 1..9 it does. That is recorded as a separate test, because the defect is a property
of the probe list *and* the data together, and naming only the function would hide it.

## What changed in the report

Every `demand_evidence` result now carries a `probe_disclosure` record:

```
groups_frozen:        6        <- what the frozen list said
groups_disclosed:     8        <- what the derived probes say
split_by_disclosure:  2        <- the size of what was being hidden
basis: "...an AUDIT, not a proof: no finite sampling decides equality of functions"
```

A number that was wrong is reported alongside its correction, not silently replaced.

## Verification

- **187 passed, 20 subtests** across 14 suites, including 14 new tests in
  `test_probe_range_decides_the_verdict_v1.py`.
- `repo_integrity_guard_v1`: mode `static+diff`, 17 rules, **0 violations**.
- Module findings unchanged: domain-of-verification **7/7**, hypothesis classes **14/14**, vocabulary
  induction **12/12**, discovered tests **10/10**, evidence demand **9/11**, observation refutation
  **8/9**. The three failures remain pre-registered failures kept intact.

## Non-claims, and the boundary that matters most

**No finite set of probes decides equality of arbitrary functions.** Widening the probe set does not
make the grouping sound. A future change that replaced "verified over the probe range" with "these are
the same explanation" would be *worse than the bug*, because it would launder a sampling result into a
claim about functions. P5 exists to prevent exactly that, and asserts the caveat is present.

- `DETERMINED` still means one explanation over the inputs checked, never truth.
- The audit's `stable` verdict means "did not move", not "proven sound".
- Four dimensions are audited because four are in the decision path today; a fifth frozen list
  elsewhere in the system would not be caught, and the audit does not claim otherwise.
- `truth.achieved` false. `$0`. No external model calls, no neural weights. No sentience claim.
