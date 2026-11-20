# Destructive Admission Gate — Exhaustive Falsifiability End-to-End

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain @ e1ce165d | **Status:** SHIPPED, §6 NOT DONE (hardest open still synthetic, not external harness)

## 0. Why this was the next non-blocked bottleneck

Bottleneck 12-13 shipped path context-awareness + `destroy_negative` dict + live probe `content_a_generalized_write_would_destroy` unit, but admission still `gained1 lost0` without exercising it — correctly ephemeral Tier A would have become destructive Tier B if family replaced unread user file. Per §5 law "never idle while unfinished work remains," next best is to wire the live destroy check into admission as informational gate, proving exhaustive falsifiability before it blocks.

Blocked: TB4 66 Harbor H100×3 + OSWorld-V2.1 108 KVM 214GB 11.53% model-judge + SWE-Pro 1,865 731 public ~30% broken — infra absent (2CPU/3.8GB) → audit/probe only per `BENCHMARKS_AUDIT_ONLY`.

## 1. What shipped (3 minimal edits, 0 new primitive)

| File | Edit | Why |
|---|---|---|
| `family_predicate_induction_v1.py:104-112` | Keep precondition `any_state` for generalized families (reverted over-specific `requires_files` that broke twin `auth.py→auth_v2.py` generalization) | Best-part-is-no-part: precondition must be hole-aware, not exact path |
| `long_horizon_composer_v1.py:92-100` | Pass `pre_state/post_state` snapshots to `attribute_and_induce` so `edit_of+edit_preserves_outside` proven via `pre[buggy]→post[fixed]` diff | Reuse existing `postcondition` fallback logic (12) — now live for composite |
| `composite_family_admission_v1.py:118-168` | Step 6 destructive world: `tmp/src/auth.py=unrelated` → `content_a_generalized_write_would_destroy(abstract[?str0], inst, cwd)` → `would_destroy=src/auth.py`, `guard_documented=True`, `live_match=True` | Verbatim reuse of `causal_trace_to_skill_compiler` guard, no new mechanism — informational not yet blocking (`lost` stays 0, `gained1` still ADMITTED) |

**Result:** `composer 9→6 d82316bf297d7a50 PASS`, `admit_composite_family gained1 lost0 ADMITTED destroy_check {would_destroy: src/auth.py, guard_documented: true, live_match: true}` — store `CAUSAL_CUTS_V1.json` 1 durable, `restore[d823]` PASS, `FAMILY_DESTROY_GUARD_VERIFICATION_V1.json` 4/4 still PASS.

## 2. Design killed by "smartest approach?"

| Rejected | Why killed |
|---|---|
| Exact `requires_files` precondition for edit | Kills generalization (`auth.py` ≠ `auth_v2.py`) — violates player-by-player null-deref fix should transfer across file names |
| New destroy capability/service | Destroy is falsifier, not runtime cap — adding service adds part; `destroy_negative` + live probe already inspectable outside weights, add/remove without retrain |
| Train VLM for GUI destroy detection | Violates zero-model-calls + zero-knowledge-house; `content_a_generalized_write_would_destroy` is deterministic file check, $0 |

## 3. Verification (0 model calls, 0 network)

- `py_compile` 3 files PASS
- `composer 9→6 kept[1,3,4,6,7,8] 17 calls 77ms d823...` PASS (now with `edit_of` via pre/post)
- `admit_composite_family twin *_v2.py+Confirm/Notes PASS gained1 lost0 stored1 destroy would_destroy src/auth.py guard_documented true live_match true` (informational)
- `CAUSAL_CUTS_V1.json 1 cut d823...` durable, `restore` PASS, `GUI 4/4` PASS

## 4. Honest limits (why §6 not done)

- Destructive check is **informational** — not yet `lost=1` blocking admission. Next non-blocked is to make precondition content-aware (`file_contains buggy "is None"`), so destructive world `unrelated_data` correctly out-of-family → `PREDICATE_REJECTS_NEGATIVE` without needing destroy flag, and true destructive generalization becomes `lost=1` → `ADMISSION_DEFERRED` Tier A (proves 13/15 zero is correct falsification, not bug).
- Long-horizon family still `long_horizon_composition_verified` with `__any_path__` placeholder when pre_state absent — needs concrete path when live FS known.
- §6 still requires external harness twin (TB4/SWE-Pro/OSWorld-V2.1) — synthetic twin not counted; governance `NO_FRESH_REALITY` blocks terminal claim.

## 5. Next bottleneck (loop never stops)

1. **Content-aware precondition** — `pre_state` buggy snippet `if ... is None` → `requires_content` hole, so `predicate_matches_task` rejects `unrelated_data` world as out-of-family (no destroy needed) — destructive admission becomes blocking `lost=1` correctly.
2. **Snapshot compile** (blocked OIDC) — 7 caps into `BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json`.
3. **Hardest open harness twin** — wake-gated, needs H100/KVM.

Loop continues — no pause, no questions, no merge until §6 proven.
