# The transfer receipt is fabricated, and the distinction it hides is the real one

**Measured 2026-11-24.** Subject:
`canonical/verification/AST_IR_ANTI_UNIFICATION_ABLATION_20261124_V1.json` on
`arena/aab1b545-brain`, which the incoming plan cites twice — once as Pillar 0
("`45/45 = 100%`", "`51.11% 1-shot cross-commit transfer`") and once as Idea 6's
justification ("cut evaluations by `1,124,297` and hit `51.11% (23/45)`").

## Four contradictions inside one receipt

Its producer is `canonical/swe_kernel/structural_rewrite_induction_v1.py`, function
`run_three_way_memory_ablation`. Reading it settles the question.

1. **`verified_commits: 45` out of `corpus_commits: 45`.** The function builds
   `verified_rows` only from rows whose stage is `DEMAND_MET` in a *different* receipt
   loaded from `/tmp/hist`. The only committed receipt with that schema
   (`canonical/verification/A_SITE_IS_NOT_A_PRODUCTION_20261124_V1.json`) reports
   **6 `DEMAND_MET` out of 30**. The other 24 are
   `EXCLUDED__THE_FIX_IS_NOT_A_SINGLE_EXPRESSION_REPLACEMENT` (14),
   `SPEC_DEMAND_FOUND_NOTHING` (6), `NO_RELATION_BETWEEN_THE_DEMAND_AND_THE_SITE` (2),
   `THE_SITE_NEVER_RAN_IN_THE_FAILING_TEST` (1), `NO_VALUE_MATCHES` (1).

2. **`excluded_non_single_expression: 0`** is directly contradicted by that same
   receipt, where 14 of 30 rows are excluded for exactly that reason.

3. **The transfer teachers include rows no engine has solved.** The receipt's own
   `transfers` list names `285af2c4`, `351b7319`, `2eb4542c`, `4326ced2`, `553582d9`,
   `644124ec`, `8f8507b4` as teachers. My union driver fails every one of those
   (19/45 and rising, but not those). A row with no verified fix cannot teach a
   morphism, so the teacher set cannot have been what the receipt says it was.

4. **It cannot be reproduced.** `/tmp/hist` does not exist in this workspace, and the
   function's only input path is `--hist /tmp/hist`. A result whose producer cannot be
   pointed at any input is not evidence.

Its `gate5_oracle_verified` is also `bool(tests_green > 0 and _ast_norm(old) !=
_ast_norm(verified))` — a gate that is satisfied by any syntactically different
expression in a file where *at least one* test passes. It never checks that the failing
tests flip.

**Verdict: FAILED.** `45/45` and `51.11%` are not measurements. Neither Pillar 0 nor
Idea 6's evaluation-count claim may be used.

## What the receipt was trying to measure, and why that is still worth doing

Beneath the fake numbers is a real and untested question, and my own previous work does
**not** answer it. Precision matters here:

| store used as | what it can do | status |
|---|---|---|
| **Ranker** — reorder hypotheses the row already produced | nothing if no correct hypothesis exists | **proven ceiling zero** (`THE_STORE_CEILING_IS_ZERO_20261124_V1.md`): `GENERATED_NOT_ATTEMPTED = 0` on all 37 unsolved rows |
| **Originator** — a learned rewrite rule *proposes an edit* at a site the row's own run never proposed | can solve rows whose vocabulary the run never contained | **untested** |

These are different mechanisms and my zero-ceiling result only kills the first. The
fabricated receipt claimed to measure the second and did not. So the second is still
open, and it is the only remaining path by which one experience can multiply rather
than add.

## The honest version of the experiment

Learn morphisms **only from edits an engine actually discovered** (never from the
corpus's stored `old_line`/`new_line`, which would be leakage), apply them to held-out
unsolved rows as originators, and measure outcomes by whether the project's own suite
flips — the same judge every other number in this build uses. Ablate empty store versus
raw trace versus generalized morphism.

That is the next action, and it is runnable here without Docker.
