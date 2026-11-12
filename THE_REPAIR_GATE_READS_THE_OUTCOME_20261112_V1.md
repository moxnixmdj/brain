# The repair gate reads the outcome

**2026-11-12.** Base `94a105fe`. Branch `arena/bd47cd30-brain`. Round 7.

Rounds 5 and 6 measured a defect and stopped short of fixing it. This round fixes it: nine
capabilities, nine lines.

```diff
   "expect": {
-    "field": "output_verified",
+    "field": "pass",
     "type": "field_equals",
     "value": true
   }
```

Registry-wide, `expect.field == "output_verified"` went from **99 to 90**, and `"pass"` from **9 to
18**. One family (software repair and repair acceptance), nine capabilities, no adapter touched, no
capability added, no tolerance widened.

## 1. Proof in both directions

The executed probe from round 6 is now a two-sided regression test. It builds a workspace whose only
test cannot be satisfied (`assert square(3) == 999` against `return x`), runs all eight repair
adapters for real, and applies two predicates to the object each one returned:

```
adapters executed                                          8
reported the honest answer (pass == False)                 8
set output_verified == True anyway                         8
the LEGACY predicate accepted the failure                  8
the LIVE registry predicate rejects it                     8
...with 'pass' declared in the capability's result_fields  8
```

The legacy predicate is kept **as a constant in the probe**, not as configuration. That matters: the
evidence for why the change happened has to survive the change, or the next reader finds a gate that
looks arbitrary. Delete the constant and the repoint becomes an unexplained preference; keep it and
the repoint is a receipt.

## 2. The blast radius, measured before shipping

Thirty-one test files reference the nine capabilities. Run them before and after the repoint, same
environment, same command:

```
before: 50 failed, 385 passed
after:  50 failed, 385 passed
diff of failure ids: empty
```

The 50 are pre-existing environment failures — this sandbox has no `numpy`, `pydantic`, `cadquery`,
`opencv` — not regressions. The full 2,442-file suite cannot be run faithfully here, so **CI is the
referee**; what this round establishes locally is that no test in the blast radius changes state.

## 3. Why history could not have told us

Before repointing, I tried to re-score every receipt in the tree under both predicates. 460 result
nodes carry `output_verified`; 83 of them also carry `pass`; **54 are accepted by both; the two
predicates disagree on zero of them.**

That is not a reassuring result, it is a sample of the evidence tree: **it keeps successes.** A
failed repair's receipt is not filed as evidence, so the failures that would have made the two
predicates disagree are exactly the ones that were never written down. History is structurally
incapable of measuring this defect. Only execution could, which is why round 6 had to run the
adapters instead of counting files — and why this round could be shipped on executed evidence and
not on a grep.

## 4. What this does to the numbers

Every headline figure this project has produced was computed through the gate this round changed.
The following are therefore **stale as of this commit** and must be re-measured, in this order:

| figure | source | expected direction |
|---|---|---|
| one-shot safe 60/145 = 41% | round 3 | **falls** |
| typed but unchecked 29/145 | round 3 | unchanged |
| runtime predicate pass 113/145 | round 3 | **falls** |
| 20 unattributed receipts | round 3 | unchanged |

**A falling number here is the correct outcome.** The 41% counted capabilities as "safe to learn from
one try" partly because their step predicate went green — and for the repair family it went green
because a result file existed. If the count does not fall after this commit, then either the repoint
was cosmetic or round 3's independence detection is broken. Both are worth knowing; neither is worth
guessing.

## 5. What is *not* fixed, stated precisely

Ninety capabilities still read `output_verified`. Most of them are right to: a file write, a tarball,
an archive, a copy — for those, "the artifact exists and its digest matches" **is** the outcome, and
there is nothing better to read. The defect was never "transport fields are bad". It is narrower:

> **A predicate is wrong when an outcome is computed and available, and the registry reads a
> transport field instead.**

Round 5 found 55 such candidates and 9 unambiguous ones. The remaining 46 are a reading list: eleven
read a field the capability does not even declare. Those are next, and each needs the same two-sided
proof this round used — a failing fixture, an adapter that answers honestly, and the registry
changing its mind.

## 6. Receipts

```
python3 gate_accepts_a_failed_repair_probe_20261112.py --list
python3 -m pytest -q canonical/tests/test_gate_accepts_a_failed_repair_v1.py \
                    canonical/tests/test_acceptance_predicate_target_v1.py     16 passed
```

## 7. Non-claims

Failure path only. Nothing here shows a *successful* repair is accepted, and no adapter was audited
for internal correctness. `python.task.acceptance.measured.objective.v1` is repointed but not
executed — it needs a content-addressed receipt that cannot be honestly fabricated. Round 3's census
has not been re-run; its numbers in §4 are predictions, labelled as such. No capability added, no
family flipped, no tolerance widened, `truth.achieved` false, $0, zero model dependency.
