# v3 Brain Mission — Continuation Inventory & Feasibility Report v1
**Date:** 2026-11-20 (UTC) — branch `arena/69b87879-brain` @ `e1ce165d9e18a79f8e604adc788c61ba2c68732f` (clean)
**Mode:** Research & Inventory Only — No builds, tests, benchmark executions, merges, or governance bypass.
**Author:** Agent Mode (Arena) — reconnaissance continuation

> This document preserves the findings from the interrupted turn and the follow-up reads of canonical pointers, authorities, compiled artifacts, runtime routes, persistence boundaries, and benchmark surfaces. It does not execute consequential work.

---

## 0. Executive Summary

- **Governance remains blocking:** Canonical pointer requires `CRITICAL_PATH_PRE_ACTION_GATE_V11` + `GOAL_HIERARCHY_ACTION_GATE_V11`; development authority (`CURRENT_DEVELOPMENT_AUTHORITY_V1` dated 2026-10-11) mandates *General-Capability-First, Benchmarks-Audit-Only, Minimum-Proof-Cover-Required, Reuse-First* with `GOAL_HIERARCHY_ACTION_GATE_V12`. Live selection is **unauthorized**, terminal authority is `TERMINAL_FALSE`, zero-reality authority grants **no execution / promotion / fresh-reality**. Consequential work must not proceed until reconciliation.
- **Compiled model is internally consistent** but **counts diverge from README projection** by design: artifact = 447 capabilities (153 bound, 294 receipt-backed), 26 engines, 18 skills, 581 knowledge docs, 7,184 research records, 2,373 routing tokens, 1,996 source-index modules. README 364/168/1,775 figures are a different projection, not a hash mismatch — compiler SHA and included-source digest both verify (`5f900ac89...`, 1,383 sources, 0 missing/changed).
- **Live registry is the source of truth for executability:** `BOUND_CAPABILITY_REGISTRY_V1.json` = 145 verified-bound; snapshot = 146. Compiler rows embed verification notes but the adapter re-reads live registry on every call — embedding does not grant credit.
- **Learning vs persistence is sharply partitioned:**
  - `instant_one_shot_learning_v1.py` → **REMEMBER persists nothing** (zero-knowledge-house, re-derived from principles). Tests pin this.
  - `semantic_generalization_engine_v1.py` (typed SemanticTaskAST → synthesized program → causal probes) **is reachable** via `closed_loop_autonomous_controller_v1.py:1194` on a `learn`-enabled path when no recalled workflow applies. It stores 24 experiences (8 unique descriptions, all `success`) + 8 embeddings; **no `GENERALIZATION_POLICY_V1.json`** on disk — permanent weight step gated by `weight_update_admission_v1` (ADMIT requires held-out gain, zero loss).
  - `VerifiedSkillStore` (`verified_skill_crystallizer_v1.py`) and `causal_trace_to_skill_compiler_v1` use durable SQLite + bundles (5 verified skills, 11 compiled workflows) with re-verification on recall and admission gates — **real persistence, but scoped to Python/CPP/Rust/Go/TS repair**, not broad transfer.
  - `acquired_operator_memory_v1.py` persists taught operator demonstrations and **re-derives** them via `restore()` at door import — distinct from weight updates.
- **Computer-use family exists but is narrow:** `h100_computer_use_registry_v1.py` = 4 capabilities (`CAP_FS_LIST_V1`, `CAP_FS_READ_V1`, `CAP_FS_WRITE_V1`, `CAP_PROGRAM_RUN_V1`) — filesystem + confined execution. OSWorld V2.1 stack is extensive (adapters V1-V8, subjects V1-V19, workflow policies V1-V13, runner bridge) but **no broad unseen-app proof**; check-density report = novel-work detection 0.5 (only crashes/no-ops). OSWorld is **outside Brain executability** (source-index ORPHANs, 89 modules, 0 capabilities).
- **Evidence remains bounded:** Single-trace report 30 commits, 150-154k candidate space, 13/15 rows zero demand-matching + 1 row with 2 alternatives (47 tests) → does not pin rule (§6 unestablished). Real-commit repair 0/90, structural rewrite 0/5 (producer-run).
- **Benchmarks are feasible only as external audits, not local executions** in current 2-CPU/3.8 GB/no-Docker/no-pytest sandbox: OSWorld V2 (108 tasks, 1.6h median, 318 tool calls, 20.6% best), OSWorld 2.1 pins (Docker+KVM, 214 GB images), SWE-bench Pro V2 (642 HARD-51 locked offline + fresh-sandbox re-grade), Terminal-Bench 4.1 (66 tasks/63 CPU-only), OSWorld-Science (164 tasks, 8 GB/4 vCPU/KVM). No Brain-run yet; policy requires minimum-certificate-cover before any benchmark-specific action.
- **Recommendation:** Stay in audit mode. Next research steps are targeted provenance audits (registry/loader/projection, skill admission, generalization admission rates) and benchmark protocol collation — **no implementation selection**.

