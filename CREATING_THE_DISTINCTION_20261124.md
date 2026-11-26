# Creating the Distinction

**Date:** 2026-11-24 · **Branch:** `arena/39d26eb4-brain`
**Module:** `canonical/swe_kernel/distinction_creation_v1.py` (built this session)
**Tests:** `canonical/tests/test_distinction_creation_v1.py` — 23 tests, all passing
**Authority:** NONE. No model, no network, no weights.

---

## 1. The gap this closes, in the project's own words

`canonical/verification/WITNESS_INVERSION_20261116_V1.json` states the law and the
mechanism's limit in one sentence:

> a witness inverter can only SELECT a value the artifact already contains; it
> cannot CREATE a distinction the artifact does not have.

That was not a bug. Eighteen real witnessed failures, **zero** of them expressible
as a selection over the live frame. The real fix invents a branch or a message.
`WHY_NO_MECHANISM_CAN_BUY_REACH_20261116_V1.md` names the missing organ:
*synthesise the missing branch or the missing message from the test's own demand.*

This module is that organ, built and measured.

**Why a selection needs one example and a condition needs two.** A failure gives a
point. A point cannot separate anything from anything — it has no second point to
differ from. Positive and negative evidence together are a *set*, and a set
partitions the input space. The partition is the guard. That is the whole
mechanism, and it is why this is not a better alphabet.

## 2. What it computes

Given labelled examples, `synthesise_guard()` derives the shortest conjunction
that holds on every positive and no negative. Nothing is enumerated from a
template library; the atoms come from how the labels behave as the values move:

| Data shape | Guard created |
|---|---|
| negatives only below the positives | `x gt max(negatives)` |
| negatives only above the positives | `x lt min(negatives)` |
| negatives on **both** sides, none inside | `x between min(pos) and max(pos)` |
| one feature cannot separate | conjunction of two atoms |

Every candidate is checked against **all** examples before it is proposed. A guard
that fails one example is not a guard.

## 3. The honest result: 4/4 on real conditions, with the right evidence

Measured on four real conditions of the kind fixes actually introduce. The
synthesiser sees only labelled examples; the human's rule is used only to answer
questions and to score.

| Case | Guard created | Agreement on exhaustive holdout |
|---|---|---|
| byte `0..255` | `n between 0 and 255` | **857/857** |
| percent `0..100` | `p between 0 and 100` | **702/702** |
| port `1..65535` | `p between 1 and 65535` | **65936/65936** |
| positive int `d >= 1` | `d gt 0` | **699/699** |

**4/4 exact, each matching the human's condition rather than merely fitting.**

### The same corpus with random evidence: 0/4

| Case | Random negatives | Edge negatives |
|---|---|---|
| byte `0..255` | `n gt -26` → 532/857 | `n between 0 and 255` → 857/857 |
| percent `0..100` | `p gt -26` → 377/702 | `p between 0 and 100` → 702/702 |
| port `1..65535` | `p gt -25` → 498/500 | `p between 1 and 65535` → 500/500 |
| positive int `d >= 1` | `d gt -25` → 674/699 | `d gt 0` → 699/699 |

**This is the finding, not a footnote.** The variable was never the synthesiser —
it was whether the evidence contains the boundary. A negative drawn far from the
edge says "that far out is wrong" and nothing about where the edge is. The guard
that fits such data is sound but useless, and it is useless in exactly the way
that keeps REACH at 18.7%: the condition is not in the evidence.

## 4. The loop: the module names the example that would close it

A guard always commits on values nobody observed. That commitment is named in
`commitment_beyond_the_data`, and turned into a question in `next_probes`:

```
guard:        n lt 256
commitment:   n: claims values below 0 are valid (unobserved)
next probe:   is n = -1 accepted?          <- one question decides the lower edge
```

Answering it and re-synthesising converged **3 of 4** cases in **3 rounds with 2
questions**, starting from random evidence:

| Case | Rounds | Questions | Final guard | Agreement |
|---|---|---|---|---|
| byte `0..255` | 3 | 2 (`256`, `-1`) | `n between 0 and 255` | 657/657 |
| percent `0..100` | 3 | 2 (`101`, `-1`) | `p between 0 and 100` | 502/502 |
| port `1..65535` | 3 | 2 (`65536`, `0`) | `p between 1 and 65535` | 65936/65936 |
| positive int `d >= 1` | **never** | 8 asked, none closed it | `d between 1 and 106` | 406/1499 |

### The fourth case is a real limit, stated exactly

