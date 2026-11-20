# Admission — Composite Family Permanent (first Tier B durability)

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain | **Status:** FIRST COMPOSITE FAMILY ADMITTED, §6 NOT DONE (synthetic twin, not external harness)

## 0. What was admitted (1 file, 1 durable family)

| File | Outcome |
|---|---|
| `canonical/swe_kernel/composite_family_admission_v1.py` (180 lines) | Twin synthesis + held-out + sabotage → `gained=1 lost=0` → persisted to `canonical/astra_runtime/causal_cuts/CAUSAL_CUTS_V1.json` |

**Family:** `d82316bf297d7a50` — 9-step 4-file truthiness fix + GUI Submit composite (6-step minimal cut 4×`python_file_op` + 2×`semantic_dom`), 28 holes (`?path|?str|?num`), postcondition `long_horizon_composition_verified` (4× file_contains + gui_submit), falsifiable via constructed negative.

**Reuses:** long-horizon composer + twin world synthesis (simplified `synthesize_perturbed_twin_world`), cut store, GUI registry, null-space gate pattern.

## 1. Twin synthesis (genuinely distinct)

- Original: `src/auth.py/db.py/api.py/ui.py` + `Submit` + `Summary` textbox
- Twin: `src/auth_v2.py/db_v2.py/api_v2.py/ui_v2.py` + `Confirm` + `Notes` textbox — same bug pattern `is None → not token`, same structure, different bindings — proves distinctness (different file names + different GUI labels), not replay of same instance (previous guard `HELDOUT_IDENTICAL_TO_TRAINING_INSTANCE` would have refused same bindings).

## 2. Admission proof (held-out + sabotage)

| Check | Expected | Got |
|---|---|---|
| Original induction PASS | family falsifiable | PASS composite family `d823...` |
| Predicate matches twin (recall) | `should_fire true` | PASS |
| Twin cut attribution correct | 6 causal kept [1,3,4,6,7,8] vs noise | PASS |
| Twin GUI ground/act | decisive margin verify | PASS |
| Sabotage (drop db fix) correctly fails oracle | `not sabotage_oracle` | PASS |
| Gained≥1 lost==0 | `gained 1 lost 0` | PASS → **ADMITTED** |
| Persist to external JSON | `stored_count 1` | PASS |
| Restore re-derives | `restored [d823...] failed []` | PASS |

90.82ms, 0 model calls, 0 network, external store add/remove without retraining verified.

**This is the first demonstration of §3 hypothesis *charitable* being true for hardest proxy:** do once (9-step mixed) → cut to 6 → induce composite family → twin held-out gain + sabotage control → permanently stored, re-derivable, GUI verified.

## 3. Honest limits (why not §6)

- Twin is synthetic file-name perturbed, not external OSWorld2.0 twin with real held-out VM + model-based checks (11.53% weight) + user simulator — synthetic twin cannot be counted as §6 hardest open.
- Store count 1 synthetic, not 1,865 SWE-Pro or 108 OSWorld tasks — scope is mechanism proof, not benchmark score.
- No weight-space null-space merge needed for this family (Tier B store sufficient) — Tier C probe still REFINE on count tasks.
- Governance `ACTIVE_FAIL_CLOSED__BENCHMARKS_AUDIT_ONLY` still blocks claiming external score; this doc is audit/probe, not parent objective.

**Next bottleneck:** Same admission but with real `osworld-v21` runner twin (requires KVM+Docker+214GB) or `SWE-Pro` 41-repo twin (requires Harbor) — needs infra this sandbox lacks (2CPU/3.8GB). Loop will switch bottleneck if blocked, never idle: next non-blocked is tightening `?path` over-capture + merging GUI registry into `grounded_action` union.

Done = that twin but with external harness, not synthetic — not yet claimed.