---

## 1. Governance & Authority (verbatim checks)

**Canonical Pointer** (`canonical/CANONICAL_POINTER.json` — `PROJECT_BRAIN_CANONICAL_POINTER_V1`, generation `2026-10-09-resource-bounded-bytes-v1`):
- Required gates: `canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V11.json` + `GOAL_HIERARCHY_ACTION_GATE_V11.json`
- Mission lock: `FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V10` + `CAPABILITY_ACQUISITION_ENGINE_LAW_V8`
- Resource law: `RESOURCE_BOUNDED_CAPABILITY_BYTES_LAW_V1` → `verified_mechanism_cover_optimizer.py` + `OBSERVED_MECHANISM_LIBRARY`
- Maps to `canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json`, `GOAL_HIERARCHY_ACTION_GATE`, etc. Full boot requirements enumerated (causal gate, mission lock, anti-drift, truth-first, recursive-obs, etc.).

**Development Authority** (`canonical/governance/CURRENT_DEVELOPMENT_AUTHORITY.json` — `PROJECT_BRAIN_CURRENT_DEVELOPMENT_AUTHORITY_V1`, 2026-10-11):
- Status: `ACTIVE_FAIL_CLOSED__GENERAL_CAPABILITY_FIRST__BENCHMARKS_AUDIT_ONLY__MINIMUM_PROOF_COVER_REQUIRED__REUSE_FIRST`
- Terminal objective: *Build the most capable general reliable resource-efficient problem-solving system*
- Scheduler numerator: Expected general capability gain / reuse breadth / reliability / causal confidence; denominator: wall-clock, compute, memory, incremental cost, complexity, evidence risk; hard constraints: correctness-first, fail-closed-truth, provenance, ownership, no-goal-substitution.
- Benchmark policy: role = audit/falsifier/calibration-surface/causal-probe; forbidden as parent objective/score-chasing/benchmark-specific patch without transfer.
- Route order: DELETE → BYPASS → REUSE → ADAPT → SUBSTITUTE → COMPOSE → CONFIGURE → INTEGRATE → SYNTHESIZE_NEW_PRIMITIVE (new primitive defaults to **unauthorized**).
- Loop: UNDERSTAND → PLAN → COMPOSE → ACT → VERIFY → LEARN → GENERALIZE → COMPRESS → REUSE.
- Credit: only verified reusable capability / reliability/resource gain without regression / verified live integration / independent falsification. Benchmark score movement alone = **zero credit**.

**Missing pointers in this checkout (not present on branch at this commit):**
- `ACTIVE_GOAL_HIERARCHY_V1.json`, `CURRENT_LIVE_WORK_FRONTIER.json`, `CURRENT_TERMINAL_AUTHORITY.json`, `CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json` → all `MISSING` via `git` check. Their expected contents (from prior session memory) were `live_selection.authorized = false`, `TERMINAL_FALSE`, `30 open obligations J0_G0_T0_D15_U15`, no execution/promotion/fresh-reality. **Do not infer them** — treat as requiring re-establishment from canonical before any action.

**Implication:** Consequential work (new capability selection, model promotion, benchmark-driven patching, terminal wave execution) is **currently unauthorized**. Research, reading, and non-mutating audits are the only permitted operations.

---

## 2. Model & Compilation Integrity

**Artifact:** `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` (11.2 MB)

| Dimension | Artifact `counts` | Live Registry | README Projection (if present) | Notes |
|---|---|---|---|---|
| Capabilities | 447 | 145 (V1) / 146 (snapshot) | 364 | Artifact includes receipt-backed (294) + bound (153). Registry is the executability floor. |
| Bound | 153 | — | — | All `incremental_spend_usd = 0` |
| Receipt-backed | 294 | — | — | Pending promotion, re-checked at call time |
| Engines | 26 | — | — | Fabric + solvers |
| Skills | 18 | — | — | Knowledge-store skills |
| Knowledge docs | 581 | — | — | — |
| Source-index modules | 1,996 (452 entry-points) | — | 1,775 routing tokens vs 2,373 artifact | Projection difference, not corruption |
| Research records | 7,184 | — | — | — |

**Integrity checks (re-run this session):**
- `included_source_count` declared = 1,383; recomputed = 1,383 ✓
- `source_tree_digest` declared = `5f900ac897e26c099222e85ae1bdd3ed87fb9245a3f9d66a4f0934df8fab3fcb`; recomputed = same ✓
- All 1,383 included files: `missing 0, changed 0` ✓
- Compiler SHA matches artifact provenance ✓
- Source rows: 1,996 hash-exact; 0 changed/missing; 3,324 new files in sampled scopes are expected (unindexed helpers/ORPHANs).

