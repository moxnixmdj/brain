# A period is a table, not a ramp

Result note, 2026-11-04. Base `40708bd0`, branch `arena/11714ee7-brain`.
Pre-registration: `PREREG_A_PERIOD_IS_A_TABLE_NOT_A_RAMP_20261104_V1.md`.

---

## What my own last round actually built

Last round's headline was *"the operator basis grows by induction"*. Re-reading the body that
induction emits:

```python
def run(x0):
    return x0 - math.floor(x0 / P) * P
```

`P` is filled in. **The shape is a template I wrote.** So what was induced is one integer inside a
fixed form, and my phrase "an operator that did not exist before" was too generous. It is corrected
here, and the correction is not cosmetic — it is measurable.

```
test function: period 3, within-period values [5.0, -2.0, 7.0]
  status: NO_CONSISTENT_HYPOTHESIS
```

A perfectly periodic function — period 3, three arbitrary values, repeating forever — was **refused**,
because `x mod 3` is a ramp and this function is not. The previous round's induction could recover a
ramp and nothing else, while reporting success in general terms.

This is the same defect as every round before it, in the place I least expected: I had hardcoded the
answer's *shape* and congratulated myself on computing its *parameter*.

## The distinction that matters

| object | what it claims | falsifiable off its evidence? |
|---|---|---|
| the old 2/10 lookup | nothing beyond observed pairs | no — that was the bug |
| induced `x - floor(x/P)*P` | periodic with period P **and ramp-shaped** | only for ramps |
| a period **table** `[v0..v_{P-1}]` | `f(x) = v[x mod P]` for all x | **yes, at any input** |

A table is not a memory of the evidence. It is a claim about *infinitely many* inputs, and a single
counterexample kills it — which is precisely what the lookup could not be killed by, because it
asserted nothing.

## What changed

**`settlement_v1`**

- `induce_periodic_table` — finds the smallest period whose block explains the evidence exactly, and
  returns the block. The values are the world's; the creature contributes only the claim that they
  repeat.
- `table_evidence_requirement` / `candidate_period` — the period is *visible* long before it can be
  *claimed*, so the requirement is queryable and a caller can budget for it instead of discovering it
  by failing.
- **Compression rule**: a block must be at most a quarter of the evidence. Without it, `x*x` over
  twenty points yields a "period 20" table with compression 1.0 — a restatement dressed as a structure.

**`meta_circular_organ_graph_v1`**

- `_table_body` emits a literal tuple indexed by a floored residue, so the body stays a pure organ.
- Growth now triggers from **every** failing door, not just `HELD_OUT_REFUTED`. `NO_CONSISTENT_HYPOTHESIS`
  is the strongest failure and was the shortest path out of the function — it is also the case where
  growing matters most.
- Two independent signals license growth: the structure classifier, **or** a table that already fits.
  Requiring the classifier alone made the table unreachable for exactly the functions it exists for.

## Measured, through the real path, from three seeds

| function | result | questions | held-out |
|---|---|---|---|
| arbitrary block `[5,-2,7]`, period 3 | INDUCED_OPERATOR_CRYSTALLIZED | 14 | **150/150** |
| `x mod 4` | INDUCED_OPERATOR_CRYSTALLIZED | 19 | 150/150 |
| `x mod 15` | INDUCED_OPERATOR_CRYSTALLIZED | 74 | 150/150 |
| `x mod 30` | INDUCED_OPERATOR_CRYSTALLIZED | 149 | 150/150 |
| `x mod 44` | INDUCED_OPERATOR_CRYSTALLIZED | 219 | 150/150 |

Held-out spans `-90..-1` and `200..259`. The block test asserts two *different* blocks of the same
period produce two *different* organs — if the body were a template with a filled-in period, both would
collapse to `x mod 3` and the test would fail.

Refusals that should stay refusals: `x*x` → `NO_CONSISTENT_HYPOTHESIS`, `floor(x/7)` →
`HELD_OUT_REFUTED_STRUCTURE_UNDIAGNOSED`.

## Pre-registration scored

| prediction | result |
|---|---|
| **P1** arbitrary block crystallizes ≥95% | **PASS** — 150/150 |
| **P2** ramps not lost | **PASS** — k=4…44 all 150/150 |
| **P3** table is a hypothesis, not a memory | **PASS** — predicts `f(-1)`, `f(500)` |
| **P4** memorisation refused | **PASS** — `x*x`, `x^3`, `floor(x/7)` all refuse |
| **P5** no timidity | **PASS** — `x*y` 40/40, `7x-2y+12` = 76 |
| **P6** threshold principled, not constant | **PASS** — requirement is `4 × period`, queryable |

## Four bugs found by measurement inside this round

Each was caught by a test failing, not by reading the code:

1. **Unbounded budget escalation.** Recomputing the budget from the straight-run length every iteration
   made the budget raise itself: 61 questions and still climbing, with the period sitting in the
   evidence the whole time. Now: one escalation, capped at twice the base.
2. **Self-contradictory evidence.** Anchoring the probe on a fixed seed while incrementing a counter
   re-probed held points and appended them with different values — `(2, 5.0)` then `(2, 7.0)`.
   Contradictory evidence destroys every hypothesis downstream and looks exactly like "no structure
   here", which is the most expensive misdiagnosis available.
3. **Reported cost understated the questions asked.** The top-up loop collected evidence without
   incrementing the spend — an error in the one number a caller needs to decide whether to continue.
4. **Frozen requirement never re-derived.** A single pass sized the requirement from a three-point
   sample and stopped at 60 points when a period-30 table needed 120. It now re-derives each round.

## The honest limit

Inducing a period table of size `P` costs about `4P` observations plus `P` questions to acquire the
period. This is **evidence proportional to the structure**, and prior experience does not reduce it:
having learned `mod 4` does not make `mod 44` cheap.

What experience buys is the structure's **expressibility**. Before the table existed, no budget
suffices for `[5,-2,7]`, because no body in the grammar could express it.

## Non-claims

- A period table is a hypothesis about *repetition* and nothing else. Non-periodic structure still
  refuses, and that is correct, not a claim of unknowability.
- `INDUCED_OPERATOR_CRYSTALLIZED` means induced from this run's evidence and verified on held-out
  inputs it never saw. Not truth.
- I will not call a filled-in template "a new operator" again. If what is induced is a parameter, the
  note says parameter. This round induces a block, and says block.
- `truth.achieved` false, `authority: NONE`, $0, no neural weights, no external model calls.
