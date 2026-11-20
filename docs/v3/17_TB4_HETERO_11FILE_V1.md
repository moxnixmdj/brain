# TB4 Hetero 11-File — Heterogeneous Long-Horizon Composition

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain @ e1ce165d | **Status:** SHIPPED, §6 NOT DONE

## 0. Why this was next non-blocked bottleneck

16 proved 11-file *scale* but uniform bug (all `is None→not`, family collapsed to 1 snippet hole). Real TB4 261 lines / SWE-Pro 4.1 files are heterogeneous — different bug per file, which is exactly where frontier drops 20pts (Verified 79% → Pro ~55%). Single bottleneck unlocking most §6: prove causal cut + content-aware family handles 11 *different* edits with same 4-file mechanism, no new primitive. Snapshot compile and Harbor twin remain blocked (OIDC/H100); per §5 switch to next-best.

## 1. What shipped (1 file, 0 new primitive, 0 new caps)

| File | Lines | Reuse |
|---|---|---|
| `canonical/swe_kernel/tb4_hetero_composer_v1.py` 140 lines | `extract_minimal_cut` backward greedy, `attribute_and_induce` with `pre_state/post_state` (11 distinct `requires_content` snippets), `gui_computer_use_registry_v1` 3 caps decisive |

**Task:** 11 files each different buggy pattern — `is None`, `== ''`, `is None: return 8000`, `k not in CACHE`, `msg is None`, `url is None`, `v is None`, `args is None`, etc. — 15-step trace (11 writes + FILL+CLICK +2 noise at 3/8), goal "Fix 11 heterogeneous files and ship via GUI Ship". Oracle: each file's write exactly matches its fixed content (strict, not just `if not` substring).

## 2. Design killed

| Rejected | Why killed |
|---|---|
| Per-file family (11 families) | Violates no-part — single composite family already handles 11 bindings with 11 `requires_content` entries, one predicate `filesystem_accessible+11 snippets` |
| New hetero-specific induction | Same mechanism — 4-file hetero diff already proven via `if token/sql/req/x is None:` 4 snippets; 11 is same, just more distinct holes |
| Harbor H100 run | Infra absent, would idle |

## 3. Verification (0 model calls, 0 network, 0 spend)

- `py_compile tb4_hetero_composer_v1.py` PASS
- `compose_and_verify_hetero 15→13 kept[0,1,2,4,5,6,7,9,10,11,12,13,14] pruned[3,8] 30 oracle calls 33.73ms family aa022865439040b8 PASS`
  - Attribution correct (13 causal = 11 heterogeneous writes +2 GUI, 2 noise pruned)
  - Family `requires_content_count 11` — 11 distinct snippets: `if token is None:`, `if sql is None:`, `if req is None:`, `if x is None:`, `if k not in CACHE:`, `if s == '':`, `if PORT is None:`, `if msg is None:`, `if url is None:`, `if v is None:`, `if args is None:` — each path-agnostic, falsifiable `destroy_negative` GUARDED
  - GUI ground decisive inf → act → verify TARGET_ACTION_FOUND

Scales: 4-file 17 calls 77ms → 11-uniform 30 calls 36ms → 11-hetero 30 calls 33ms (greedy omission O(n), family size O(distinct snippets) not O(files)).

## 4. Honest limits

- Proxy synthetic, not official Harbor 66 H100 — no Harbor receipt; governance `BENCHMARKS_AUDIT_ONLY` blocks terminal claim.
- Family `aa022865439040b8` ephemeral Tier A (not yet twin-admitted `gained1 lost0`); next is heterogeneous twin `_v2/` + sabotage → Tier B durable.
- 11 snippets verbatim (`if PORT is None:`) not normalized — paraphrase `if PORT==None` missed (next: semantic hash via `semantic_generalization_engine`).
- No execution — oracle checks file content equality, not runtime effect (next: execute `pytest` oracle for true SWE-Pro shape).

## 5. Next bottleneck

1. **Heterogeneous twin admission** — synthesize twin 11-file with perturbed paths/labels, `predicate_matches_task` + `gained1 lost0` → Tier B for `aa022...` (proves heterogeneity generalization).
2. **Snapshot compile 7 caps** (blocked OIDC).
3. **Official Harbor/KVM** wake-gated.

Loop continues — no pause, no questions.