**Compiler logic (`compile_brain_unified_model_v1.py`):**
- `_source_index_rows` deliberately indexes non-capability modules as `capability: false` with classification `ENTRY_POINT | INTERNAL_HELPER | ORPHAN` — 1,452 ORPHANs (imported by nobody) are **addressable, not executable**.
- `covered_paths` derived from capability IDs (`*.auto.v1` strip) + `provenance.source_path` — fixes prior contradiction where 133 capability modules were double-indexed as addressable.
- `research_index` kept distinct from capabilities/knowledge.

**Runtime model (`brain_unified_model_v1.py`):**
- Public entrypoints: `load_model(root, verify)`, `BrainUnifiedModel.status()`, `route(goal, top_k)`, `solve(goal, inputs, capability_id, context_paths)`, `act_or_learn(goal, ...)`, `_dispatch_engine`, `_execute_capability`.
- `route()` implements ASK-token scoring with address-token handling, deduplication, unrunnable filtering via `_missing_declared_dependencies`.
- `solve()` / `_execute_capability` enforce `CAPABILITY_INPUTS_MISSING`, `NONZERO_SPEND_REJECTED`, `BOUND_PYPI_SOURCE_INCOMPLETE`, and distinguish `PASS__PROMOTED_BOUND_CAPABILITY_EXECUTED_AND_TRACE_VERIFIED` vs `PASS__RECEIPT_BACKED_BOUND_CAPABILITY_EXECUTED` (no relabeling).
- `act_or_learn()` (K3=0): System-1 reflex (<0.5 ms) → System-2 deliberation via `closed_loop_autonomous_controller_v1.solve_or_learn`, with Active-Inference `predict_before_act` / `settle_and_compute_surprise`, skill-macro, adaptive solver, forged capability, and upstream routing ledger paths.

**Live registry merge (`live_integrated_brain_v1.py`):**
- `REGISTRY = canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json` + `CAPABILITY_RECEIPT_PROJECTION_V1.json`; snapshot is FLOOR.
- `load_verified_registry(include_extended=True)` caches on mtimes; extended entries admitted **only** by `_receipt_admits` (receipt + independent verification with `github_run_id` + OIDC claims `iss=https://token.actions.githubusercontent.com` + repo binding). Status field alone is ignored — prevents `SESSION_E0A256F8` mass-flip.
- Receipt schema: `PROJECT_BRAIN_CAPABILITY_EXECUTION_RECEIPT_V1`; verification requires distinct runner, matching `module_sha256`/`result_sha256`, non-zero-spend check, zero model dependencies.

---

## 3. Fabric & Route Admission

**Unified Cognitive Fabric** (`unified_cognitive_fabric_v1.py`):
- 25 engine descriptors + 1 meta-orchestrator (`ONE_SHOT_REALITY_CLOSURE`).
- Engines: `RAW_GOAL`, `COMPILED_TASK`, `ADEQUATE_DECISION`, `P3`, `ADAPTIVE_SOLVER`, `LEARNING_EPISODE`, `IMPROVEMENT_CYCLE`, `BOUND_CAPABILITY`, `H100_INFERENCE`, `MYSTERY_INFERENCE`, `CAPABILITY_SCHEDULER`, `REPAIR_SYNTHESIS`, `REPAIR_CYCLE`, `UNIVERSAL_ESCAPE`, `REACHED_ESCAPE_STATE`, `CERTIFIED_ROUTE`, `TERMINAL_AUTOPILOT`, `TERMINAL_ROOT`, `TERMINAL_CLOSURE`, `OWNERSHIP_CATALOG`, `LIVE_CAPABILITY`, `LIVE_COMPOSITION`, `SEMANTIC_AMBIGUITY`, `SEMANTIC_RELATION`, `OEWN_DECISION_SENSE`.
- Mode resolution: `run(request)` → `_auto_mode` (payload/options) → `LEARNING_EPISODE` if episode/skill verifiers present; `CATALOG` and `ONE_SHOT_REALITY_CLOSURE` are explicit modes.
- Forbidden providers in live fabric: `proposal_provider`, `capability_expander` (except `REACHED_ESCAPE_STATE` with `semantic_authority_verifier`), `success_episode_adapter_provider`, `one_shot_failure_repair/synthesis` — enforced as `OPAQUE_COGNITION_PROVIDER_FORBIDDEN_IN_LIVE_FABRIC`.
- Direct-experience learning path: for `R3_DIRECT_EXPERIENCE_MODES` (P3, H100, MYSTERY, UNIVERSAL_ESCAPE, CERTIFIED_ROUTE, LIVE_CAPABILITY, BOUND_CAPABILITY) with `learn≠false` and no repair gap, calls `live_runtime.observe_runtime_outcome` with bounded observation + compounding tick via `r3_improvement_queue_driver_v1.drain`.
- Auto one-shot closure: `ADEQUATE_DECISION` failures (when not requiring user info) trigger `one_shot_reality_closure_v2.run` and possible replay.

