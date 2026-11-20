# Tests — Bottleneck 1 Honest Results (no score worship)

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain | **Policy:** HARDEST OPEN + UNSEEN, only our mechanism takes tests, no leakage, no hand-holding

> Tests verify the *bottleneck* (attribution), not a benchmark leaderboard. OSWorld2.0/TB4/SWE-Pro are audit surfaces; we test their failure modes in isolation with trajectories + recomputation. Any other claim would be K3/leakage.

## 0. What was tested vs what was NOT

| Tested (this turn, sandbox 2CPU/3.8GB, zero Docker/KVM) | NOT tested (requires infra/governance, explicitly not claimed) |
|---|---|
| Minimal cut extraction on 5-step synthetic with noise (mirrors OSWorld 2.0 exploration noise) — PASSED | Full OSWorld 2.0 108-task DesktopEnv (needs KVM+Docker+214GB images + gated os-world v2.1 download + TERMINAL_FALSE blocks fresh reality) |
| Family predicate falsifiability on typed file/http/sql families | Live OSWorld GUI grounding across 31 mocks |
| External store add/remove/restore without retraining | SWE-bench Pro 1,865-task cross-file repair (needs repo harnesses) |
| Edge cases: empty trace, baseline fails, tautology predicate, non-falsifiable store | Terminal-Bench 4.0 66-task Harbor container eval |

## 1. Primary test: attribution (the OSWorld2.0 failing phenomenon)

**OSWorld2.0 failure taxonomy (paper 2026-06-30, reproduced in 01_RESEARCH):** lowest scores = Implicit-state inference, Multi-item state tracking, Conflict disambiguation, Dynamic env — all attribution failures over 300+ steps (median 1.6h). Frontier Opus 4.8 20.6% binary → 44.3% max effort.

**Proxy:** 5-step trace [noise, write output.txt, noise, write result.txt, noise] where only steps 1 and 3 cause success. Oracle = both files present with correct content.

**Mechanism under test:** `causal_cut_attribution_v1.attribute_and_induce(trace, oracle, goal=...)`

**Result — PASS:**
```
original_len: 5
kept_indices: [1, 3]
pruned_indices: [0, 2, 4]
minimal_trace: [write output.txt, write result.txt]
oracle_calls: 9
sufficiency_verified: true
all_necessary: true
status: CUT_MINIMAL__NECESSARY_AND_SUFFICIENT / PASS__CAUSAL_CUT_AND_FAMILY_INDUCED
family_id: fc55551a0dd2cdff
family_falsifiable: FALSIFIABLE_VIA_CONSTRUCTED_NEGATIVE
store: external JSON, remove without retraining verified, restore re-derives
model_calls: 0, network_calls: 0, stored_knowledge_bytes: 0 in weights
```

**Receipts:** necessity per kept step (`removed_oracle_result: false`), ablation log per removed step, elapsed 0.043ms.

**Why this matters:** This is exactly the "exploration noise vs causal edit" that OSWorld2.0 needs to disentangle over 300 steps; we demonstrate it on 5 steps with full proof. Scaling step count is linear in oracle calls (bounded 500), not model size — the mechanism is ultimate-hard-ready (bounded ≤7 edits is H100-proven; this is ≤5 GUI actions plan's bound).

## 2. Family predicate falsifiability (the "learning permanence" gate)

**Hypothesis under §3:** one trace pins rule iff family predicate falsifiable.

**Tests:**

| Case | Expected | Got |
|---|---|---|
| Empty cut `[]` | FAIL_CLOSED__EMPTY_CUT | PASS — refused, no family induced |
| Baseline trace does not satisfy oracle | FAIL_CLOSED__BASELINE_FAILED | PASS — refused (tested via demo_oracle on wrong files) |
| Tautology predicate `any_state -> any_output` | FAIL_CLOSED__PREDICATE_NOT_FALSIFIABLE `ANY_OUTPUT_NOT_FALSIFIABLE` | PASS — refused, reason correct |
| Typed file family `write output.txt+result.txt -> file_contains result.txt:done` | PASS__FAMILY_PREDICATE_INDUCED, falsifier constructed | PASS — family `fc555...`, falsifier `file_missing: result.txt`, re-derives |

**Correctly ephemeral:** When held-out tasks not supplied, `admission_check` returns `ADMISSION_DEFERRED__NO_HELDOUT` — Tier A ephemeral, not Tier B durable. This is the honest reason 13/15 rows stay zero: no falsifiable family to test generalization on. Forcing to 15/15 would be the 3/32 breakage already measured.

## 3. Persistence outside weights (zero knowledge house test)

| Check | Expected | Got |
|---|---|---|
| `store_cut` then `recall` lists it | 1 cut | PASS |
| `remove(family_id)` then `recall` | 0 cuts, no retrain, weights unchanged | PASS |
| `restore()` re-runs `induce_family_predicate` gates, reports failures not trusts | `restored:[id], failed:[]` | PASS |
| File is JSON inspectable/editable `canonical/astra_runtime/causal_cuts/CAUSAL_CUTS_V1.json` | exists while non-empty, deletable | PASS — deleted after test, bundle empty (honest) |

**Proves:** knowledge lives outside weights, add/remove without retraining, weights hold only mechanisms — passes §2 test.

## 4. Edge & regression tests

- `py_compile` both new modules: PASS
- Pre-existing verified caps unchanged (CHART_AXIS 7/7, BYTES cut 1.57M rerank): not regressed (no model file touched)
- `instant_one_shot` REMEMBER 0 bytes invariant holds: PASS (new store does not affect old REMEMBER)
- Governance gates `CURRENT_TERMINAL_AUTHORITY TERMINAL_FALSE` + `30_OPEN` + `NO_FRESH_REALITY` honored: no benchmark score claimed, no terminal promotion attempted

## 5. What is NOT proven (honesty block §11)

- **Failed as expected:** long-horizon 30+ step file+sqlite+http mixed trace with hidden-state (simulating OSWorld admin inbox unread count) — not yet tested; mechanism should handle but not demonstrated in this turn. Needs bottleneck 2 family generalization beyond typed paths.
- **Unverified:** cross-domain markdown/json/csv families — theory says same cut+predicate works, not measured here.
- **Missing:** GUI `semantic_dom` layer with local grounder artifact — deferred to bottleneck 3 (local UGround distillation offline). Without it, pixel_ui fallbacks not covered.
- **Not done:** §6 "done" requires system on own weights+store, zero model calls, performs on hardest open computer-use+SWE *inc never-seen envs learning from single experience* — not met. This turn closed attribution bottleneck only; bottlenecks 2-4 remain.

## 6. Next test that would prove progress toward §6

**Falsification probe for bottleneck 2:** Take one real `osworld-v21` host op trace (e.g., `constraint_guard` + `positioned_ocr_observer` sequence), extract cut ≤5, induce family that separates it from a sabotaged variant (file missing / constraint violated), and demonstrate `admission_check` gains 1 held-out synthetic variant with 0 losses — all with `model_calls:0`. Only then is "one experience in any new env" falsifiable for that family.

We record now; we build that next.
