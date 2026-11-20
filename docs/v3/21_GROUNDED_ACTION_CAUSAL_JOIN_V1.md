# Grounded Action Causal Join — Live Router Wired to Store

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain @ e1ce165d | **Status:** SHIPPED, §6 NOT DONE (official Harbor/KVM wake-gated)

## 0. Why this was the single bottleneck

20 proved `route_goal_to_family` + `execute_family_plan` work in isolation (`aa022` 11-hetero → fresh repo `pytest 12 passed` + `unrelated rejected`). But `grounded_action_v1.act` — the live plain-goal router that ` §6` actually tests — never consulted `CAUSAL_CUTS_V1.json`. The store was decoration: `act("Fix 11 heterogeneous files …")` fell through to `NO_CANDIDATE_SURVIVED` instead of `CAUSAL_FAMILY_RECALL`. §3 hypothesis *instant learning in new arbitrary environment* requires the live system, not a harness, to recall with zero model calls. This patch is the final non-infra JOIN.

## 1. What shipped (1 file patched, 0 new files, 0 new caps, 0 new deps)

| File | Change | Lines |
|---|---|---|
| `canonical/runtime/grounded_action_v1.py` | Pre-grounding causal-family fast path: `recall()` → `predicate_matches_task()` with filesystem `pre_state` (src/**/*.py) for content-aware `requires_content` guard → most-specific (`len(requires_content)` desc) → execute `minimal_trace` with stub injection (`execute_stub`/`request_stub`/`run_stub`) + GUI via `gui_computer_use_registry` → `VERIFIED_ACTION causal_family.<id>` | +70 |

**Mechanism (mirrors 20's proven logic, no duplication):**
- Early in `act()`, before `load_registry`/`ground`, try causal path; on exception `pass` to preserve existing routing (fail-closed, not fail-open).
- `_cf_pre` built from `root.rglob("src/*.py")` + paths in cuts (for `requires_content` destructive guard — same as `predicate_matches_task` needs).
- `_cf_matches` = all stored families where `predicate_matches_task(goal, _cf_pre)` fires; `NO_FAMILY_MATCHED` if none (zero knowledge house: unrelated `Generate barcode with zint` + `unrelated_data` correctly rejected).
- Winner = most `requires_content` snippets (11 `aa022` beats 4 `0ff9` for 11-file goal — player-by-player specificity).
- Execution: `python_file_op` → `write_text` with stub injection (`execute(sql)`→`from execute_stub import execute`) same as `tb4_hetero_execution._write_repo_from_trace`; `semantic_dom` → `CAP_GUI_GROUND_V1` + `CAP_GUI_ACT_V1` (decisive 1.25). Returns `VERIFIED_ACTION` with `model_calls 0`, `provides long_horizon_composition_verified`.

## 2. Design killed

| Rejected | Why killed (no-part) |
|---|---|
| New synthetic capability entry per family in `BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json` | Would duplicate registry (146 caps) + require OIDC receipt; causal families are composite 13-step plans, not single `invoke_capability` — direct trace replay is minimal and honest |
| Embedding ranker / LLM re-rank | Violates zero model calls; `predicate_matches_task` deterministic substring + `requires_content` already proves `auth.py→auth_v2.py` and specificity |
| Separate `causal_grounding.py` module | Would split JOIN into two routers; single fast-path in `act()` is one JOIN, one file, same as forged/capability_forge injection pattern already at lines 627/643 |

## 3. Verification (0 model calls, 0 network, isolated pytest)

- `py_compile grounded_action_v1.py` PASS (syntax fix `provides` line)
- `act("Fix 11 heterogeneous files … verified by pytest", fresh repo with 11 buggy src/*.py) → VERIFIED_ACTION causal_family.aa022865439040b8 candidate_count 2 ok true` — auth fixed `if not token:` present, `db` injected `from execute_stub import execute`, `pytest 12 passed` after act (stubs ensure `execute/request/run` resolve)
- `act("Generate barcode image with zint", same repo) → ok false ACTION_FAILED auto.apt.zint` — not hijacked to causal family (predicate correctly rejected, `PRECONDITION_NOT_TRUE_OF_WORLD` for unrelated)
- `act("Write hello world to output.txt", fresh repo) → VERIFIED_ACTION CAP_FS_WRITE_V1 ok true` — normal registry routing preserved (no regression)
- Store `2 durable 0ff9(4)+aa022(11) restore 2/2 PASS`, `tb4_hetero_grounded_route PASS`, `tb4_hetero_execution 30 calls aa022 PASS`

## 4. Honest limits

- Stub injection (`execute_stub.py` etc.) is proxy for real repo deps (`pip install -e .`) — SWE-Pro repos have real `requirements.txt`; next: ephemeral `pip install` in act's trace replay (costly)
- `test_contents` still source-text via pytest (19 limit) — behavioral-pure 11-hetero would need redesigned `HETERO_SPECS` where every `is None→not` changes output for some input (e.g. `CACHE={'k':None}`)
- Official Harbor 66 (3×H100) + OSWorld 108 (KVM 214GB) not executed — `BENCHMARKS_AUDIT_ONLY` blocks terminal claim without OIDC `brain-trusted-oidc-receipt.yml`
- `requires_content` verbatim `if token is None:` not normalized (`==None` paraphrase missed) — next: semantic hash

## 5. Next bottleneck

1. **Behavioral-pure 11-hetero** — rewrite `HETERO_SPECS` so all 11 changes are behaviorally observable without `test_contents` (pure SWE-Pro execution semantics)
2. **Official Harbor OIDC dispatch** — `gh workflow run` with `3×H100` + `KVM 214GB` infra to score 66 TB4 + 108 OSWorld against live `act` (now wired)
3. **Snapshot compile** — `BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json` already 146 caps (145 V1 +1) — verify OIDC receipt for new join, else document blocked command

Loop continues — no pause, no questions.
