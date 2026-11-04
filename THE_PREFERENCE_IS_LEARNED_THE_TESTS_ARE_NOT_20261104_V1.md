# The Preference Is Learned. The Tests Are Not.

**2026-11-04 · round 13 · branch `arena/e55485af-brain` · authority NONE · `truth.achieved` false · $0**

Round 12 wrote down its own limit: *"recovery of a kind becomes possible when a test for that kind
exists, and writing the test is still my job."* This round takes that sentence seriously and reports
exactly how much of it can be moved.

---

## 1. What was moved, and what was not

**Moved:** there are now two structural tests (periodic, level) and a **record of discovery** that
decides which is tried first. Failed attempts are remembered, so the same blind retry does not happen.
The library's order is a function of its history, not of my typing order.

**Not moved:** I wrote both tests. This is *a preference among a fixed library*, learned from
outcomes. Calling it "the creature invents tests" would be false, and the writeup has to say so rather
than let a good-looking table imply otherwise.

The gain is real but conditional, measured:

```
five level targets      fixed order 10 attempts   record 6 attempts   SAVED 4  (40%)
mixed (periodic first)  fixed order  6 attempts   record 6 attempts   no gain
three periodic targets  fixed order  3 attempts   record 3 attempts   no gain
```

**The record buys nothing when the library's own order already happens to be right.** That second and
third row are asserted as tests, not merely mentioned, because a mechanism that reports a win on a
stream where it cannot possibly help is not measuring anything. With only two tests, and periodic
winning first, reordering *cannot* reduce attempts — and the measurement says so.

---

## 2. A defect found by adding a second test

The periodic test computes `x % period`. On `Fraction` inputs:

```
1.5 % 2 == 3/2
```

So every fractional observation becomes its own residue class, no partition is ever consistent, and
the test reported **`NO_STRUCTURE`** — which reads as *"there is no periodic structure here"*, when
the truth is *"this test is undefined on this domain"*.

That is the same conflation as `SEARCH_TRUNCATED` (a budget, not the world) and `ONTOLOGY_EXHAUSTED`
(a missing class, not missing evidence) — now reproduced **inside a single test**. Tests can now
answer `NOT_APPLICABLE` and it is distinct from `REFUTED`. The bug had been sitting there since round
12 without ever being reachable, because there was only one test and it was only ever asked about
integers.

---

## 3. Two targets that are actually different

```
mod 2   INDUCED  test=periodic   value repeats every 2 inputs
floor   INDUCED  test=level      value steps at each whole number, 3 steps

    import math as _m
    _k = int(_m.floor(x))
    if _k == 0:   return 1
    elif _k == 1: return 2
    elif _k == 2: return 3
```

Each test refuses the other target: periodic declines fractional inputs outright, level declines
`mod 2` as underdetermined. If one test had quietly handled both, the record would be sorting a
single item and every ordering measurement would be theatre. That is why it is a test.

Both bodies verify against the observations, and both were recovered where the string search offers
nothing useful — 75 interchangeable programs for `mod 2`, and period-3 data that the search cannot
spell at all.

---

## 4. A fourth silent shape mismatch

I passed the project's `((args,), value)` example form to a function expecting flat `(x, y)`. Every
point became unparseable and the library answered **`NOT_APPLICABLE`** — a considered-looking verdict
for data it could test perfectly well.

That is the fourth instance this session of *one module naming an input shape differently from the
one reading it*: the stale collection, the `repr` signature, the `FITS`/`DETERMINED` mismatch, the
stale default. Every one failed **silently**. The fix now validates arity and refuses loudly, and the
message names the reason ("these tests reason one input at a time"). The general lesson is not
"check your arguments"; it is that **a wrong-shaped input and a legitimate negative answer are
indistinguishable to the caller unless the callee says which one happened.**

---

## 5. Where this stands

| target | string search | class + composition | induced tests |
|---|---|---|---|
| `2x`, `3x+1` | 0 bodies / 12 programs | **affine, exact** | — |
| `relu`, regime change | 15 / 50 programs | **2 branches, searched** | — |
| `mod 2`, `mod 3` | 75 / **0** programs | exhausted | **periodic** |
| floor / step | 67 programs | exhausted | **level** |
| random points | 0 bodies | exhausted | **refused by every test** |

Four mechanisms now, each with a domain where it is the only one that works, and each with a domain
where it refuses. The refusals are the part I trust: `noise` is tried by every test and declined by
all of them, and the degrees-of-freedom constraint from round 12 is enforced centrally in
`_adjudicate` so no test can opt out of it.

**Non-claims.** No sentience. This is not test invention — it is preference among two tests I wrote.
`INDUCED` does not mean true: a level function fitted to six points could be wrong at the seventh,
and the body says what it will do there rather than hedging. The library has two tests and neither
composes with the family ontology yet, so nothing here explains `x*x + 1` or a periodic-within-a-regime
function. `truth.achieved` false. $0.

---

## 6. Ranked next moves

1. **The bottleneck is now visible and single.** Every round ends by naming the same thing: a test, a
   class, a primitive I typed. The only way to move it further is for the *inventory of tests* to be
   generated from the vocabulary recovered from survivors — `%` suggests partition, `//` suggests
   level, `*` suggests scaling — with the degrees-of-freedom constraint as the only admission rule.
   That is falsifiable: on a target whose vocabulary suggests a structure no test covers, it should
   propose one.
2. **Persist the record across processes** — still in memory, still forgotten on exit.
3. **Feed induced bodies into `demand_evidence`**, which still speaks only to the string search.
4. Domain tracking; the front door.
