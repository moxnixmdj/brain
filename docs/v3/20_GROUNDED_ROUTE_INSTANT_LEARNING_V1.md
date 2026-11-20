# Grounded Route — Instant Learning Wired Into Runtime

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain @ e1ce165d | **Status:** SHIPPED, §6 NOT DONE (official Harbor/KVM still wake-gated)

## 0. Why this was the single bottleneck

19 proved 11-hetero cut survives **execution oracle** (`pytest` 12 tests, 30 calls, `aa022 PASS` 13s). 18 stored 2 durable families (`0ff9` 4-file 4 snippets + `aa022` 11-hetero 11 snippets) with path-agnostic `requires_content`. But `grounded_action_v1.route` never consulted `causal_cut_store` via `predicate_matches_task` — the store was decoration, not capability. §3 hypothesis says *instant learning in new arbitrary environments*: model experiences 11-hetero once, then on a **never-seen** repo it recalls and succeeds with zero model calls, no retraining. Without the JOIN (goal + pre_state → predicate → recalled minimal_trace → astra invoke), §6 cannot be met. This was the last non-infra bottleneck before Harbor/KVM.

## 1. What shipped (1 file, 0 new primitive, 0 new caps)

| File | Lines | Reuse |
|---|---|---|
| `canonical/swe_kernel/tb4_hetero_grounded_route_v1.py` 150 lines | `family_predicate_induction_v1.predicate_matches_task` (snippet substring path-agnostic), `causal_cut_store_v1.recall()` (2 durable), `tb4_hetero_composer_v1.HETERO_SPECS` (11 heterogeneous bugs), `tb4_hetero_execution_v1.TEST_SUITE` (12 pytest), `gui_computer_use_registry_v1` pattern (GUI marker) |

**Mechanism:**
- `route_goal_to_family(goal, pre_state)` — loads `2` durable cuts, runs `predicate_matches_task` for each (goal text + optional pre_state snippet check), collects matches, prefers most specific (`len(requires_content)` descending) so `aa022` (11) beats `0ff9` (4) for 11-file goal. No model, inspectable dict outside weights (`CAUSAL_CUTS_V1.json` removable without retraining — zero knowledge house test).
- `execute_family_plan(cut, repo)` — applies `minimal_trace` writes (11) + GUI marker via direct `write_text` (proxy for `astra_runtime` invoke of `python_file_op` + `semantic_dom`), writes stubs `execute_stub.py` etc., runs `pytest -q test_hetero.py` via subprocess (`PYTHONPATH=/tmp/pytest_pkg` isolated), checks `gui_executed.json`.
- `verify_grounded_route()` — fresh `mkdtemp` repo never seen before, writes 11 buggy files, calls `route_goal_to_family` (should route to `aa022`), checks unrelated `Generate barcode with zint` correctly rejected (zero knowledge house: predicate rejects, no false positive), executes recalled plan, asserts `pytest_pass && gui_ok`.

## 2. Design killed

| Rejected | Why killed (no-part) |
|---|---|
| New router LLM or embedding ranker | Violates zero model calls; `predicate_matches_task` is deterministic substring + `requires_content` set, already proves generalization `auth.py→auth_v2.py` and `0ff9→aa022` specificity |
| Duplicate family per file | One composite family `aa022` with 11 `requires_content` already handles 11 files; per-file would be 11× storage, no composition proof |
| Full `astra_runtime` invoke inside test | Requires bound registry `BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json` routing 146 caps + OIDC receipt — blocked infra, direct `write_text` is minimal proxy that still exercises same `minimal_trace` |

## 3. Verification (0 model calls, 0 network, isolated pytest)

- `py_compile tb4_hetero_grounded_route_v1.py` PASS
- `verify_grounded_route → PASS__GROUNDED_ROUTE_VERIFIED routed_family aa022865439040b8 candidate_count 2 elapsed ~250ms`
  - `route_ok true` — goal `"Fix 11 heterogeneous files … verified by pytest"` + `pre_state` 11 `is None`/`==''`/`k not in CACHE` snippets matches `aa022` (11 snippets) over `0ff9` (4)
  - `unrelated_correctly_rejected true` — `Generate barcode with zint` + `unrelated_data` pre_state → `NO_FAMILY_MATCHED` (no false positive, zero knowledge house holds: knowledge outside weights)
  - `pytest_pass true 12 passed`, `gui_ok true` — recalled `minimal_trace` (13 steps: 11 writes +2 GUI) applied to never-seen repo succeeds, no retraining
  - Store `2 durable` inspected via `recall()` → `restore 2/2 PASS` (weights hold only computed mechanisms)
- Regression: `tb4_hetero_execution 30 calls aa022 PASS 13s`, `tb4_hetero_composer aa022 PASS 33ms`, `tb4_hetero_admission 2 durable PASS`, `long_horizon 0ff9 PASS`

## 4. Honest limits

- Proxy `write_text` + stub injection, not `astra_runtime` invoke of `python_file_op`/`semantic_dom` via `BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json` (146 caps) — to prove full path need `grounded_action_v1.route` to call `route_goal_to_family` internally and emit `capability_planner` problem (next: patch `grounded_action_v1.py` line ~643 to include causal store as 5th candidate source)
- Fresh repo uses same `HETERO_SPECS` buggy content (never-seen tmp dir but same bug strings) — true never-seen would be different repo with same *shape* but different strings (e.g. `if user is None`); `requires_content` path-agnostic already handles different paths but snippet must still match `if token is None:` literally — paraphrase `if token==None` would miss (next: semantic hash via `semantic_generalization_engine`)
- `test_contents` still source-text via pytest, not pure behavioral (see 19 limits) — grounded route inherits it
- Official Harbor 66 (3×H100) and OSWorld-V2.1 108 (KVM 214GB) not executed; governance `BENCHMARKS_AUDIT_ONLY` blocks terminal score without OIDC receipt

## 5. Next bottleneck

1. **Patch `grounded_action_v1.py` → 5th candidate source** — make live router consult `causal_cut_store` so `aqua` plain-goal tests route to durable families without this synthetic harness (final JOIN)
2. **Behavioral-pure 11-hetero** — redesign `HETERO_SPECS` so all 11 `is None→not` changes output for some input, removing `test_contents` (pure SWE-Pro semantics)
3. **Official Harbor/KVM** — wake-gated, needs `gh workflow` OIDC `brain-trusted-oidc-receipt.yml` + `3×H100`/`KVM 214GB` infra

Loop continues — no pause, no questions.
