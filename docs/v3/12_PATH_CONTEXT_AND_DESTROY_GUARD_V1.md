# Path Context-Awareness + Destroy Guard — Composite Negative Completed

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain @ e1ce165d | **Status:** SHIPPED, §6 NOT DONE (hardest open still synthetic, not external harness)

## 0. Why this was the next non-blocked bottleneck (autonomous loop §5)

Blocked: real `osworld-v21` KVM/214GB twin + `TB4` Harbor H100×3 + `SWE-Pro` 41-repo twin — infra absent (2CPU/3.8GB) → switch per law "if blocked, switch to next-best bottleneck, never idle."
Non-blocked with max capability per byte:

| Bottleneck | Why load-bearing | Why now |
|---|---|---|
| **Path overcapture** | `_PATH_LIKE_RE` on `json.dumps(blob)` counted content string `"geom.py"` as path hole — 3 literals for 2 file ops (`geom.py` in content + `src/auth.py` + `geom.py` path → inflated family, reduced transfer, violated "every bit calculated") | Measurable duplication, 0 new files, best-part-is-no-part (remove before adding) |
| **Composite destroy negative** | File-creation family that generalizes to "replace whole file with taught content" passes 9→6 cut and GUI verify but would destroy unread user data — `causal_trace_to_skill_compiler` proves this via `content_a_generalized_write_would_destroy` (measured 2026-11-11 rename `geom.py` replaced file, door PASS) | Exhaustive falsifiability hole: family had `negative_trace` + `file_missing` but no `destroy_negative` — composite families need it |

Snapshot compile (BOUND snapshot) remains blocked by compiler + OIDC — not attempted this turn.

## 1. What shipped (2 minimal edits, 0 new files)

**File:** `canonical/swe_kernel/family_predicate_induction_v1.py` (466 → 500 lines, +34)

| Edit | Lines | Mechanism | Reuse |
|---|---|---|---|
| Path context-aware | `_extract_action_schema:124-139` | Path holes ONLY from explicit path-typed fields (`path,db_path,source_path,target_path,state_path,dom_path,sqlite_path,output_path`) with `_PATH_LIKE_RE.search` gate; `"/" in v` fallback — removes blob overcapture | Reuses same `_PATH_LIKE_RE` strict gate from 11, not new regex |
| Destroy guard | `_extract_postcondition:241-251` + `_make_falsifier:340-365` | `dominant==python_file_op` now checks `pre_state[path]` vs `post_state[path]` → emits `edit_of+edit_preserves_outside:True` when edit proven; falsifier adds `destroy_negative` exhaustive case (GUARDED vs REJECTS_DESTRUCTIVE_OVERGENERALIZATION) mirroring `causal_trace_to_skill_compiler.content_a_generalized_write_would_destroy` | Direct verbatim copy of destroy semantics, no new primitive — composition of existing proven guard |

Bytes: +34 lines changed, 0 new caps, 0 weights — bytes frontier `1,577,081 NEXT87 frozen` preserved.

## 2. Design killed by "smartest approach?"

| Rejected | Why killed |
|---|---|
| New regex for path | Reuse strict regex already shipped in 11 — adding second regex violates no-part |
| Separate destroy capability/service | Destroy is a *falsifier*, not a runtime capability — adding service adds part; falsifier dict is inspectable outside weights and satisfies Tier A/B/C contradiction test (external store add/remove without retrain) |
| Train new model to distinguish create vs edit | Violates zero-model-calls + zero-knowledge-house; pre/post snapshot diff already provides content-addressed proof |

## 3. Verification (this turn, 0 model calls, 0 network)

| Check | Result |
|---|---|
| `py_compile family_predicate_induction_v1.py` | PASS |
| Path regex strict intact (`pathlib.Path` false, `src/auth.py` true) | PASS |
| Old blob path literals `["geom.py","src/auth.py","geom.py"]` → new `["src/auth.py","geom.py"]` (content geom.py not counted as path) | PASS |
| Edit `geom.py old→new` with `pre/post` → `postcondition {edit_of: geom.py, edit_preserves_outside: True}` → `destroy_negative: GUARDED_BY_EDIT_PRESERVES_OUTSIDE` | PASS |
| Creation `new.py` without edit guard → `destroy_negative: PREDICATE_REJECTS_DESTRUCTIVE_OVERGENERALIZATION` | PASS |
| `compose_and_verify()` 9→6 kept[1,3,4,6,7,8] pruned[0,2,5] 17 calls 77ms `d82316bf297d7a50` | PASS |
| `admit_composite_family()` twin `*_v2.py+Confirm/Notes` → `gained 1 lost 0 stored 1` | PASS `d823...` overwrites with new falsifier, `restore[d823] failed[]` |
| `CAUSAL_CUTS_V1.json` durable 1 cut, destructible without retrain `remove+restore` | PASS |
| GUI `CAP_GUI_GROUND/ACT/VERIFY` margin inf decisive verified | PASS `canonical/verification/GUI_COMPUTER_USE_VERIFICATION_V1.json` 4/4 |
| Store `canonical/astra_runtime/causal_cuts/CAUSAL_CUTS_V1.json` falsifier keys `destroy_negative` present | PASS |

## 4. Honest limits (why §6 not done)

- Destroy guard is falsifier-documented, not yet executed end-to-end as a *live* replay in a world with `existing unrelated file` that would be destroyed — next non-blocked is destructive-write live probe (create world with `geom.py=unrelated`, replay generalized write, verify `content_a_generalized_write_would_destroy` returns `geom.py` and predicate rejects).
- Long-horizon family still `long_horizon_composition_verified` with `__any_path__` placeholder for destroy target (needs concrete path when pre_state known) — not yet wired to live FS check.
- §6 still requires external harness twin (OSWorld-V2.1 108 KVM, TB4 66 H100×3, SWE-Pro 1865) — synth twin not counted; governance `NO_FRESH_REALITY_FROM_THIS_CUT` + `BENCHMARKS_AUDIT_ONLY` correctly blocks terminal claim.

## 5. Next bottleneck (loop never stops)

1. **Destructive-write live probe** — next non-blocked: construct pre_state with `geom.py=unrelated`, teach `geom.py=new`, induce family without edit guard, replay in destructive world, prove `content_a_generalized_write_would_destroy == "geom.py"` and admission refused (`ADMISSION_DEFERRED` stays ephemeral Tier A, not Tier B durable).
2. **Snapshot compile** (blocked, OIDC) — if unblocked, promote 7 caps (4 FS/program + 3 GUI) into `BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json` so planner sees them without runtime union.
3. **Hardest open harness twin** — requires infra absent; remains wake-gated, not attempted per `TERMINAL_FALSE 30_OPEN`.

Loop continues — no pause, no questions, no merge until §6 proven (own weights+store zero-calls on hardest open inc never-seen single-experience).
