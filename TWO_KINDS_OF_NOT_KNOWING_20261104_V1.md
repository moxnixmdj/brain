# Two Kinds of "I Don't Know", and the One It Was Using

**2026-11-04 · round 11 · branch `arena/e55485af-brain` · authority NONE · `truth.achieved` false · $0**

Last round ended by naming the shape of the failure: both mechanisms die on the same input class, and
both die by **refusing to have a second kind of object**.

---

## 1. The measurement that started this

`relu` and `mod 2` — two functions every programmer writes without thinking:

```
relu : PROVISIONAL explanations=0   affine=INCONSISTENT  power=UNDERDETERMINED
mod2 : PROVISIONAL explanations=0   affine=INCONSISTENT  power=UNDERDETERMINED
```

`PROVISIONAL` means *ask me again*. But `affine` had already been **refuted** by the data. No further
observation can rescue an ontology with no class for the shape — the gap is in the *classes*, not in
the evidence. Telling the caller "give me more data" spends its only scarce resource on a question
whose answer is already known to be useless.

This is the same conflation I fixed one layer down last round. Same failure, same insight:
**"I stopped looking" and "it isn't there" are different reports.** Budget exhaustion and ontology
exhaustion are both absences; neither is a fact about the world.

So `ONTOLOGY_EXHAUSTED` is now a third status, distinct from `PROVISIONAL` (a class is one input
short — a real question) and `UNRESOLVED` (nothing fits and nothing could even be tested).

And the two findings do not outrank each other. `{(-2,0), (-1,0), (2,2)}` refutes `affine` on its
third point while `power` still needs one more non-zero ordinate — one observation away from
settling. My first fix declared that exhausted, which told the caller to acquire a new class when
a single observation would do. **Refuted and unpinned have to be weighed, not ranked.**

---

## 2. Composition, with the boundary searched

Both mechanisms fail on piecewise data because neither can hold a second object. The repair is not a
bigger grammar — it is a **split**:

```
relu        DETERMINED  branches=2  split_at=1/2
    if x <= (1 / 2):
        return 0
    return x

regime change at 2.5   DETERMINED  branches=2  split_at=5/2
    if x <= (5 / 2):
        return 2 * x + 1
    return 2 * x + 2

mod 2       ONTOLOGY_EXHAUSTED   branches=0
```

The boundary is **searched, not assumed**: cuts are taken at midpoints between adjacent observations,
so `x ≤ 1/2` and `x ≤ 5/2` are found as readily as `x ≤ 2`. A grid of whole numbers would have
missed both. That was the prediction I said would invalidate the whole result if it failed (P7); it
held.

Every composed body is compiled to source and re-verified against the search's own checker. A fit
that cannot be written as a program has not been reached.

---

## 3. The constraint that stops this from being a magic trick

The first working version composed **`mod 2`** — alternating zeros and ones — into two constant
branches and called it `DETERMINED`. That is the failure mode this whole arc exists to catch: a
mechanism fitting perfect matches by having as many parameters as it has observations.

A constant branch is "pinned" by **one** observation. So is a two-parameter branch by **two**. Let
that count as evidence and every curve becomes a hypothesis.

So a branch must be **pinned by more data than it has parameters**:

```
relu from 4 points  -> PROVISIONAL  needs=4
    cut 0.5  left  constant  surplus=0   one observation, one parameter
    cut 2.5  left  affine    surplus=0   two observations, two parameters
    cut 3.5  right constant  surplus=0
```

Every cut leaves some branch with zero degrees of freedom, so the answer is *"I need four
observations, two per branch with one to spare"* — a `needs` value computed from the structure, not
a refusal. With five points `relu` composes. With four it correctly declines.

`mod 2` never composes at any count, because alternating outputs are not a split of anything this
ontology contains. **A mechanism that fitted `mod 2` would be inventing a boundary to match its own
answers**, and P4 predicted it would not — asserted as a test, not hoped for.

---

## 4. Three more silent substitutions, all mine

**Same function, two names.** A zero-slope affine *is* a constant. Counting both reported two
explanations where there is one function — the 12-programs-one-function defect, one layer up.

**And the dedup kept the wrong survivor.** When two descriptions are the same function, keeping the
first in list order kept the *worst-supported* one: `affine` with `a=0` spends two parameters on two
points (zero spare) while `constant` spends one (one spare). The better description existed and was
being discarded, which left `relu` reported as short of evidence it actually had.

**A stale default disabled the feature.** `compose_and_verify` still defaulted to
`("affine", "power")` after `COMPOSITION_FAMILIES` gained `constant`, so `relu` failed while
`compose` succeeded on identical input. A default value is a place where a fix goes to die quietly.

All three are the pattern of this entire session: **one module naming a state differently from the
one that reads it**, and the comparison failing silently rather than loudly. `FITS` vs `DETERMINED`,
`pinned` vs `status`, `("affine","power")` vs `COMPOSITION_FAMILIES`. Every one was found by running
the thing and looking at a number that was absurd, never by re-reading the code.

---

## 5. Honest scoreboard

| input | string search | family layer | + composition |
|---|---|---|---|
| `3x+1` | 0 bodies at any budget | **fits** `{a:3,b:1}` | fits |
| `2x` from 3 points | 12 programs / 3 explanations | **1** explanation | 1 |
| `relu`, 5 points | 15 programs / 5 explanations | refuses | **`if x<=0.5: 0 else x`** |
| regime change at 2.5 | 50 interchangeable programs | refuses | **two branches, `5/2`** |
| `mod 2` | 107 programs | refuses | **refuses** |
| 4 points, real kink | produces something | refuses | `PROVISIONAL`, `needs=4` |

The composition adds reach only where there is structure to find. It refuses `mod 2` at every
evidence level, and it declines the 4-point kink while naming exactly what would settle it. Nothing
here replaces anything: the string search still produces candidates when no class applies, and the
family layer still does what one expression cannot.

**Non-claims.** No sentience. Two branches maximum, one input, three families — this is a small
ontology with a small composition operator, not a general mechanism. A composed explanation is a
guess that fits, and its boundary is only located to within the gap between adjacent observations —
the report says so. `mod 2` remains unexplained by everything in this repository; that is the honest
state, and next round should make it the target rather than pretend it is covered.

`truth.achieved` false. $0.

---

## 6. Ranked next moves

1. **Make `mod 2` the next target, deliberately.** It is the smallest function that defeats all
   three mechanisms, and the missing primitive is visible: a hypothesis about *structure* — a period,
   a parity, a discrete case — not about a curve. Adding it must come with the same constraint that
   killed the `mod 2` false positive: parameters must not outnumber observations.
2. **Let the boundary carry its own uncertainty.** Right now any cut between the same two
   observations fits equally and the report says so in prose. It should be a computed interval.
3. **Feed the composed program back into the epistemic layer** — `demand_evidence` and the refutation
   loop still only speak to the string search, so the newer mechanisms are not yet interrogated by
   the machinery built to interrogate.
4. Domain tracking; the front door.
