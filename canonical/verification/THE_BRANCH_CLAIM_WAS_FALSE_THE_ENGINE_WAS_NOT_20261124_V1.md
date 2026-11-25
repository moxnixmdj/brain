# The branch claim was false; the branch's engine was not

**Measured 2026-11-24.** Receipts: `THE_BRANCH_UNION_RECEIPT_20261124_V1.json`
(mine), `/tmp/rel/theirs_full.json` (theirs, reproduced), and the pre-existing
`intake/RECEIPT_THE_DEMAND_IS_LEARNED_FROM_THE_RUN_20261121_V1.json`.

## The claim, checked

The incoming plan opened with Pillar 0: merge seven branches, the first of which is
`arena/aab1b545-brain` at **"45/45 = 100%"** on the 45-commit corpus. My own measurement
on the same corpus the same day was 10/45. Both cannot be true.

The branch's own committed receipt
(`intake/RECEIPT_THE_DEMAND_IS_LEARNED_FROM_THE_RUN_20261121_V1.json`) says:

```
stages: VERIFIED 13, NO_SEPARATING_RULE 31, NO_FAILING_TEST 1
L2_real_witness_and_control: 44
authority: NONE__PRODUCER_RUN_SANDBOX
```

**13/45, not 45/45.** The commit message and the plan both overstate by 32 rows. The
`L2: 44` figure in the same receipt is also not a verification count. Per §0/§1.10 the
claim is **FAILED**, and any plan step whose justification is "we already reach 100%"
should be re-derived from scratch before being acted on.

## The branch's engine, checked — and it is better than mine on a whole class

Having rejected the claim, the underlying engine had to be judged on its own merits,
because it is not the engine the claim was attached to and it is not a re-run of mine.
`canonical/tools/the_demand_is_learned_from_the_run_v1.py` (989 lines) does something
structurally different:

1. refuse the row unless the human edit alone flips the failing tests on the project's own
   suite (the control);
2. instrument **every boolean-position guard** and record each value's type-level features
   (None, truthiness, zero, empty literal, size, builtin type) *together with the pytest
   node that reached it*;
3. score each feature by how well its truth value **separates failing nodes from passing
   nodes at that one guard site**;
4. compile the best-separating feature into a guard expression and accept only if it flips
   every test the control flips and breaks none.

The human edit is used to validate the judge. It never selects, compiles or ranks a
candidate — the candidate is named by a pass/fail separation score computed from the
run's own probed values. I checked this in the source rather than taking it on trust.

**Reproduced independently** on four of the rows my engine misses, from a clean worktree
of that branch, with my own corpus file and my own repo clones: 3/4 VERIFIED in 29.3 s,
each on its **first** candidate and first attempt. The edits it learned are the human's
edits: `name != "__version_info__"` (attrs a08bfb90),
`hasattr(iterable, '__reversed__')` (more-itertools cca32949),
`self.get_plugin(ep.name)` (pluggy e108fa44). The fourth (werkzeug 3a408edf) returns
`NO_ORACLE` on my clone.

## The measured union

| engine | verified | of 41 |
|---|---|---|
| mine (`the_relation_is_read_from_the_failing_run_v1`) | 10 | 24.4% |
| theirs (`the_demand_is_learned_from_the_run_v1`) | 11 | 26.8% |
| **union** | **17** | **41.5%** |

Overlap is **4 rows**. Each engine has rows the other cannot reach:

- theirs only (7): `223561a8`, `40830087`, `a08bfb90`, `bf1e8be9`, `cca32949`,
  `d340b0c1`, `e108fa44`
- mine only (6): `0625596e`, `08bb0477`, `189a76d5`, `258202ed`, `3b0378dd`, `8af75907`

That is the strongest result of the session and it cost one merge, not one invention.

## What this corrects in my own previous conclusion

I wrote, and committed, that "generation is the only lever and the corpus is close to
exhausted", and I classified `cca32949` (`hasattr` → `getattr(x, k, None)`) and
`3a408edf` (`if final:` → `if not static:`) as **not derivable from a failing run**.
That was wrong, and the error is specific and worth naming:

- I looked for the fix's **vocabulary** in the run's evidence (`copy`, `getattr`, the new
  literal) and concluded that when the vocabulary was absent the row was unreachable.
- The correct question is whether the **decision** at the fault site can be separated from
  the passing runs. `cca32949`'s guard is `hasattr(...)`; the probe records whether that
  guard took its true branch under failing nodes versus passing nodes, and the separation
  is what names the repair — no `getattr` token needs to appear anywhere in the evidence.

So "never generated" was a true statement about *my* generator and a false statement
about what a run contains. The distinction that matters is **vocabulary reach** versus
**decision separability**, and only the first one is a wall.

What survives: the store conclusion. Union or not, the correct answer still has to be
generated before any ranking can matter, and the store still changes zero outcomes.
What does not survive: "mostly exhausted" and the two not-derivable classifications.

## Next

Integrate, do not reimplement. The engine that wins these rows is a guard-probe
classifier; the engine that wins mine is a relation over runtime values and source
literals. They see different things at the same fault site, so the correct design is one
engine that runs both candidate generators over the same row and takes the union of
candidates under a single judge. Reimplementing 989 lines of guard probing inside my
relation DSL would be the "worse boundary" — duplicated instruments, two instrumentation
paths to keep honest.