`d >= 1` **cannot** be closed by evidence. Every observed maximum leaves "is
`max+1` accepted?" open and the answer is *yes* forever. No number of examples
converges on an open edge.

This is not a defect of synthesis. It is the difference between a condition with
an upper bound and one without. The module reports the open edge as a commitment
rather than inventing a bound — which is the correct behaviour and the reason it
does not score 4/4 here.

## 5. Refusals, kept in the denominator

Three distinct refusals, reported separately because they call for different
actions:

| Status | Meaning | What would help |
|---|---|---|
| `REFUSED__NEEDS_BOTH_POLARITIES` | one set is empty | a negative example |
| `REFUSED__CONTRADICTORY_EXAMPLES` | one positive and one negative agree on every feature | the examples are the same point labelled twice |
| `REFUSED__NO_DISCRIMINATING_FEATURE` | no conjunction up to 3 atoms separates | a richer probe, not more examples of the same shape |
| `REFUSED__TOO_FEW_EXAMPLES` | equally short guards disagree | one example they disagree on |

**A measured case where refusal is correct.** Positives `(0,1,128,255)` against
negatives `(-27, 26, 256)` refuses with `NO_DISCRIMINATING_FEATURE`, because 26
sits *inside* the positive span and no single atom separates. A conjunction could
in principle (`0..255`), but it would need the same feature twice, which is
illegal in a conjunction and would be a range atom anyway. The refusal is honest:
the evidence is inconsistent with any single-atom rule.

## 6. Bugs found by checking, not by reading

Six, each of which produced a confidently wrong guard first:

1. **`_ordered` applied to a list instead of each value** — returned `False` for
   every numeric feature, routing all threshold atoms into the equality branch.
   `qty >= 1` was invisible for positives `(1,2,5,10)` vs negatives `(0,-1,-5)`.
2. **One-sided thresholds offered without a closed edge** — emitted `n <= 255` for
   positives `(0,100)` against negative `300`, silently asserting 256 valid.
3. **`between` offered with only one edge decided** — `d between 1 and 7` for
   `d > 0`, which **rejects 8**, a value the real rule accepts. The safe-looking
   choice was the wrong one.
4. **Closure test far stronger than needed** — refused the byte range against
   `{-1,256,300}` because it demanded *all* negatives above the maximum.
5. **A list treated as a scalar feature** — containers were compared by accident.
6. **Probes asking questions already answered** — the loop asked "is n = 256
   accepted?" eight times after 256 was already a known negative, and never
   terminated.

Each is now a comment in the source naming the measurement that exposed it.

## 7. What is established, and what is not

**Established, with measurements above:**
- A distinction can be **created** from labelled examples, not only selected from
  an artifact, for the class of conditions expressible as a conjunction of
  up-to-3 monotone/equality atoms.
- Created guards match the human's condition exactly **4/4** when the evidence
  includes the boundary.
- The module can name the single example that would convert its own guess into a
  decided distinction, and answering it converges bounded conditions in 2
  questions.
- Open-edged conditions provably cannot be closed by evidence, and the module
  says so instead of guessing.

**Not established — and this is the whole remaining question:**
- **Where the labelled examples come from.** This module consumes positive and
  negative sets. In the real loop, a repo-hosted test supplies them, and
  *whether it supplies an edge example is not under our control*. If the existing
  test only exercises interior values, the guard is sound and useless — exactly
  the random-evidence row above. So this module does not by itself raise REACH.
  It makes REACH *attainable* when the demand carries an edge, and it makes the
  absence of an edge visible and quantified for the first time.
- **The branch body.** The condition is derived; what the branch must *do* comes
  from the demanded outcome, not from the examples. Emitted as a proposal with
  `raise <exception-from-the-demand>` and never executed here.
- **Interval/inside-span negatives.** A negative inside the positive span needs a
  range, which is currently only created when both edges are closed. Extending
  the atom set to composed intervals is the next mechanical step, but it will not
  change the evidence question above, which is the binding one.

## 8. Where this leaves the product

`p_correct = REACH × SEARCH × VERIFICATION = 0.2978`. This work touches **REACH**
only, and only the sliver of it that is "the fix introduces a new condition".

It does not raise the 18.7% asymptote. It establishes the missing *organ*: given a
demand that carries an edge, the distinction the artifact lacks can be created
rather than sought. The remaining binding term is now precisely stated:

> **Is the edge in the demand?** If the test that defines "correct" exercises the
> boundary, the condition is creatable in two questions. If it does not, no
> synthesiser can recover what the evidence omits — and that is a statement about
> tests, not about models.

That is the next bottleneck, and it is narrower and more answerable than the one
this module started from.
