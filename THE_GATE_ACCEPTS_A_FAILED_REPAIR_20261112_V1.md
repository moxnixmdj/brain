# The gate accepts a failed repair

**2026-11-12.** Base `fea6498c`. Branch `arena/1399c02c-brain`. Round 6.

Round 5 argued from source text that nine repair capabilities accept on `output_verified` while the
answer sits in `pass`. This round does not argue. It builds a workspace whose only test **cannot be
satisfied**, runs the adapters for real, and applies both predicates to the object each one
returned.

```
adapters executed                                        8
reported the honest answer (pass == False)               8
set output_verified == True anyway                       8
the REGISTERED predicate accepted the failure            8
the CORRECTED predicate (pass == True) rejected it       8
...with 'pass' declared in the capability's result_fields 8
```

| capability | adapter says | registry says |
|---|---|---|
| `python.patch.search.test_guided.ast.v1` | `OPEN__NO_VERIFIED_CANDIDATE_IN_BOUNDED_SEARCH` | **ACCEPTED** |
| `python.software.repair.loop.coupled.ast.v1` | `OPEN__NO_VERIFIED_REPAIR_IN_STRICT_OR_COUPLED_BOUNDS` | **ACCEPTED** |
| `python.software.repair.loop.strict_progress.ast.v1` | `OPEN__NO_STRICTLY_IMPROVING_CANDIDATE` | **ACCEPTED** |
| `python.software.repair.loop.test_guided.ast.v1` | `OPEN__NO_VERIFIED_PATCH_IN_BOUNDED_LOOP` | **ACCEPTED** |
| `python.software.repair.guided.provenance.coupled.v1` | `OPEN__NO_VERIFIED_REPAIR_IN_GUIDED_BOUNDS` | **ACCEPTED** |
| `python.software.repair.measured_acceptance.v1` | `OPEN__NO_VERIFIED_REPAIR_IN_BOUNDED_SEARCH` | **ACCEPTED** |
| `python.software.repair.semantic_acceptance.v1` | `OPEN__NO_VERIFIED_REPAIR_IN_BOUNDED_SEARCH` | **ACCEPTED** |
| `python.software.request.semantic_behavior.compile.v1` | `OPEN__SEMANTIC_RESIDUALS` | **ACCEPTED** |

The fixture is `def square(x): return x` against `assert square(3) == 999`. No single AST mutation,
no test-literal substitution and no bounded two-edit pair reaches 999 from `x`. The adapters are not
broken — every one of them answers honestly and says so in a status string. **They then set
`output_verified = True` because writing the answer file succeeded, and the registry accepts on that
field.**

Authority **NONE**. Executed, deterministic, ~4 seconds, `model_dependency_count: 0`,
`incremental_spend_usd: 0`. Nothing re-registered, no predicate repointed in this PR.

---

## 1. What this means for "learn it once and keep it"

The thesis under test is: *give the model the most advanced actions, let it experience each once,
and it learns them permanently; therefore everything on a computer becomes solvable.*

That decomposes into three claims, and this repository can now answer all three from its own
measurements.

**(a) "One demonstration teaches the procedure."** Largely **true**, and the strongest true part.
Round 2 measured 14.1 of 47 programs surviving a single demonstration. AhaBench found worked
procedures reaching 78.6–100% on held-out variants against 0–73.9% for answer-only priors. One
demonstration really does carry a lot of procedural information.

**(b) "Once is enough to identify which procedure."** **False**, measured. After one demonstration
the leader was the right program **10%** of the time and **0 of 10** were exact. Three
demonstrations moved that to 80% and 5 of 10 exact. One demonstration plus two *chosen* questions
settled 10 of 10 at a cost of 2.0 queries. The binding is the demonstration, but the *identification*
is the cost — and nothing about "give it a try" pays that cost.

**(c) "Once learned, it is permanent."** **False as currently wired**, and this is the round's
finding. Permanence is a claim about an acceptance test: you can only call a lesson kept if
something later says it still works. In this tree, for the eight executables above, the thing that
says it worked is satisfied by a file having been written. **A lesson marked permanent by that gate
is permanently wrong.** This is not a modelling limit; it is `expect.field` pointing at the wrong
key, one line per capability.

## 2. Why "give it a try in all environments" is the wrong next move

Round 3 counted 60 of 145 capabilities structurally able to learn from one try, and 29 typed but
unchecked — no independent verification at all. Adding exposure preferentially fills those 29 cells,
because they are the ones that will say yes. That is not learning faster; it is manufacturing
evidence at the rate you can produce receipts. The same census put 20 receipts on disk that nobody
attributed.

The environment side has its own version of the same trap. Agent S4 (arXiv:2610.28601) shows
interface evolution worth 3.8× fixed-interface OSWorld V2 performance (5.6% → 21.3%, GPT-5.5 13.0%,
Opus 4.8 20.6%) — but that gain comes from *held-out selection*, i.e. paying for the identification
in (b), not from more tries. And *The Verification Horizon* (arXiv:2606.26300) says a fixed reward
stops being valid as the policy improves. More environments make the reward problem worse, not
better.

## 3. The limiting factor, named

> **The bottleneck is not the action set and not the number of environments. It is that the
> acceptance predicate asks whether a file was written.**

Every downstream number in this tree — one-shot safe 41%, 113/145 predicate-passing, the 5/5 false
success repaired by hand — was computed through that gate. Fixing the gate is one line per
capability and it is the cheapest real progress available.

## 4. Ranked next moves, each falsifiable

1. **Repoint the nine.** `expect.field: output_verified → pass`, with this probe as the regression
   test (it already runs in seconds). *Falsified if* the probe's `corrected_rejects_the_failure`
   drops below `ran`.
2. **Re-run Round 3 after step 1.** *Prediction:* the one-shot-safe count **falls** from 60. If it
   does not fall, either the repoint was cosmetic or Round 3's independence detection is broken.
   Either answer is worth more than the number.
3. **Read the 46 candidates** from Round 5 — the 11 undeclared-outcome cases first, since that is
   the same declaration-mismatch defect already proven in `task.acceptance.objective.lossless.v1`.
4. **Pay for identification instead of exposure.** Round 2's result is explicit: three
   demonstrations, or one demonstration plus two chosen questions, moves program identification
   from 10% to 80–100%. Nothing in the environment story competes with that per unit of cost.
5. **Only then** widen the action surface.

## 5. Receipts

```
python3 gate_accepts_a_failed_repair_probe_20261112.py --list
canonical/tests/test_gate_accepts_a_failed_repair_v1.py     9 tests, all passing
```

The tests pin the fixture as genuinely unsatisfiable — so a future edit cannot quietly make the
test passable and turn this into a measurement of nothing — and pin both halves of the defect: the
adapters must keep answering honestly, and the registry must keep accepting them. When the defect is
fixed, `test_the_registry_predicate_accepts_every_one_of_them` is the test to delete, deliberately.

## 6. Non-claims

Only the **failure** path was executed. Nothing here says a real repair would be accepted or
rejected correctly, and the adapters' internal verification was not audited. One of Round 5's nine
definite cases is not executed: `python.task.acceptance.measured.objective.v1` needs a
content-addressed measurement receipt that cannot be fabricated honestly, so it stays an inference
from static reading. No capability re-registered, no predicate repointed, no family flipped,
`truth.achieved` false, $0, zero model.
