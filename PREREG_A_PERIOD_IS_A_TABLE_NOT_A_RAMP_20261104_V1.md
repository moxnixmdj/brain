# PRE-REGISTRATION — *A period is a table, not a ramp*

2026-11-04, V1. Written **before** implementation, after measuring a defect in my own previous merge.
Base `40708bd0`. Branch `arena/11714ee7-brain`.

---

## What my own last round actually inducted

Last round's headline was "the operator basis grows by induction", with `x mod k` at 150/150 held-out
for periods 4 through 44. Re-reading the body that induction emits:

```python
def run(x0):
    return x0 - math.floor(x0 / P) * P
```

`P` is filled in. The *shape* is a hardcoded template. So what was induced is **one integer inside a
fixed form**, not a new operator. My result note called it "an operator that did not exist before" —
that was too generous, and I am correcting it here.

Measured consequence, immediately:

```
test function: period 3, within-period values [5.0, -2.0, 7.0]
  status: NO_CONSISTENT_HYPOTHESIS
```

A perfectly periodic function — period 3, three arbitrary values, then it repeats forever — is
**refused**, because `x mod 3` is a *ramp* and this function is not. The previous round's "induction"
would recover `x mod k` and nothing else, while reporting success in general terms.

This is the seventh or eighth appearance of the same defect, in the place I least expected it: I had
hardcoded the answer's *shape* and congratulated myself on computing its *parameter*.

## The deeper question this raises

Which of my learned objects are genuinely hypotheses and which are memories wearing a hypothesis's
clothes? I measured that distinction rather than assuming it:

| object | what it claims | falsifiable off its evidence? |
|---|---|---|
| the old 2/10 lookup | nothing beyond observed pairs | no — that was the bug |
| induced `x - floor(x/P)*P` | periodic with period P **and ramp-shaped** | only for ramps |
| a period **table** `[v0..v_{P-1}]` | `f(x) = v[x mod P]` for all x | **yes, at any input** |

A period table built from three questions scores **150/150** on held-out inputs `-90..-1` and
`200..259`, predicting `f(-1) = 7` and `f(500) = 7` — inputs it never saw. It is not a memory of the
evidence; it is a claim about infinitely many inputs, which any single counterexample would kill.

So the right generalization of "period" is not a parameter in a ramp. It is a **period-`P` table
together with the induction principle that says the table repeats**.

## What I will build

1. **`induce_periodic_table`** — given evidence, find the smallest `P` that explains it, then emit an
   organ whose body is the observed block `[v0..v_{P-1}]` indexed by `x mod P`. This is a hypothesis
   about all integers, verified exactly as before at `2P` and `3P`.

2. **Verification that a table cannot fake.** Before crystallizing, the table is tested against the
   fixed point of its own claim: the block must be *exactly* periodic in the collected evidence, not
   merely consistent with the points that happened to fall in it. Where a ramp and a table disagree,
   the evidence decides between them — neither is preferred.

3. **A named boundary for compactness.** A table with `P` entries is `P` units of description. If `P`
   approaches the number of observations, the "induction" is memorization and must be reported as such
   rather than dressed as structure. The threshold must be stated and measured, not silently chosen —
   the last round's fixed threshold of 16 turned out to be a hard ceiling on learning, and I will not
   repeat that.

## Predictions — stated so they can fail

- **P1 (the refusal becomes a capability).** The arbitrary periodic function above — period 3, block
  `[5,-2,7]` — must crystallize and score ≥95% held-out. *Falsified if it still refuses.*
- **P2 (ramps are not lost).** `x mod k` must still work for k ∈ {4,5,7,8,10,11,15} at ≥95% held-out.
  *Falsified if the general form breaks the special case it replaced.*
- **P3 (the table is a hypothesis, not a memory).** Held-out inputs far outside the evidence
  (`-90..-1`, `200..259`) must be predicted correctly. *Falsified by any drop on unseen inputs.*
- **P4 (memorization is refused).** A function with no repeating structure must not be crystallized as
  a long table that happens to cover the observations. *Falsified if `x*x` or `floor(x/7)` crystallizes.*
- **P5 (no timidity).** Determined problems (`x*y`, `7x-2y+12`) still crystallize. *Falsified if the
  change makes them refuse.*
- **P6 (the compactness threshold is principled, not a constant).** The point at which a table stops
  being an induction and becomes a memory must follow from the data, and the boundary must be measured
  and reported. *Falsified if behaviour flips at an unexplained fixed number.*

## Non-claims

- A period table is a hypothesis about *repetition*, and nothing more. It says nothing about functions
  that are not periodic, and those keep refusing.
- `SETTLED` and `INDUCED_OPERATOR_CRYSTALLIZED` remain relative to the evidence and the reachable probe
  space. Not truth. `truth.achieved` false, `authority: NONE`, $0.
- I will not describe a filled-in template as "a new operator" again. If what is induced is a parameter,
  the note will say parameter.

## Why this is the deepest available layer

Two rounds ago the creature could not notice its own blindness. Last round it could acquire a
parameter. This round it acquires the *shape*: a period table is the first object this system will hold
that is not a form I wrote down — the block of values is whatever the world put there, and the only
thing the creature contributes is the claim that it repeats. That is the smallest honest instance of
`Ω_{t+1} = Ω_t ∪ P_t` where the *structure*, not just a number, came from experience.
