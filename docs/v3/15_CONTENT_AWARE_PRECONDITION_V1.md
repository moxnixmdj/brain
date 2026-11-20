# Content-Aware Precondition — Destructive World Out-of-Family

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain @ e1ce165d | **Status:** SHIPPED, §6 NOT DONE (hardest open still synthetic, not external harness)

## 0. Why this was the next non-blocked bottleneck

14 left destructive check informational (`would_destroy=src/auth.py live_match true` but `lost` still 0) — exhaustive falsifiability was documented, not enforced. Per "best part is no part" the missing part was not a new cap but a *precondition snippet* that makes unrelated world out-of-family without exact path dependence. Real OSWorld hardest failures are implicit-state where file exists but not the right content — our predicate `any_state` would fire and destroy. This is the single bottleneck that unlocks `lost==0` honesty for composite families.

Blocked: TB4 66 Harbor H100×3 + OSWorld-V2.1 108 KVM 214GB 11.53% model-judge + SWE-Pro 1,865 731 public ~30% broken — infra absent → audit only.

## 1. What shipped (2 edits, 0 new files, 0 new caps)

| File | Edit | Mechanism |
|---|---|---|
| `family_predicate_induction_v1.py:108-138` | `requires_content` path-agnostic: for each written file that existed with different content, capture buggy line `if token is None:` etc as `snippet_key→snippet` (not exact path), precondition `requires: filesystem_accessible + requires_content:{snippet: snippet}` | Reuse existing `pre_state` snapshot diff (12) — now content, not path |
| `family_predicate_induction_v1.py:485-505` | `predicate_matches_task` content-aware: when `task_pre_state` provided, each `snippet` must appear in *some* file's content (path-agnostic) → `PRECONDITION_CONTENT_MISMATCH` else `FAMILY_MATCH`; when `None` advisory-pass (twin goal-only) | Path-agnostic check allows `auth.py→auth_v2.py` generalization while rejecting `unrelated_data` |
| `long_horizon_composer_v1.py:92` + `composite_family_admission_v1.py:118,156-168` | Composer/admission now pass `pre_state/post_state` so `edit_of` + `requires_content` proven; admission step6 verifies `predicate_rejects_unrelated=True` + `predicate_accepts_buggy=True` | Same snapshots already created for `edit_of` — no new data |

**Family:** `d82316bf297d7a50` → `0ff936c7c2683729` (hash now includes `requires_content` 4 snippets: `if token is None:`, `if sql is None:`, `if req is None:`, `if x is None:`), 6-step cut unchanged, `filesystem_accessible` + content, `long_horizon_composition_verified` + `edit_preserves_outside` via `pre→post` diff.

## 2. Design killed

| Rejected | Why killed |
|---|---|
| Exact `requires_files: [src/auth.py,...]` | Kills generalization (`auth.py`≠`auth_v2.py`) — violates player-by-player null-deref should transfer across file names |
| New destroy service/capability | Destroy is falsifier + precondition, not runtime service — adding cap adds part |
| Train VLM for content check | Violates zero-model-calls; `snippet in content` is deterministic $0 |

## 3. Verification (0 model calls, 0 network)

- `py_compile` 3 files PASS
- `compose_and_verify 9→6 kept[1,3,4,6,7,8] 0ff936c7c2683729 PASS` (`precondition requires_content` 4 snippets)
- `predicate_matches_task(twin, None) → FAMILY_MATCH` (advisory-pass, twin distinct `auth_v2.py` generalizes)
- `predicate_matches_task(twin, destr_pre={auth:unrelated,db:unrelated...}) → PRECONDITION_CONTENT_MISMATCH_missing_buggy_snippet_if token is None:` (destructive world correctly out-of-family, no destruction)
- `predicate_matches_task(twin, buggy_pre=orig_pre) → FAMILY_MATCH` (buggy world in-family)
- `admit_composite_family twin *_v2.py+Confirm/Notes → PASS gained1 lost0 stored1 destroy_check {would_destroy:src/auth.py, guard_documented:true, live_match:true, predicate_rejects_unrelated:true, predicate_accepts_buggy:true}` — `CAUSAL_CUTS_V1.json` now 2 cuts (`d823` superseded + `0ff9` current) `restore[0ff9,d823] failed[]`, `GUI 4/4` PASS

## 4. Honest limits

- Store has 2 cuts (old `d823` without content + new `0ff9` with content) — old could be pruned (next: `remove(d823)` to keep minimal). Kept for audit trail.
- `requires_content` is snippet-exact (`if token is None:`) not normalized — paraphrase `if token==None` would be missed (next: semantic normalization via `semantic_generalization_engine` hash, but not needed for hardest proxy where snippet is exact).
- §6 still synthetic twin not external harness — TB4/SWE-Pro/OSWorld-V2.1 need Harbor/KVM not in sandbox, governance `NO_FRESH_REALITY` blocks terminal claim.

## 5. Next bottleneck

1. **Snapshot compile** (blocked OIDC) — promote 7 caps (4 FS/program+3 GUI) into `BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json` so planner proposes GUI without runtime union.
2. **Hardest open harness twin** — needs H100/KVM, wake-gated.
3. **Prune old family** — `remove(d82316bf297d7a50)` to keep store minimal (1 durable `0ff9`).

Loop continues — no pause, no questions.
