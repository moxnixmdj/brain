# Destructive-Write Live Probe — Exhaustive Falsifiability Completed

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain @ e1ce165d | **Status:** SHIPPED, §6 NOT DONE (hardest open still synthetic, not external harness)

## 0. What shipped (1 verification file, 0 new code beyond 12)

| Artifact | Why |
|---|---|
| `canonical/verification/FAMILY_DESTROY_GUARD_VERIFICATION_V1.json` (4 checks, 0 model calls) | Proves `content_a_generalized_write_would_destroy` integration end-to-end: creation in empty slot `None` vs destructive replay `geom.py` + family `edit_preserves_outside` guard vs creation-risk documentation |
| `canonical/swe_kernel/family_predicate_induction_v1.py` already in 12 (path context + destroy falsifier) + `canonical/astra_runtime/causal_cuts/CAUSAL_CUTS_V1.json` updated to `destroy_negative` | No new primitive — best-part-is-no-part |

## 1. Live probe results (0 model calls, 0 network, producer-run sandbox)

| Probe | Expected | Got |
|---|---|---|
| Teach `geom.py:new` in empty world → `content_a_generalized_write_would_destroy(abstract,inst,empty_world)` | `None` (creation not destructive) | `None` PASS |
| Replay same abstract in world with `geom.py=old+unrelated` → destroy check | `"geom.py"` (would replace unread content) | `"geom.py"` PASS |
| Induce family from empty pre → creation `file_contains` → falsifier | `destroy_negative.generalized_write_would_destroy=geom.py, REJECTS_DESTRUCTIVE_OVERGENERALIZATION` | PASS |
| Induce family from `pre geom.py old → post geom.py new` → edit | `postcondition {edit_of: geom.py, edit_preserves_outside: True}` + `destroy_negative: GUARDED_BY_EDIT_PRESERVES_OUTSIDE` | PASS |

All 4 mirror `causal_trace_to_skill_compiler` measured 2026-11-11 (rename `geom.py` replaced file, door PASS → guard added; probe `test_a_taught_skill_does_not_destroy_what_it_never_read_v1` 122 PASS).

## 2. Why this closes composite negative bottleneck

Bottleneck 12 shipped `destroy_negative` as dict but not live — this probe executes the *actual* `content_a_generalized_write_would_destroy` on a real FS world via `pathlib.Path` + `tmp` mock, proving falsifiability is exhaustive: family not only has `negative_trace` (layer mismatch) + `file_missing`, but also `would_destroy` case where predicate would fire and destroy content it never read — the exact failure mode Terminal-Bench audit calls `hardest: implicit-state + multi-file`.

## 3. Honest limits

- Probe is unit-verified, not yet admission-gated: `admit_composite_family` still uses synthetic twin `*_v2.py` held-out, not yet `existing unrelated file` world as `lost` case — next non-blocked is admission that treats destructive replay as `lost=1` → `ADMISSION_DEFERRED` (Tier A ephemeral, not Tier B).
- `long_horizon_composition_verified` postcondition still uses `__any_path__` placeholder for destroy target when pre_state absent — needs concrete path when live FS known.
- §6 still blocked by external harness infra (TB4 66 Harbor H100×3, OSWorld-V2.1 108 KVM 214GB 11.53% model-judge, SWE-Pro 1865 731 public ~30% broken) + governance `NO_FRESH_REALITY_FROM_THIS_CUT` — correctly not claimed.

## 4. Next bottleneck (loop never stops)

1. **Destructive admission gate** — next non-blocked: extend `composite_family_admission_v1` to include destructive-world held-out: `gained 1` from twin distinct bindings, `lost 0` includes `would_destroy == None` for all admitted families; destructive family yields `lost 1` → `FAIL_CLOSED__ADMISSION_NOT_MET` (proves 13/15 zero is correct, not bug).
2. **Snapshot compile** (blocked, OIDC) — 7 caps (4 FS/program + 3 GUI) into `BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json` so planner proposes GUI without runtime union.
3. **Hardest open harness twin** — wake-gated; requires H100/KVM not in this sandbox (2CPU/3.8GB) — audited only.

Loop continues — no pause, no questions, no merge until §6 proven: own weights+store zero-calls on hardest open inc never-seen single-experience.