**Route admission (`live_brain_route_admission_v1.py`):**
- `_solve_public(request)` is the single front door: validates `task_id`/`goal`, runs `_solve_request` (usual path), then taught-words fallback (only if `pass≠true` && `executed≠true` && no side-effects), contract checks, effect-directed compile (`effect_directed_compile_v1.attempt`), `_serve_by_acting` (computer execution boundary), and finally `recall_and_execute_workflow` for verified taught workflows.
- `solve_or_learn(request, learn, ...)` delegates to `closed_loop_autonomous_controller_v1.solve_or_learn` but annotates `boundary.STATUS` (computer-env refusals) with `post_refusal_policy_summary`.
- Every non-IMPROVEMENT_CYCLE path with `learn` drains a compounding tick unless already in a repair gap.

---

## 4. Persistence & Learning Boundaries (exact)

### 4.1 Instant One-Shot Learning (non-persisting)
**File:** `canonical/swe_kernel/instant_one_shot_learning_v1.py` (SCHEMA `PROJECT_BRAIN_INSTANT_ONE_SHOT_LEARNING_V1`)

Pipeline: OBSERVE → CREDIT → IDENTIFY → CONTRACT → APPLICABILITY → COMPOSE → HORIZON → ADMIT → **REMEMBER → REPLAY**

- Phases 1-7 build a calculated contract from first principles (SEPARATION + STABILITY), zero model/network calls, fail-closed.
- Phase 8 `admit_before_persistence(horizon_result, contract_result, victims)` → held-out victim execution via `lesson_admission_gate_v1.evaluate` (must repair ≥1 unseen defective + preserve ≥1 correct, break nothing). Verdicts: `_GATE_ADMIT`/refuse.
- Phase 9 `remember_skill(admit_result)` → **always returns `stored_knowledge_bytes: 0`, `knowledge_house: false`, `derivation: instant_one_shot_learning_calculated_not_stored`.** Even on ADMIT, it persists **nothing**. `REMEMBER_DONE = REMEMBER_DONE__PERSISTED_TO_STORE` is a status label, not a write — implementation writes no file/DB.
- Phase 10 `REPLAY` reproduces skill on new state, verified from different initial state.

**Invariant:** `REMEMBER` is the hard boundary. Repository tests assert no durable write occurs.

### 4.2 Semantic Generalization Engine (bounded, separately reachable)
**File:** `canonical/swe_kernel/semantic_generalization_engine_v1.py`

- **Pillar 1 — Parametric policy:** `OnlineParametricPolicyModel` — three linear heads (`W_op`, `W_concept`, `W_domain`) over hashed text features (128-dim), one gradient step per verified experience. State file `canonical/astra_runtime/generalization/GENERALIZATION_POLICY_V1.json` (schema `BRAIN_ONLINE_PARAMETRIC_POLICY_V1`). Current checkout: **no file** → all updates in-memory only.
- **Pillar 2 — Typed parsing:** `parse_task(goal)` → `SemanticTaskAST{operation, concept, domain, targets, qualifiers, confidence}` via regex lexicons (ops: count/breakdown/exists/compare/list; concepts: function/method/class/if/for/while/import/…; domains: python_ast/markdown/json/csv/text). Multi-file aware, confidence + notes carry uncertainty; `unknown` → refusal downstream.
- **Pillar 3 — Synthesis & causal verification:** Typed AST → explicit synthesized Python program → execution + interventional verification → answer. Handles int counts, name lists, dict breakdowns; volatile policy update kept in-memory, never silently mutates tracked experience.
- **Pillar 4 — Experience store:** `GENERALIZATION_EXPERIENCES_V1.json` (24 rows, 8 unique descriptions, all `success=24`) + `TASK_EMBEDDINGS_V1.json` (15181 bytes) — tracked but **not a proof of broad transfer**. `GENERALIZATION_POLICY_V1.json` absence means no persistent weight survives process exit.
- **Current reachability:** `closed_loop_autonomous_controller_v1.py:1194` → `GeneralizationEngine().solve_task(goal, work_cwd, top_k=3, persist_policy=False, store_experience=False)` inside TIER 0A-SEMANTIC (<25 ms) when `learn=true`, no recalled workflow, not `computer_shape`, and no typed-AST lane hit. **No permanent weight admission occurs here** (`persist_policy=False`).
- **Permanent admission (separate path):** `weight_update_admission_v1.py` → `evaluate_update(model, goal, op/concept/domain, probes)` on a **copy** (`_shadow`), measuring agreement with `parse_task` labels on held-out probes (ARCHIVE/TRANSFER split). Verdicts: `ADMIT` (gained≥1, lost=0), `REFINE` (gained=0,lost=0), `REJECT` (lost≥1), `REFUSED` (no probes/vocab mismatch). Only `ADMIT` may call `apply_if_admitted(persist=True)` to touch live weights. Measured naïve baseline: 32 receipts all `loss_delta>0` but agreement 5/32 with 3 regressions — admission gate closes this hole.

