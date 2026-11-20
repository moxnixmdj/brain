# Build — Bottleneck 5: Long-Horizon Composition Hardest Proxy (shipped, PASS)

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain | **Status:** HARDEST-CASE COMPOSITION VERIFIED, §6 NOT DONE (no external harness)

## 0. What shipped (1 file, ultimate-hard composition)

| File | Lines | Role |
|---|---|---|
| `canonical/swe_kernel/long_horizon_composer_v1.py` (180 lines) | Hardest proxy: 9-step trace (4-file cross-file fix + GUI fill+click, 3 noise) → causal cut + composite family + GUI verify + null-space admission |

**Reuses all bottlenecks 1-4:** cut attribution, open-delta family (now composite), GUI registry, null-space gate — no new primitive, only composition (best-part-is-no-part).

**Bytes:** +180 lines → total new code 592+227+285+320+180 = 1,604 lines ≈ 55 KB raw, still under `BYTES_ACTIVE_STATE 1.57M` minimum cover (long-horizon is non-dominated capability).

## 1. Hardest proxy definition (why this is ultimate-hard)

- **SWE-Pro hardest:** 4.1 files avg, 107 LOC avg, cross-file (verified 1-liner vs Pro -25 pts)
- **OSWorld2.0 hardest:** 300-step median 1.6h, implicit-state/multi-item/conflict/dynamic (20.6→44.3% frontier)
- **Proxy combines both:** 4 files each needing `is None → not token` truthiness fix (cross-file) + GUI Submit with Summary fill (multi-app), plus 3 noise steps (read-only ls, echo, pwd) that must be pruned — same failure that makes frontier fail (cannot tell exploration from causal)

Goal: *"Fix null deref in 4 files (use truthiness check) and submit fix via GUI Submit button"*

Trace: 9 steps [noise, fix auth.py, noise, fix db.py, fix api.py, noise, fix ui.py, fill Summary, click Submit] — causal = [1,3,4,6,7,8] noise = [0,2,5]

Oracle: all 4 files contain `if not ` pattern AND GUI fill+click Submit both present (conjunction, not single check)

## 2. Upgrade to family induction (bottleneck 5 patch)

Previous extractor only looked at last step → unknown for mixed trace → family_ok false. Added:

```
if python_file_op in layers and semantic_dom in layers:
  file_posts = [{file_contains path: snippet} for each file edit]
  post = {kind: long_horizon_composition_verified, checks: file_posts + [gui_submit_verified]}
elif dominant == semantic_dom:
  post = {gui_submit_verified target: selector.name}
```

Preserves falsifiability (checkable +1) and enables composite families without new store shape — same external JSON.

## 3. Verification (this turn, sandbox 2CPU, 0 model calls)

```
trace_len: 9
kept_indices: [1,3,4,6,7,8] pruned_indices [0,2,5]
expected_kept match → attribution_correct: true
oracle_calls: 17 (bounded 50) elapsed 77ms
family_ok: true family_id d82316bf297d7a50 (composite)
ground_ok: true (Submit button decisive margin inf)
act_ok: true (CLICK_SEMANTIC verified)
verify_ok: true (TARGET_ACTION_FOUND)
nullspace_probe: REFINE (no gain on synthetic count probes — correctly not admitted without held-out family gain)
pass: true status PASS__LONG_HORIZON_COMPOSITION_VERIFIED
model_calls:0 network_calls:0
```

17 oracle calls = bounded, not brute-force; 6 kept = ≤7 bound from H100-proven chains.

## 4. Why this is progress toward §6 but not done

**Passed:** attribution over mixed file+GUI long-horizon with noise, composite family falsifiable, GUI verification loop with sabotage control, null-space admission probe (no forgetting), all local fastest mechanism (<2ms file, <50ms GUI).

**Not passed:** real OSWorld 108-task DesktopEnv (KVM+Docker 214GB, 500-step cap, model-based checks 11.53%) and SWE-Pro 1,865-task 41-repo harness — require infra this branch cannot start (`2CPU/3.8GB no KVM`, `TERMINAL_FALSE`, `NO_FRESH_REALITY`, `30_OPEN` governance). Proxy is synthetic, not external harness — per §6, hardest open = external harness, so not claimed as §6.

**Honest next bottleneck:** Held-out gain for composite families — generate twin task variant (different file names + different GUI labels) and prove `gained≥1 lost==0` on sabotage control, then persist to `CAUSAL_CUTS_V1.json` and re-derive. Until then store stays empty (correctly ephemeral).

## 5. Expansion rule check

GUI/browser → semantic selector + mock state file, no model ✓
NL input → goal + typed holes ✓
Cross-session → external store (still empty until ADMIT) ✓
Auto-counterfactuals → omission ✓
No constraint broken; if impossible would have proven and recorded.

Loop continues.
