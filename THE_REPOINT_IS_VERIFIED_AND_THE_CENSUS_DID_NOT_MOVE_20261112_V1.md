# The repoint is verified, and the census did not move

**2026-11-12.** Base `d1b9c677`. Branch `arena/bd47cd30-brain`. Round 7.

Two things happened that this note has to keep separate, because they have different owners and
different strengths of evidence.

**Someone else repointed the gates.** `#6678` moved eight repair capabilities from
`expect.field = output_verified` to `pass`, on the strength of the round-5/round-6 finding. That is
in `main` already.

**This round tried to do the same thing and then checked its own prediction.** The prediction was
wrong, and the way it was wrong is worth more than the repoint.

---

## 1. Independent verification of the repoint

I rebuilt the round-6 probe as a **two-sided** test: the predicate as it stood is kept as
`LEGACY_EXPECT` (data in the probe, never read back into the registry), and the live registry is
evaluated beside it. Same unsatisfiable fixture — `assert square(3) == 999` against `return x` — same
eight adapters, executed:

```
adapters executed                                          8
reported the honest answer (pass == False)                 8
set output_verified == True anyway                         8
the LEGACY predicate accepted the failure                  8
the LIVE registry predicate rejects it                     8
```

And the claim is now about the code that decides, not about my restatement of it:

```python
from canonical.runtime.grounded_action_v1 import _check_expect   # what the runtime calls
_check_expect(expect, {"pass": False, "output_verified": True})  # -> (False, …)   8/8
_check_expect(expect, {"pass": True})                            # -> (True,  …)   8/8
```

A probe that re-implements `field_equals` proves the probe's opinion. `_check_expect` is the
function the runtime calls; both directions are pinned in `test_gate_accepts_a_failed_repair_v1.py`.

## 2. The prediction that failed

Round 6's note said, in a table, that after the repoint the one-shot-safe count **must fall** from
60/145 = 41%, and that if it did not, "either the repoint was cosmetic or round 3's independence
detection is broken."

It did not fall. Re-running round 3's census against the repointed registry:

```
bound capabilities            145
typed interface               111
declares independence         107
  of which receipt on disk    78
one-shot safe (typed + receipted)      60  = 41%
```

**60 before, 60 after.** The census is unchanged by the repoint, and the reason is not that the
repoint was cosmetic — §1 shows it is not. The reason is that round 3's census never looks at which
field the predicate reads. It counts *a receipt existing on disk*. A capability can have an
independent receipt and a transport-shaped gate at the same time; those are different questions.

So the correct statement is the duller one, and it is mine to make because I got it wrong:

> **The census and the gate census measure different things, and neither implies the other.**
> A capability can be "typed + receipted" (60) and still have a gate that cannot fail (the eight,
> until 2026-11-12). The 41% was never a statement about gate quality, and reading it as one was an
> overreach — mine, in the previous round.

The useful consequence: **41% must not be re-derived as evidence for or against this fix.** It is a
receipt-existence figure. The gate question has its own number, which is 8 of 8, executed.

## 3. The ninth capability is left where it is, on purpose

Round 5 named nine definite cases. Eight are repointed. `python.task.acceptance.measured.objective.v1`
still reads `output_verified`, and this note does not change it — because it cannot be executed here.
It consumes a content-addressed repository measurement receipt, and a fabricated receipt is worse
than a transport field: it would produce exactly the kind of green that this whole series exists to
find.

It is pinned as the single remaining entry in `DEFINITE_DEBT`, with that reason written next to it,
and `definite <= DEFINITE_DEBT` still fails if anything new joins it.

## 4. Why history cannot adjudicate this

Before any of the above I tried to re-score every receipt in the tree under both predicates. 460
result nodes carry `output_verified`; 83 also carry `pass`; 54 are accepted by both; the two
predicates disagree on **zero** of them.

That is a property of the evidence tree, not of the system: **it keeps successes.** The failing
receipts that would have made the predicates disagree are precisely the ones never written down.
History is structurally incapable of measuring this defect, which is why rounds 6 and 7 had to run
adapters instead of counting files.

## 5. What is still true, and what to do

- The eight repair gates now ask the question the adapters answer. Verified twice, by two sessions,
  one of them against `_check_expect`.
- `DEFINITE_DEBT` holds one entry, with a stated precondition for removing it.
- Round 5's other 46 candidates are untouched: eleven read a field the capability does not declare,
  and the remainder offer a status string or an unthresholded score. Each needs the same two-sided
  proof — a failing fixture, an honest adapter, and the production checker changing its mind.
- 90 capabilities still read `output_verified`, and most are right to. For a file write or a tarball,
  "the artifact exists and its digest matches" **is** the outcome. The defect was never "transport
  fields are bad"; it is: *an outcome is computed and available, and the registry reads transport
  instead.*

## 6. Receipts

```
python3 gate_accepts_a_failed_repair_probe_20261112.py --list
python3 -m pytest -q canonical/tests/test_gate_accepts_a_failed_repair_v1.py \
                    canonical/tests/test_acceptance_predicate_target_v1.py     18 passed
python3 one_shot_regime_census_20261112.py                                     60/145, unchanged
```

## 7. Non-claims

Failure path only. No adapter was audited for internal correctness, and nothing here shows that a
*successful* repair is accepted under the new predicate beyond `_check_expect` returning True for a
`pass: True` dict. The ninth capability is not executed. The census is unchanged and is not evidence
either way. No capability added, no family flipped, no tolerance widened, `truth.achieved` false, $0,
zero model dependency.