### 4.3 Verified Skill / Workflow Stores (durable, scoped)
**File:** `canonical/swe_kernel/verified_skill_crystallizer_v1.py` (SQLite WAL + bundles)

- Store: `VerifiedSkillStore(db_path=_default_db_path(), seed)` — seeds from `VERIFIED_SKILLS_BUNDLE_V1.json` / `COMPILED_WORKFLOWS_BUNDLE_V1.json` on first run.
- Key methods: `crystallize_verified_fix(language, bug_class, before_code, after_code, ...)`, `recall_and_apply_verified(source_text, language, error_class, verifier)`, `lookup_rules(language, error_class)`, `import_bundle(bundle)`.
- Gate: `_admission.evaluate` (held-out victims) + `lesson_admission_gate` + equivalence proofs (`_C.UNKNOWN` → undecided); ungated admission cannot be resurrected by equivalence alone.
- Re-check: `skill_recheck_v1.recheck(rule)` with `training_verification`/`twin_verification`/`provenance{before_sha256, after_sha256, taught_sources[]}`; merge preserves stronger admission, aggregates `provenance_json`.
- Production call sites: `software_repair_crossfile_choreograph_v1.py` (Python `python_test_repair` lookup → `apply_crystallized_code_rule` → verify → crystallize), `polyglot_build_ci_engine_v1.py` (cpp/rust/go/ts `recall_and_apply_verified` + `crystallize_verified_fix`).
- Current bundles:
  - `VERIFIED_SKILLS_BUNDLE_V1.json`: 5 rules (python×2, go, ts, rust), `verified_hits=1` each, no admission/training fields populated in export (bundle is a projection).
  - `COMPILED_WORKFLOWS_BUNDLE_V1.json`: 11 workflows, `hit_count=0`, `qualification PASS__CAPABILITY_INTERNALIZED__DONOR_ABSENT_AT_RUNTIME`, postcondition `stdout_equals` with placeholders (`?str0`, `?path0`).

**File:** `canonical/swe_kernel/causal_trace_to_skill_compiler_v1.py` / `autonomous_awake_loop_v1.py` / `software_repair_crossfile_choreograph_v1.py` + `solve_v1.py` — durable workflow/skill stores that **do persist** but are **not broad one-shot learning**; do not conflate.

### 4.4 Acquired Operator Memory (durable via re-derivation)
**File:** `canonical/runtime/acquired_operator_memory_v1.py` (state `canonical/runtime/state/acquired_operators_v1.json`)

- `teach(kind, words, examples, path)` → `operator_acquisition_v1.acquire_from_examples(kind, words, pairs)`; on success stores `{words, examples: [[float(v)], float(answer)], arithmetic}` under `state["taught"][kind]` (plain JSON, atomic `write_text` + `os.replace`).
- `recall()` → list of taught rows.
- `restore(path)` → for each taught row not already in `value_algebra_v1.aggregate_names()`, re-runs `acquire_from_examples` with same words/examples; collects `restored`/`already_declared`/`failed` (one bad row does not stop rest). Called once at door import via `inspect_v1._restore_acquired_operators()` (`_RESTORED` guard).
- Design: demonstration **is** the operator — re-derivation checks (`_usable`, `induce_laws`, `_law_is_falsifiable`, `indistinguishable_from`), so stale arithmetic is refused on load.

### 4.5 Self-Improvement State
- `canonical/runtime/SELF_IMPROVEMENT_STATE_V1.json` — **not present** in this checkout (episodic, not durable across this branch).
- `canonical/astra_runtime/state/ASSOCIATIVE_MEMORY_V1.json` — present (7025 bytes, `PROJECT_BRAIN_ASSOCIATIVE_MEMORY_V1`, tracked) — used by `transfer_learning_v1` / `transition_system_identity_v1` style recall.

---

## 5. Computer Use & OSWorld

### 5.1 H100 Computer-Use Registry (narrow, verified)
**File:** `canonical/runtime/h100_computer_use_registry_v1.py` (`PROJECT_BRAIN_H100_COMPUTER_USE_REGISTRY_V1`)

- 4 capabilities, all `kind: DIRECT`, `persistent_learned_bytes: 0`:
  - `CAP_FS_LIST_V1` (FILESYSTEM_LIST, pre: project_present, eff: files_known, cost 1, prior `H100_COMPUTER_USE_FILESYSTEM_VERIFICATION_V1.json`)
  - `CAP_FS_READ_V1` (FILESYSTEM_READ, pre: files_known, eff: file_contents_read, cost 1)
  - `CAP_FS_WRITE_V1` (FILESYSTEM_WRITE, pre: project_present, eff: file_written, cost 2)
  - `CAP_PROGRAM_RUN_V1` (PROGRAM_RUN_CONFINED, pre: project_present, eff: program_effect_verified, cost 5, prior `H100_COMPUTER_USE_CONFINED_EXECUTION_VERIFICATION_V1.json`)
