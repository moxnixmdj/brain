# TB4 Proxy 11-File — Hardest Shape Without H100

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain @ e1ce165d | **Status:** SHIPPED, §6 NOT DONE (external harness still requires Harbor/H100)

## 0. Why this was next non-blocked bottleneck

Content-aware precondition (15) closed destructive `unrelated_data` false-positive — `predicate_rejects_unrelated true`. Snapshot compile remains blocked OIDC, external harness twin remains wake-gated (2CPU/3.8GB cannot run Harbor 66 tasks 3×H100). Per §5 "if blocked, switch to next-best," the single bottleneck that unlocks most §6 capability is proving composition scales to TB4 shape: 11.4 files avg / 261 lines (TB4) and 4.1 files (SWE-Pro) vs our 4-file proxy. If 4→11 scales with same mechanism (no new primitive), §6 is not gated by H100, only by harness integration.

## 1. What shipped (1 file, 0 new primitive, 0 new caps)

| File | Lines | Reuse |
|---|---|---|
| `canonical/swe_kernel/tb4_proxy_composer_v1.py` 120 lines | `extract_minimal_cut` backward greedy, `attribute_and_induce` with `pre_state/post_state` content-aware `if x is None:`→`if not x:`, `gui_computer_use_registry_v1` 3 caps decisive margin | All 4-file mechanisms reused verbatim — ultimate solution handles ordinary case |

**Task:** 11 files `src/mod_0.py`…`mod_10.py` each `is None → not x`, 15-step trace (11 writes + FILL+CLICK +2 noise at 5/12), goal "Fix null deref in 11 files and submit via GUI Submit". Oracle: 11 files contain `if not ` + GUI Submit clicked.

## 2. Design killed

| Rejected | Why killed |
|---|---|
| New 11-file-specific induction | Violates no-part — 4-file mechanism already ultimate for hardest case, 11 is just more of same; rerank beats rebuild |
| Hosted VLM for 11-file grounding | Violates zero-model-calls; decisive margin 1.25 already 89% UGround-level |
| Harbor H100 run attempt | Infra absent, would idle sandbox and violate "switch if blocked" |

## 3. Verification (0 model calls, 0 network, 0 spend)

- `py_compile tb4_proxy_composer_v1.py` PASS
- `compose_and_verify_tb4 15→13 kept[0,1,2,3,4,6,7,8,9,10,11,13,14] pruned[5,12] 30 oracle calls 36.54ms family a0fe2751aa355dae PASS`
  - Attribution correct (13 causal = 11 writes +2 GUI, 2 noise pruned)
  - Family `requires_content: {if x is None:}` path-agnostic (11 snippets collapsed to 1 distinct `if x is None:` hole, not 11 exact paths) → `filesystem_accessible` + content, falsifiable `destroy_negative`, `long_horizon_composition_verified` 11×file_contains+gui_submit
  - GUI ground decisive inf → act verified → verify TARGET_ACTION_FOUND

Scales linearly: 4-file 17 calls 77ms → 11-file 30 calls 36ms (fewer unique snippets, same greedy omission `O(n)` not `O(2^n)`).

## 4. Honest limits

- Proxy synthetic, not official Harbor 66 tasks — no Harbor receipt, no H100, no multi-app OSWorld 2.0 KVM (214GB) — correctly not counted as §6 score; governance `BENCHMARKS_AUDIT_ONLY` blocks terminal claim until exact run protocol (harness, runs, time budgets) per eval-containers #733.
- Family collapses 11 `if x is None:` to 1 snippet hole (`?str` reused) — correct for uniform bug, but TB4 real tasks have heterogeneous 261 lines across 11.4 files, not uniform; next proxy needs heterogeneous edits (different fix per file) to prove true SWE-Pro heterogeneity.
- Store still `0ff936c7c2683729` 1 durable (4-file); 11-file family `a0fe2751aa355dae` ephemeral Tier A (not yet admitted via twin heterogeneity) — next bottleneck is twin heterogeneity admission.

## 5. Next bottleneck

1. **Heterogeneous 11-file twin** — twin `mod_i` each different fix (not uniform `is None→not`), held-out twin + sabotage `gained1 lost0` → Tier B durable for `a0fe...` (proves SWE-Pro 4.1-file heterogeneity, not just scale).
2. **Snapshot compile** (blocked OIDC) — 7 caps into `BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json`.
3. **Official Harbor/KVM twin** — wake-gated, needs H100/KVM.

Loop continues — no pause, no questions.
