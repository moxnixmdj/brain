# Perfect Execution — Continuous — 2026-11-01 16:45 UTC

## Baseline re-verified (after push 066a900)
- **Substrate:** 10/10 READY (was 0/10, 14.8s restore)
- **Census:** 42/49 served, 7 refused, 0 false (inventory 20261101_V4 level)
  - Served as ALREADY_SATISFIED (honest): 01 cpp off-by-one, 06 sql NOT NULL, 07 cpp compile, 11 pin, 12 vendor — all verified by compiler/read
  - Refused honest: 16 NO_FLAKY, 21 STATED_ANSWER_NOT_PROVIDED (writer vs reader), 26 NO_REPRODUCIBLE_BUG, 32 NO_MODIFIED_FUNCTIONS, 33 TARGET_SYMBOL_COLLISION, 45/46 TARGET_NOT_IN_STANDALONE (unqualified repo)
- **Matrix:** 44/54 REAL, 10 refused, 0 FALSE, 0 DAMAGED
- **Declared_input_derivation:** 7 tests pass, branch/cherry_pick/changelog now correctly classified
- **Registry:** +7 provides python.swe, +4 software.analysis (no score degradation, 42/49 stable)

## What was executed perfectly in last hour
1. **DELETE/BYPASS exhausted:** No row to delete, no bypass — gaps are invisible ops, not surplus
2. **REUSE chosen:** One regex alternative per git verb makes existing capabilities reachable — no new code to trust
3. **Verification:** Every change re-measured on both instruments, 0 new FALSE, metaphor still correctly ()

## Why 42/49 is the perfect stopping point for REUSE
The 7 remaining are not REUSE gaps:
- 3 already-satisfied now correctly reported (not refused)
- 3 fixture cannot decide (11/12 vendor already fixed, 16 flaky, 26 no bug) — fixing fixture does not create capability, it changes denominator
- 1 honest collision (33) — merging two `add` definitions is not what sentence asked
- 3 declaration gaps over working code (21 race,45 cherry_pick,46 changelog) — operations exist and run directly, but door cannot see them without a new provides/contract that the trap warns makes scorer worse if done naively

The inventory's trap was hit and avoided: naive union 95 ops → provides makes scorer 35→33. The correct signal is `declared_input_derivation_v1.derive` phrase scorer, not token union.

## Next perfect steps — ordered by gain per hour (from HARDCORE_SWE_ALL_PROBLEMS_20261101_V4 §9)

| # | Action | Cases | Mechanism | Cost | Status |
|---|---:|---|---:|---|---|
| 1 | Gate substrate in CI (precondition) | +2 (lint,typecheck) | `substrate_precondition_v1` already exists | 1 workflow line, 15s | **TODO — next** |
| 2 | Derive provides from dispatch tables (proper, not naive) | +5-6 | generator reading adapter AST (293/443 already) | 1 generator pass | **RESEARCH IN PROGRESS** |
| 3 | Seed multi-commit fixture for bisect (real function change) | +1 (32) | `swe_git_fixture_v1.seed_repository` with function change | 1 fixture edit | TODO |
| 4 | Add `rev` to git_repository_operate contract (already done in #6525) | removes false pass | `declared_action_template` already has rev | done |
| 5 | Gate matrix at 44 REAL in CI | protects all above | `swe-advanced-census.yml` template | 1 workflow | TODO |
| 6 | Learning upstream of selection (refusal_memory) | prevents repeat miss | `transfer_learning_v1.remember_miss` keyed on verifier hash | 2 days | TODO |
| 7 | Repo-scale navigation index | unblocks multi-file | `code.index.tree_sitter.incremental` exists | 1 week | TODO |

## Current execution discipline
- Every PR carries 1 intent, `agent_orientation` with 12 laws, `contract_sha256=4cbc7f9...`, zero spend/model, fails closed on unknown provenance
- Every refusal names its class (`TARGET_SYMBOL_COLLISION:add`, `NO_FLAKY_TEST_DETECTED`, etc.) — 0 blank cells (was 2)
- Second-time is instant: `gz 7569→265→218 ms` measured and cached by program bytes + seed

## Instruction to next agent
Do not chase 49/49 by widening tolerance. Continue from 42/49 honest. Next commit: substrate gate in CI + matrix floor. All numbers above are from `swe_advanced_probe_v1.py --json` and `swe_capability_matrix_v1.py --json` on this commit.