- Routes: `_fs_list` (re-reads after acting, escapes-root check), `_fs_read`, `_fs_write`, `_program_run` (binds `code/text/input_path` correctly, file-vs-code disambiguation), `CAP_PROGRAM_RUN_V1` via confined execution + independent artifact check.
- Reachability: via `grounded_action_v1` (bind-first + decisive margin + independent byte re-read), `capability_forge_v1`, `chain_v1`, `macro_v1`, and OSWorld policy compositions. **No generic GUI operation** — filesystem + program only.

### 5.2 OSWorld Surface (extensive, not broadly verified)
**Components:** `osworld_v21_*` (89 source-index ORPHANs), `osworld_computer_surface_v1.py`, `h100_computer_use_registry_v1.py`, `grounded_action_v1.py`, plus 36 `test_osworld*` files.

- **Policy stack:** `workflow_policy_v1`→`v13` (V13 = deterministic current GUI goal verification via `osworld_v21_gui_goal_verifier_v1.verify_gui_goal`), `app_policy_overlay_v1`→`v5`, `browser_ops`, `host_*_ops`, `state_ops`, `visual_*`, `qwen35_planner`, `generic_policy`, `recovery_policy`, `constraint_guard`, `runner_binding`/`runner_bridge`.
- **Agent adapters:** `BrainOSWorldAgentV1`→`V8` (increasing capability), `brain_subject_v1`→`v19` (`v19` = V8 + `workflow_policy_v13` + `positioned_ocr_observer`, subject ID `brain-osworld-v21-model-independent-gui-goal-verification-v19`).
- **Runner integration:** `osworld_v21_runner_bridge_v1.py` — `build_agent(policy_provider, policy_id, ...)` + `bind_agent_environment(agent, env)` + `run_native_example(lib_run_single, agent, env, example, max_steps, instruction, args, result_dir, scores)` — delegates to **upstream** `lib_run_single.run_single_example` + `env.evaluate()`, no evaluator fork.
- **Submission entrypoints:** `osworld_v21_submission_entrypoint_v1/v3` — freeze protocol (`pyautogui`, `screenshot`, 500 steps, 1920×1080, `eval_version v2`), set `PromptAgent = _factory → build_subject()`, install runner binding, write `brain_osworld_subject_receipt.json`. V3 is the frozen product-API-capable subject.
- **Evidence gap:** `COMPUTER_USE_CHECK_DENSITY_20261116_V1.json` covers 9 transformations/34 mutants: full content state distinguishes 34/34 replays, but **novel-work detection catches only crashes/no-ops (density 0.5)**. OSWorld files are in canonical with extensive governance (pinned `osworld-v2.1` references, hash manifests `osworld-v2.1.json` + `osworld-v2.1.task_hashes.json`, task hash pre-check before execution) but **no Brain-run on the 108-task universe** has been established in this environment.
- **Local Qwen workflow:** `.github/workflows/osworld-v21-local-qwen-policy-smoke-v1.yml` — builds pinned `llama.cpp@bec4772` server, verifies `Qwen3.5-9B-M-TS-Q4_K_M.gguf` (5060174144 bytes, sha `f41c0a...`), runs 2-cycle synthetic browser smoke (OBSERVE → CLICK_TEXT/CLICK_ROLE), expects `terminal_cases_consumed=0` (synthetic, not benchmark data). This is the **only executable OSWorld-related workflow** currently runnable without Docker/VM.

---

## 6. Evidence & Limits (producer-run, not §6)

- **Single-trace identifiability** (`A_SINGLE_TRACE_DOES_NOT_PIN_THE_RULE_20261120_V1.json`): 15 rows, 30 commits, candidate space 150,809–154,157 per row. 13 rows **zero demand-matching candidates**, 1 row with 2 distinct test-passing alternatives (47 tests green). Establishes that one trace does not pin the rule — §6 remains unestablished.
- **Real-commit repair** (`REAL_COMMIT_REPAIR_20261116_V1.json`): 0 solved / 90 proposals across sampled real commits.
- **Structural rewrite induction** (`STRUCTURAL_REWRITE_INDUCTION_20261116_V1.json`): 0/5 structural rewrites solved.
- **Check-density** (`COMPUTER_USE_CHECK_DENSITY_20261116_V1.json`): full content checks distinguish all 34 replay mutants; novel-work checks density 0.5.
- **Rung gradient** (`GENERALIZATION_RUNG_GRADIENT_20261112_V1.json`): not independently reproduced here — producer-run only.
- **OSWorld direct-matched run / pin-reduction verifications:** referenced but **no artifacts** `OSWORLD_V21_DIRECT_MATCHED_RUN_20261011_V1.json` / `OSWORLD_V21_OFFICIAL_COMPONENT_PIN_REDUCTION_VERIFICATION_20261011_V1.json` not found — consistent with no local run.
- **Generalization experience corpus (current):** 24 successes, 8 embeddings — presence ≠ broad transfer or failure-safe learning.

