# Is the explanation count decided by the probe range?

Pre-registered 2026-11-04, **before** the measurement. Base `ebe3a1d5`, branch `arena/34a8f612-brain`.

## Why this and not instance eight

The last round closed the seventh instance of one defect class: a **frozen list standing where a
computation belongs** — regime predicates (round 11), vocabulary (round 12), rivals (round 14), the
constant alphabet (round 14 again). Each was found by noticing, by hand, that a table had been
answering a question a procedure should have answered.

Finding instance eight by hand would be the same work again with no new reach. The deeper question is
whether the class can be made **decidable**: is there a check that catches "this frozen list is
currently deciding an answer" without knowing in advance which list?

There is a candidate, and it sits under the newest result on this branch. `demand_evidence` reports
`DETERMINED` when every admissible program is *the same explanation*, and it decides "same" by
comparing behaviour over a **fixed 21-value probe range**:

```python
DISAMBIGUATING_PROBES = (-5, -3.5, -3, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2, 2.5, 3, 4,
                         5, 6, 7, 10, 12, 20)
```

Nothing outside −5…20 is ever sampled. So two functions that split at 100 and at 1000 are, by this
definition, the same explanation.

**Demonstrated on constructed bodies** (feasibility probe, not the measurement):

```
if x < 100:  return 1        vs   if x < 1000:  return 1
return 2                          return 2
merged by the standard probe range:    True     <- declared ONE explanation
split by probes derived from their own literals: True
```

Both are the same on every input anyone has observed. A report that calls them one explanation is
asserting a fact about functions from a fact about twenty-one inputs.

## The question

**Does this actually change a verdict on data the system meets, or is it a hole no one falls into?**

That distinction decides whether this is a defect to fix or a demonstrated-non-issue to record. The
honest answer requires measuring, over several real datasets, whether the explanation grouping
changes when the probe set is derived from what the bodies themselves can distinguish.

## Predictions

**P1 — a verdict flips.** For at least one of the datasets below, the explanation COUNT under a
probe set derived from the bodies' own literals differs from the count under `DISAMBIGUATING_PROBES`,
and for at least one of those the reported status changes. *Predicted: pass with low confidence.* I
have watched seven frozen lists each turn out to be load-bearing, and the range is narrower than the
literals the search emits — the `2x` run already produces 42 of 54 admissible bodies mentioning a
literal above 20. But I found **zero** flipped pairs in a first pass over `2x`, so I genuinely do not
know, and I am recording that I do not know rather than guessing confidently.

**P2 — where it flips, it flips toward certainty.** A larger probe set can only SPLIT groups, never
merge them, so it can only ever increase the explanation count. Therefore any flip is a case where the
system claimed `DETERMINED` (or a smaller ambiguity) than its own bodies support. *Predicted: pass —
this follows from the definition and is here so it can be checked rather than assumed.*

**P3 — the repair is cheap and does not change correct verdicts.** Deriving probes from the union of
(bodies' literals ± 1) ∪ `DISAMBIGUATING_PROBES` leaves every dataset whose verdict was already
correct unchanged. *Predicted: pass, but see P5.*

**P4 — this check generalises past probes.** The same shape of test — "recompute the answer with the
frozen dimension widened, and see whether the answer moves" — can be applied to the constant alphabet
and to the weight bound, and the three together cover every frozen dimension currently in the
decision path. *Predicted: pass; this is the actual deliverable, and the probe range is only the
first instance.*

**P5 — it will not catch everything, and I will say so.** Widening the probe set does not make the
grouping sound: there is no finite set of inputs that decides equality of arbitrary functions. A
report that stops saying "verified over the probe range" and starts saying "these are the same
explanation" would be **worse** than the current behaviour. *Predicted: pass — the boundary is real
and must appear in the report.*

## Falsifiers

- **F1.** No dataset flips. Then the probe range is not currently deciding anything, this is a
  demonstrated-non-issue, and I must record it as such rather than shipping a fix for a defect that
  does not manifest. A fix with no failing case before it is superstition.
- **F2.** The repaired grouping changes a verdict that was already correct. Trading a false
  `DETERMINED` for a false `PROVISIONAL` is not progress.
- **F3.** The wider probe set makes an existing test pass that was failing, or fail that was passing,
  for a reason unrelated to grouping. That would mean the probe set is entangled with something else.
- **F4.** The report begins asserting equality of functions rather than equality over observed inputs.

## What would count as a genuine gain

Narrowly: **a `DETERMINED` that the system can no longer justify is demoted to what the evidence
supports.** Not "more functions solved". If F1 holds, the genuine gain is the *negative* result plus
the reusable check, and I will report it that way.

## Non-claims, fixed in advance

- Probe widening is a **heuristic audit**, not a decision procedure. No finite sampling decides
  functional equality.
- `DETERMINED` would still mean only "one explanation over the inputs checked". It is not truth.
- Pure Python, small rational datasets, `$0`, no external model calls, no neural weights, no dynamic
  code execution outside the existing checked body compiler.
- `truth.achieved` stays false. No sentience claim.
