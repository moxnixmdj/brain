# The repair organ's real ceiling, and what the honesty gate can actually see

**Measured 2026-11-05.** Companion to `FIRST_PRINCIPLES_FIVE_20261105_V1.md`. Method: seven single-defect
worlds, each with one broken module and one failing test pinning the owed behaviour. No work is handed
to the creature — `run_sovereign_board(..., workspace=ws)` senses, selects, repairs, and gates on its own.

## 1. What the organ produces

Given a defect whose fix is a four-wide operator swap or a one-token comparison flip, it succeeds. Given
anything that needs a *shape* of reasoning the operator grammar cannot express, it memorizes.

| defect | what the organ wrote | verdict by the gate |
|---|---|---|
| `add(a,b) -> a - b`, owed `add(2,3)==5` | `return 5` | rejected — OUTPUT_IGNORES_INPUTS |
| `head(xs) -> xs[:-1]`, owed `head([1,2,3])==[1,2,3]` | `return xs` | rejected — TEST_CANNOT_DISTINGUISH_IDENTITY |
| `total(xs) -> product`, owed `total([])==0` | `return 0` | rejected — OUTPUT_IGNORES_INPUTS |
| `last(xs) -> xs[n-2]`, owed `last([1,2,3])==3` | `return 3` | rejected — OUTPUT_IGNORES_INPUTS |
| `at_least(a,b) -> a > b`, owed `at_least(3,3) is True` | `return a >= b` | **accepted** |
| `shout(s) -> s.lower()`, owed `shout('ab')=='AB'` | `return s.upper()` | **accepted** |
| `div(a,b) -> a / b`, owed `div(1,0) is None` | (no generalizable candidate) | refused |

So: **7/7 pinned tests can be made green; 2/7 become genuine acquisitions.** The gap is not the gate
being too strict. The gap is that the organ's answer to "make this example pass" is usually the example.

**This corrects the previous pass's headline.** I reported "two independent defects repaired, fixes
persist". That was true, and narrower than it sounded: `add` and `mul` are both op-swaps. The regime in
which this creature acquires capability is one where the answer lies inside a small operator grammar.

## 2. What the honesty gate can see — three limitations, all measured

Writing them down because the alternative is a gate that reports on itself and calls it evidence.

1. **It cannot confirm intent.** Proving `a + b` correct needs a specification the test does not contain.
   The gate rejects memorization and argument-blindness. It cannot certify that a repair computes the
   right thing, only that it is not a constant and not input-blind.
2. **Identity is invisible to shape-preserving perturbation.** `head(xs) -> xs` satisfies the owed
   assertion in this world and every held-out input of the same shape. No perturbation of the *arguments*
   discriminates it. The gate withholds credit and names the reason
   (`TEST_CANNOT_DISTINGUISH_IDENTITY`) rather than claiming the code was exonerated — the honest verdict
   is "this evidence cannot decide", and it is reported as such.
3. **Boolean results are only weakly probed.** `_perturb` moves numbers, strings and lists; it has no
   coercion that reliably flips a boolean *argument*. So `at_least` is accepted on the strength of not
   being constant. That is a real pass, but a weaker one, and the gate says so
   (`BOOLEAN_RESULT_INPUT_SENSITIVITY_UNPROBED`) instead of laundering it into `RESPONDS_TO_INPUT`.

## 3. A bug this measurement caught in my own work

`_stage_if_changed` was defined as a closure inside `experiment_in_cow_sandbox` and called from
`_repair_multifile_python_confined`, where it does not exist — a `NameError` on a path the previous pass's
two test worlds never entered. Fixed by making it a method (`_note_staged_change`) with explicit staging
dicts. **The zoo found it in the first case; the two ad-hoc worlds could not.** That is the argument for
measuring breadth before claiming generality.

## 4. What this implies for the next step

The binding constraint is no longer the loop, the ranking, the scheduler, or the gate. It is the
**candidate space**: `propose_stun_and_guard_repairs` + `_propose_deterministic_ast_repairs` +
`python_test_guided_patch_search_v1._candidate_specs` enumerate operator/bound/method edits. Every honest
fix that needs a new branch, a new loop bound, an identity element, or a type coercion is outside that
space, so the creature's only reachable answer is the constant — which the gate then correctly refuses.

Widening the candidate grammar is the honest next step. Adding another verifier is not: the verifier is
already refusing more than the organ can usefully produce, and a stricter gate on a narrow search only
converts silent overclaiming into a lower number with the same ceiling.

---

# Addendum, same day: the ceiling was a broken verifier

I wrote the section above concluding that the candidate grammar was the binding constraint. **That was
wrong**, and chasing it found something worse one layer down.

## What happened

I widened the grammar with `_propose_structured_ast_repairs` (integer offsets, identity swap, division
guard) and measured the zoo again: **unchanged, 3/6**. Controlled test — same zoo with the generator
deleted — also 3/6. The generator was dead weight.

So I traced instead of widening further. Every repair, in every case, came from the coupled engine
(`WHITEBOX_TRACE_AND_DUAL_SYNTHESIS`), never from the AST generators. The AST path was gated on
`batch_screen["passing_indices"]`, which was **always empty**.

## The bug

`PersistentConfinedZygote.screen_batch` stages each candidate into a slot directory and symlinks the
rest of the tree from `/input/<batch>`. A test doing the ordinary thing —

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

— had that symlink **resolved back to the input copy**, so it imported the *original* module. The
candidate was invisible to its own test. Verified against ground truth (apply the candidate, run pytest):

| world | candidate | screen says | truth |
|---|---|---|---|
| GREEN | WRONG | `passing=[0]` — passed | FAIL |
| BROKEN | RIGHT | `passing=[]` — failed | PASS |
| BROKEN | no-op | `passing=[]` — failed | FAIL |

Exactly inverted. The screen was grading the **world**, not the candidate.

Consistent with everything above: 7/7 pinned tests could be made green (by the engine, which does its own
verification), but only 2/7 became acquisitions (because the AST path could not report a pass at all in
any world the creature repairs). No amount of candidate-space widening could have moved the number.

## The fix

Stage with **hard links** — `resolve()` cannot escape a hard link — and register each test module under
its own file stem as well as the synthetic `_zyg_cand_N_M` name.

Zoo after the fix, measured by executing tests, nothing handed in:

| defect | owed | held-out |
|---|---|---|
| op swap | pass | **pass** (`return a + b`) |
| off-by-one | fail | fail (refused — organ answers `return xs`, gate withholds) |
| comparison | pass | pass |
| zero guard | pass | pass |
| identity | pass | **pass** (`return 0 if not xs else p`) |
| string method | pass | pass |

**5/6, up from 2/6.** Two of the three previously-unreachable shapes now acquire genuine fixes.

## What this says about the method

Two changes I wrote this turn — the structural generator and an edit-size ranking — were both correct
code written against a bug I had not yet found, and both measured as doing nothing. They were deleted
rather than shipped. The discipline that produced the 5/6 was not cleverer candidate generation; it was
refusing to believe a number until I could point at the mechanism that produced it, and refusing to ship
a change I could not show to be load-bearing.

A verifier that cannot see the thing it verifies does not produce a low score. It produces a *plausible*
one, in an inverted direction, and every layer above it inherits the sign error.