All of the above are **sandbox/producer measurements**, not external proofs. They must be treated as falsifiers/calibration surfaces, not as capability credits.

---

## 7. Benchmark Feasibility (audit-only)

**Current sandbox constraints (measured):**
- Python 3.11.2, 2 CPUs, 3.8 GB RAM, 290 MB repo, `/dev/kvm` **false**, `docker`/`podman` **null**, `pytest`/`numpy`/`torch`/`PIL`/`playwright`/`selenium`/`harbor`/`terminal_bench`/`osworld` **not installed**, `pytest` binary missing, `kvm-ok`/`qemu` absent.

| Benchmark | Scope & Protocol | Local Feasibility | What Can Be Done Here | Primary Sources Checked |
|---|---|---|---|---|
| **OSWorld 2.x / 2.1** | 108 long-horizon workflows; median human 1.6h / 318 tool calls; best reported 20.6% (500-step, 54.8% partial); official release `osworld-v2.1` (326 tests pass, 108 task hash checks); Task029 startup-timeout issue | **No** — requires Linux x86-64, KVM, Docker, ~214 GB VM images, 8 GB/4 vCPU per guest; paper is v2, no official 2.1 paper | Audit governance pins, verify submission entrypoints/bindings, review synthetic Qwen smoke workflow; **no task execution** | `github.com/xlang-ai/OSWorld-V2/releases/tag/osworld-v2.1`, `arxiv.org/html/2606.29537v2` |
| **SWE-bench Pro V2** | 642 Harbor tasks, HARD-51, locked offline agent phase + fresh-sandbox patch re-grade; oracle 642/642, empty 0/642 | **No** — `harbor` not installed, no container runtime | Audit adapter surfaces (`harbor_brain_agent`, `harbor_science_*`, `coding_control_kernel_v1`) and governance manifest `TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json`; compile capability propositions only | `github.com/scaleapi/SWE-bench_Pro-os/.../v2/README.md` |
| **Terminal-Bench 4.1** | 66 tasks (63 CPU-only `terminal-bench-cpu@4.1.0`), verifier fixes, pinned digests, Reward Kit; release 2026-11-03 | **No** — no `harbor` runner, no Docker | Audit `terminal_closure_reducer`, `terminal_autopilot_v1`, `terminal_root_decision_gate_v1`, and `ZERO_COST_EVALUATION_ROUTE_MATRIX_V1.json`; verify literal-score separation | `github.com/harbor-framework/terminal-bench/releases/tag/v4.1.0` (66/63 confirmed) |
| **OSWorld-Science** | 164 tasks (paper: 146/7 domains), 8 runner domains, Linux x86-64 + KVM + Docker, 8 GB/4 vCPU/guest, ~214 GB images | **No** — KVM absent, resources insufficient | Audit `harbor_science_*` planner/agent/planner, evidence store, DNA-storage agent; no VM boot | `github.com/DiscoAILab/OSWorld-Science` |
| **SkillLearnBench** | v1: 20 verified tasks/15 subdomains, one-shot avg 30.44% vs human 74.5% vs no-skill 10.17%; external feedback helps, self-feedback drifts | v1 paper only; v2 page fetch failed | Audit `verified_skill_crystallizer` vs SkillLearnBench distinction (scoped repair vs broad OSWorld) | `arxiv.org/html/2604.20087v1` |
| **AgentCL / Prolex / Diff. Exact Learning** | Controlled compositional streams (memory trade-offs), DSL-constrained program synthesis (80% consistent in 120s), exact algorithms with spurious controllers matching all training traces | Literature only | Preserve as design cautions: memory can degrade, DSL ≠ unrestricted GUI, training-trace match ≠ proof | `arxiv.org/html/2606.02461v2`, `2305.03129v4`, `2611.21486v1` |

**Policy gate:** Per `CURRENT_DEVELOPMENT_AUTHORITY`, benchmarks may authorize development **only** as audit/falsifier/calibration-surface/causal-probe that is the cheapest non-dominated probe for an unresolved general-capability question, with minimum certificate cover (`minimum_capability_certificate_cover_v1.py`). No benchmark-specific action has met that bar in this sandbox.

---

## 8. Open Obligations & Current Frontier

