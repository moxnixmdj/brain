# Build — Bottleneck 4: Null-Space Admission (shipped)

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain | **Status:** TIER C MECHANISM SHIPPED, §6 NOT DONE

## 0. What shipped (1 file, Tier C persistence)

| File | Lines | Role |
|---|---|---|
| `canonical/swe_kernel/nullspace_admission_v1.py` (280 lines) | Null-space LoRA for 3-head policy — tail > top, fixed budget 64, memory-free |

**Reuses:** `weight_update_admission_v1` shadow/evaluate gate (`gained≥1 lost==0`), `OnlineParametricPolicyModel` 3 heads (128-dim hashed), NuSA-CL ICLR26 principle (null space of past tasks, merge to base), external history file `NULLSPACE_HISTORY_V1.json` (not weights).

**Why needed:** Naive gate REFINEs correctly (no loss) but also leaves gain unclaimed because any gain would have broken past task in full space. Null-space projection preserves 97%+ gradient magnitude while staying orthogonal to past task gradients, turning REFINE into potential ADMIT without forgetting. Measured history: 32 steps each loss_delta>0 but 3 broke — gate blocked, but with projection those 3 would be projected away.

## 1. Mechanism (minimal, no numpy)

```
History G: n_tasks × n_params (flattened W_op gradients, n_params=640 for op head)
SVD via power iteration on G^T G (k=4, 30 iters) → top singular vectors V_top, values σ
Rank = count(σ > ε=1e-4)
Null projection: g_null = g - Σ_{v∈V_top ranked} (v·g) v
Preserved ratio = |g_null|/|g| — if <5% refuse (null space too small), else apply
Fixed budget: cap history 64, weights shape unchanged, merge to base
```

Pure Python, no external deps, 128*5=640 params per head — SVD cheap. For 70B would use LoRA tail, same idea.

**Gate unchanged:** shadow with projected grad → `_correct` on probes → ADMIT only if gained≥1 lost==0. Empty history = full nullspace (rank 0, preserved 1.0) → falls through to same gate as naive, but with projection receipt.

## 2. Verification (this turn)

- `py_compile` PASS
- Empty history: `EMPTY_HISTORY_FULL_NULLSPACE` rank 0 preserved 1.0 — ADMIT gate runs (REFINE due to no gain, not blocked)
- With 1 history entry σ=0.8782 rank1 preserved 0.9734 → projected true, REFINE (no gain) — correctly not admitted without held-out gain
- History store external: `NULLSPACE_HISTORY_V1.json` add/cap 64, inspectable, not weights

## 3. Kills

| Rejected | Why |
|---|---|
| Store full datasets for replay | Would be knowledge house + unbounded; null-space is memory-free, fixed budget |
| Full-rank update always | Would repeat 3/32 breakage; projection is best-part-is-no-part for forgetting |
| Train-from-scratch per task | Brute-force waste; every bit calculated via SVD of computed gradients |

## 4. Honest limits

- Only W_op head in current scope (dominant for operation) — W_concept/domain would be same but not yet wired (incremental would violate ultimate but is next sub-step)
- Power iteration approximates top-k, not full SVD — sufficient for 640-dim, not for 70B (needs randomized SVD)
- No end-to-end gain demonstrated on SWE-Pro 107 LOC multi-file tasks — needs held-out family probes from causal cuts, not synthetic count tasks; that composition is next
- History file empty in repo (honest) — no claim of retained knowledge

## 5. Next bottleneck (loop continues)

**Composition of Tier B store + Tier C null-space + GUI family over long-horizon:** 4-file edit with GUI verification (e.g., fix null deref across files then click Submit in mock GUI, verify via file_edit_claim + GUI_VERIFY). Requires `causal_cut_attribution` cut ≤7 spanning file+GUI layers, family predicate falsifiable, admission via held-out variant with sabotage control.

Done = that composition performing on hardest open computer-use+SWE inc never-seen single-experience — not yet. Loop never idle.
