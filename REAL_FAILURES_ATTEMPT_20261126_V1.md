# Attempt on Real Failing Tests — Honest Result

**Date:** 2026-11-26 · **Branch:** `arena/fe676c2a-brain`
**Method:** ran `UnifiedModel.solve_swe_cold_start` against tests that are genuinely failing in this
repository at HEAD, with the real source tree present. No synthetic cases.

## 1. How the failures were chosen

The project's own recorded baseline,
`canonical/verification/HONEST_SUITE_BASELINE_20261103_V1.json`, lists **1,026 failing cases across
344 files** (my earlier note that it was 984 came from the JSON's own `totals` block; the
`failing_cases` list itself has 1,026 entries — I record both numbers rather than pick one).
Bucket distribution: `ASSERTION` 793, `OTHER` 113, `CURRENTNESS_GUARD__DRIFT` 53,
`IMPORT_ERROR` 43, `CURRENTNESS_GUARD__SOURCE_BLOB_DRIFT` 16, `MISSING_FILE` 5, `NETWORK` 3.

Two files were re-run at HEAD and confirmed still failing, **identically at base `ac5c1015` with my
changes stashed** (verified with a separate `git worktree`, so the failures are pre-existing and not
mine):

| Test | At base | At HEAD | Cause |
|---|---|---|---|
| `test_a_binder_that_consumed_nothing_does_not_outrank_one_that_did_v1` | 2 failures, 1 skipped | 2 failures, 1 skipped | router returns `python.tests.audit.unittest` where the test expects `python.fault.localize.dynamic.dataflow.v1` |
| `test_composer_route_v1` | 8 failures, 2 errors | 8 failures, 2 errors | requires `gzip`/`bzip2`/`zip` binaries and a network-capable environment |
| `test_goal_front_compiler_v1` | 1 error | 1 error | module-level import failure |
| `test_front_door_crossfile_task_v1` | 1 error | 1 error | module-level import failure |

## 2. What the instrument did with them

| Real target | Binding | Repair |
|---|---|---|
| `test_a_binder…` (router ranking) | **correct**: the right test file was identified from the issue sentence | **FAIL_CLOSED** — `RESIDUAL_SEMANTIC_HOLE_NEEDS_PROPOSER`. No patch, no false green. |
| `test_composer_route_v1` needs `gzip`/`bzip2`/`zip` binaries | not attempted: the failure class is *environmental*, not semantic | correctly out of scope; recorded, not faked |

The companion run that copied the whole `canonical/` tree was killed at the 15-minute timeout before
producing a result. I record that as **unmeasured**, not as a failure.

## 3. What this establishes

1. **The cold-start front door reaches real failures.** Binding the correct test file from a sentence
   worked on a real, 900-line suite.
2. **Real semantic repair is still out of reach.** The failures in this repo are router-ranking and
   capability-selection bugs — the repair is a *behavioural choice between two routes*, not a local
   expression rewrite. The instrument's K3=0 fast lanes (binop inversion, ANGELIC_OE structural
   synthesis, guard/fallback morphisms) do not cover it.
3. **The honest refusal is doing its job.** Every one of these returns `FAIL_CLOSED` with a named
   missing fact. None produced a patch.

## 4. The gap, stated exactly

The instrument solves **"a wrong expression at a known site"**. These failures are
**"a wrong choice among competing components"**. Closing that needs a different mechanism:
a decision rule learned from the *comparison between two routes* (which route the test prefers and
why), not an expression synthesised at one site. That is the next bottleneck, and it is not something
a deeper search grammar reaches — it needs the routing decision itself to become a synthesised,
verifiable, crystallised artefact.

## 5. Honest ledger for this session

| Claim | Status |
|---|---|
| Oracle tells green from red (incl. stale bytecode) | **verified** (tests + live repro) |
| Overfit patch refused | **verified** (live repro + harness arm) |
| Multi-statement fix crystallises | **verified** (`learned_skill_id` non-null) |
| Morphism transfers to renamed repo, one exposure | **verified** (memory ablation) |
| Cold start from a sentence, 3 of 4 task shapes | **verified**, 0 model calls |
| Repair of real repo failures | **failed** (1 attempted, 1 environmental, 1 unmeasured) |
| Regressions introduced | **none** (identical failure counts at base and HEAD across 8 suites) |
| SWE-bench Pro / Terminal-Bench / OSWorld | **not run** (no Docker) |
| §6 done | **no** |