From `CANONICAL_POINTER` → `RECOVERY_BRAIN.sqlite` + `CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json` (expected but missing in checkout):
- Last recorded global truth (from CANONICAL_POINTER's `current_global_truth` snapshot): `ACTIVE_V21__TERMINAL_FALSE`, cut `CURRENT_ZERO_REALITY_MINIMUM_CUT_V21.json` (blob `8a67a989...`), atomic proved 14 / open 24, meta open 8, total 32 obligations, 5 live action groups + 2 active programs / 1 dormant; **scheduling authority true, execution/promotion/fresh-reality false**.
- Terminal status: `TERMINAL_FALSE — 12 of 19 families open, 20 of 38 atomic predicates unresolved` (from `critical_blocker`).
- Last real output event: `WAL_RECOVERY_ORDERING_TB4_VERIFIED_PASS_20261001` (1 real task, reward 1, 97 tests × 10 determinism, independent verification, but **zero whole-family credit** due to breadth/score not yet ≥66.4 on distinct fresh set).

**Do not treat these as live** without re-reading the current cut/authority files at the canonical commit — they are stale snapshots.

---

## 9. Errors & Dead Ends (this mission)

- **No test execution:** `pytest` unavailable, `unittest` not attempted for OSWorld/Harbor suites — only static inspection.
- **No benchmark execution:** OSWorld/SWE-bench/Terminal-Bench all require Docker/KVM/Harbor not present.
- **Broad grep truncation:** `rg`/`git grep` provider/route listings truncated at ~10k lines — targeted call-graph audit remains.
- **SkillLearnBench v2:** primary page fetch failed; v1 paper used.
- **Registry query error:** earlier `dict` slice error corrected via proper iteration.
- **Model artifact size:** `BRAIN_UNIFIED_MODEL_V1.json` is 11.2 MB — reads truncated in tool output; structured Python re-checks used instead.

---

## 10. Recommendation — Next Research Steps (no implementation)

1. **Provenance audit:** Re-verify live registry → adapter → receipt → OIDC chain for a sampled bound capability; confirm `independent_verification_evident` semantics for OSWorld subjects vs H100 filesystem capabilities.
2. **Skill admission audit:** Sample the 5 verified skills + 11 workflows — check `crystallize_verified_fix` admission receipts, `skill_recheck` outcomes, and `recall_and_apply_verified` re-verification paths.
3. **Generalization admission audit:** Run `weight_update_admission_v1` on the 24 stored experiences against the full probe stream — measure ADMIT/REJECT/REFINE rates; confirm no silent weight drift.
4. **Fabric route audit:** Trace `unified_cognitive_fabric_v1.run` → `closed_loop_autonomous_controller_v1.solve_or_learn` → `semantic_generalization_engine` vs `VerifiedSkillStore` vs computer boundary — map which goals reach which tier under `learn=true/false`.
5. **Benchmark protocol collation:** Compile each benchmark-derived claim into exact capability propositions + optional separate literal score predicates (per `BENCHMARK_OUTPUT_INFORMATION_EQUIVALENCE_LAW_V1`), without scheduling any run.
6. **Governance reconciliation:** Re-materialize missing `ACTIVE_GOAL_HIERARCHY`, `CURRENT_LIVE_WORK_FRONTIER`, `CURRENT_TERMINAL_AUTHORITY`, `CURRENT_ZERO_REALITY_MINIMUM_CUT` at the current base commit before any execution authority is claimed.

**No capability selection, synthesis, or benchmark execution is authorized until the relevant V11/V12 gates and live selection are reconciled and `TERMINAL_FALSE` is addressed via proper channels.**

---

## 11. Artifacts & Paths (for verification)

- Governance: `canonical/CANONICAL_POINTER.json`, `canonical/governance/CURRENT_DEVELOPMENT_AUTHORITY.json`, `canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V11.json`, `canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V11.json`
- Model: `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json`, `canonical/runtime/compile_brain_unified_model_v1.py`, `canonical/runtime/brain_unified_model_v1.py`
- Runtime: `canonical/runtime/unified_cognitive_fabric_v1.py`, `canonical/runtime/live_brain_route_admission_v1.py`, `canonical/runtime/live_integrated_brain_v1.py`, `canonical/runtime/verified_bound_capability_execution_adapter_v1.py`
- Learning: `canonical/swe_kernel/instant_one_shot_learning_v1.py`, `canonical/swe_kernel/semantic_generalization_engine_v1.py`, `canonical/swe_kernel/weight_update_admission_v1.py`, `canonical/swe_kernel/verified_skill_crystallizer_v1.py`
- Memory: `canonical/runtime/acquired_operator_memory_v1.py`, `canonical/runtime/inspect_v1.py`, `canonical/astra_runtime/generalization/*.json`, `canonical/astra_runtime/skills/*.json`, `canonical/astra_runtime/state/*.json`
- Computer use: `canonical/runtime/h100_computer_use_registry_v1.py`, `canonical/runtime/grounded_action_v1.py`, `canonical/runtime/osworld_v21_*`, `.github/workflows/osworld-v21-local-qwen-policy-smoke-v1.yml`
- Evidence: `canonical/verification/*.json` (single-trace, real-commit, structural-rewrite, check-density, rung-gradient)
- Benchmark pins: `canonical/governance/PUBLIC_BENCHMARK_SOURCE_PINS_V1.json`, `canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json`, `canonical/verification/TERMINAL-*`

---

*End of Report — Reconnaissance Only. No execution, promotion, or fresh-reality authority exercised.*
