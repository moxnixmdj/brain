# The wall was reading its own label

**2026-11-12.** Branch `arena/99527820-brain`. Base `c9958189` (PR #6777). Authority **NONE**.
`truth.achieved` stays `false`. $0 incremental spend. Zero model dependency. No capability
registered, no family flipped, no gate touched, no tolerance widened.

The owner asked a fifth/sixth time: *why can't we just give the model the most advanced coding
actions and let it experience them once?* Ten documents answered that today. This one does not
answer it again — it corrects the **evidence base** every one of those answers was computed from,
and then reports exactly what survives and what does not.

---

## 1. What was actually wrong: the door overwrites the reason it already found

`live_brain_route_admission_v1._serve_by_acting` is a **carrier rule** (a statement about the
execution boundary) that fires as a *fallback* whenever a sentence names an output suffix the
program synthesizer can verify — `.json` mostly. When it fired, it returned a **new** result:

```python
acted = {"status": "FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT", ...}
acted["served_after"] = str(result.get("status") or "")   # the door's real reason, demoted
return acted                                               # ...and returned as THE answer
```

So a request that had already been refused for a specific reason — a path outside the workspace,
an unbound declared input, a chain that was not verified, a request most of which no capability
explains — reached the caller labelled **confinement**. The tree already had a law for this shape
(`canonical/tests/test_a_precise_refusal_is_not_replaced_by_a_generic_one_v1.py`, defect 2, fixed
2026-11-03 for one class) and a law-name for the consequence
(`A_REFUSAL_HAS_TO_SAY_WHICH_REFUSAL_IT_IS`). The carrier gate was the second instance.

## 2. The measurement (reusable, disposable clone, no refusal lifted)

`canonical/tools/which_refusal_is_actually_firing_v1.py` — the existing realistic probe prints
`status` and **throws away `served_after`**, which is precisely the field that says which refusal
fired. This tool reads it. Corpus: the 39 realistic advanced-coding sentences of
`realistic_goal_reach_probe_v1.py`. Run in a `git clone --no-local`.

```
carrier status on the caller-visible label          21 of 39     (reproduces the published count)
...of those, the door had ALREADY refused for a
   different, specific reason                       18 of 21
...of those, nothing had executed                    9
...of those, an earlier attempt reports
   executed / side_effects_may_exist                9      <- must keep the carrier answer
```

**The 18, by the reason that was being hidden:**

| the reason the door actually found | n |
|---|---|
| `STEP_RAISED_OUTCOME_UNKNOWN` | 6 |
| `ROUTE_ADMISSION_REJECTED` | 3 |
| `STATED_SWE_EFFECT_UNSERVED` | 3 |
| `MOST_OF_THE_REQUEST_IS_NOT_EXPLAINED_BY_CAPABILITY` | 1 |
| `COMPOSED_CHAIN_NOT_VERIFIED` | 1 |
| `STATED_PATH_OUTSIDE_THE_WORKSPACE` | 1 |
| `CAPABILITY_RETURNED_A_VERDICT` | 1 |
| `NO_OBSERVED_EFFECT` | 1 |
| `FAIL__RAW_GOAL_COMPILATION_GAP` | 1 |

Three rows never reached a decision at all (`file.copy.v1`, `file.rename.v1`,
`python.software.repair.apply.verified.v1`) and keep the carrier status — correctly, because it is
the only thing the door knows about them.

## 3. Why this mattered more than a count

Two documents merged **the same day**, from the same tree, reached opposite diagnoses of this one
wall:

* `A_PERFECT_ACTION_IS_NOT_AN_AVAILABLE_ACTION_20261112_V1.md`: *"the dominant failure mode is
  **binding**: 54 capabilities, 37%"*;
* `TWO_DOORS_COUNT_AVAILABILITY_DIFFERENTLY_20261112_V1.md`: *"no binding-shaped status exists at
  this layer (there is no `NOT_CALLABLE` at the door)"*.

Both were right about their own measurement and both were reading **labels**. A carrier label
standing in front of a binding refusal is how a chain of engineering gets aimed at the wrong seam
— the same error `THE_WALL_WAS_NOT_THE_WALL_20261112_V1.md` had to fix one layer down (where the
dominant emitter of the status string was `_serve_by_acting`, not
`computer_execution_boundary_v1`).

## 4. The repair (additive, 9 of 21, and deliberately not 18 of 21)

In `live_brain_route_admission_v1.py`:

* `_decided_before_the_carrier_gate(attempted)` — True only when the door's status is informative
  (**not** `""` and **not** bare `FAIL_CLOSED`) **and** the attempt reports neither
  `executed: True` nor `side_effects_may_exist: True`.
* when True, the door's own result is the answer; the carrier decision is **not deleted** — it is
  recorded under `carrier_gate` beside the `served_after` this branch already wrote, with
  `refusal_precedes_the_carrier_gate: True`.

**Why 9 and not 18.** My first version kept the earlier reason whenever it was informative. It
recovered 18 of 21 — and it broke a **safety** test:
`test_door_refuses_before_recalled_workflow_and_preserves_prior_effect_uncertainty`, whose prior
attempt carries `executed: True, side_effects_may_exist: True`. The test is right. When work may
already have happened, uncertainty about effects outranks any tidier label. That half is a
property, not the defect, and is pinned by its own test so no later round can "fix" it away.

**Effect, measured both arms (`--out`):**

```
                                     before   after
caller-visible carrier status        21/39     9/39
rows whose real reason is hidden       18        9
pass                                    3        3   (identical set)
must-keep-carrier (effects unknown)      —        9   (unchanged)
```

## 5. What this does NOT claim — read this before quoting §4

* **No capability was gained.** Nothing executes that did not execute before; `pass` is unchanged
  at 3/39 and the pass **set** is identical. This is a *labelling* repair.
* **It does not prove `http.json.fetch_from_state` is safe to serve.** That row recovered to
  `FAIL__RAW_GOAL_COMPILATION_GAP`, which is in `_LEARNABLE_FRONT_STATUSES`; the learn path was
  therefore consulted where it previously was not. The row still refuses, and the guard tests
  (`test_computer_unconfined_route_guard_v1`) are unchanged and green — but no round has yet
  measured what, if anything, the learner now records for it. **That is the next measurement, and
  it is not made here.**
* **It does not resolve the binding-vs-confinement question.** It makes that question *askable*:
  the two surviving carrier rows that are "argument-shaped" (`python.software.repair.apply.verified`
  → `TEST_PATHS_REQUIRED` per #6763) and the nine effect-uncertain rows are now distinguishable
  from the nine request-shaped ones.
* **Zero independent verification.** Producer-run, one machine, my own tool. Per `AGENTS.md`
  rule 4 this is not verification until someone else runs it.

## 6. Regression evidence, both arms, same command

```
python3 -m unittest \
  canonical.tests.test_computer_unconfined_route_guard_v1 \
  canonical.tests.test_one_decision_spelled_once_v1 \
  canonical.tests.test_live_brain_route_admission_v1 \
  canonical.tests.test_live_route_memory_consult_v1 \
  canonical.tests.test_integrated_autonomous_loop_v1 \
  canonical.tests.test_route_memory_policy_v1
```

| arm | tests | failures |
|---|---|---|
| base `c9958189` (fresh clone) | 51 | **5** |
| this change (fresh clone) | 51 | **5** — the *same* five |

The five are pre-existing on the clean base (4 in `test_live_route_memory_consult_v1`, 1 in
`test_integrated_autonomous_loop_v1`) and are **not** caused by, and **not** fixed by, this change.
New test: `canonical/tests/test_the_carrier_gate_does_not_eat_the_reason_v1.py` — 6/6, including a
first test that asserts *the carrier rule really fires on the sentence used*, so the file cannot
pass by measuring nothing. `execution_guard/repo_integrity_guard_v1.py` (this branch's copy):
`violations=0 -> PASS`.

## 7. The falsifiers — how this document can be wrong

1. **The tool reproduces on someone else's machine and clone**: carrier 21 → 9, `recovered_by_rule`
   = 9, `must_keep_the_carrier_answer` = 9. If the numbers differ, §2 is stale, not "approximately
   right".
2. **The recovered rows are not request-shaped**: if a recovered row is in fact a capability that
   *would* run once its arguments are bound, then the carrier label was hiding a capability gap and
   §4 understates it. `#6763`'s S3 stage is the instrument that decides this.
3. **The safety half holds**: any change that makes a row with `executed: True` lose the carrier
   answer is a defect regardless of how many rows it "recovers".
4. **The learnable row is inert**: if `http.json.fetch_from_state` now writes a lesson, the
   recovered label changed behaviour and §5 must be re-measured before merge.

## 8. Where this leaves the owner's question

Unchanged in substance, sharper in evidence. The chain is still *bind → install → confine*, and the
front door is still the bottleneck. What changes is the **counter**: the confinement bucket that
nine rounds treated as the wall is, at the door, **mostly the door's own reasons wearing a carrier
label**. The next honest step is not another seam and not another document — it is to run the
recovered nine through `#6763`'s argument-binding stage and report what each one is actually
missing, because now the answer cannot be mistaken for "confinement".

```bash
python3 canonical/tools/which_refusal_is_actually_firing_v1.py            # the measurement
python3 canonical/tools/realistic_goal_reach_probe_v1.py                  # the published labels
python3 -m unittest canonical.tests.test_the_carrier_gate_does_not_eat_the_reason_v1
```
