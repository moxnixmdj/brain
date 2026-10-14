# Complete enumeration of limiting factors between the current state and the terminal goal

**Date:** 2026-10-14 · **Repo HEAD:** `11d4d83` (main, after PR #4697) · **Branch:** `arena/9672736d-brain`
**Method:** every count below was read from a live artifact or produced by running the repository's own gate/scheduler in this session. Items marked **[LIVE]** were executed or queried live today (gate run, scheduler run, `gh` API, unittest). Items marked **[RECEIPT]** come from a dated repository artifact (path given). Nothing is from memory. Where two artifacts disagree, both values are shown and the newer one is identified.
**Credit claimed by this document:** zero. It changes no predicate.

---

## 0. What "the terminal goal" is — and limiting factor #0

Two different objects are in play, and conflating them is itself a limiting factor:

| Object | Definition | Can it be "reached"? |
|---|---|---|
| **Real mission** (`canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json`, pointed to by `CURRENT_MISSION_OBJECTIVE.json`, 2026-10-13) | `BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE`; `mission_terminality = OPEN_ENDED_CAPABILITY_OPTIMIZATION_NO_FINITE_FRONTIER_MODEL_OR_BENCHMARK_DEFINES_FINAL_MISSION_COMPLETION` | **No, by definition.** The repo forbids deriving `GLOBAL_OPEN_ENDED_MISSION_COMPLETE` from anything. |
| **Terminal checkpoint** = `OPUS_5_5_USEFUL_CAPABILITY_OWNERSHIP_V1` (`CURRENT_TERMINAL_AUTHORITY.json` → `checkpoint_objective`; `opus_5_5_role = FIRST_FRONTIER_CHECKPOINT_NOT_TERMINAL_OBJECTIVE`) | Permanently internalize, configure, verify and own all useful Claude Opus 5.5 capabilities at ≥ Opus 5.5 level; knowledge external/JIT only; hard $0 incremental spend. Mandatory predicate: `TERMINAL_CLOSURE_REDUCER_ACHIEVED_TRUE` (`terminal_semantics_override`). | Yes — this is the only finite goal the system can close. Everything below is about this object. |

**Limiting factor #0:** the checkpoint has been demoted to "tertiary audit" in the live scheduler (`scheduler_precedence`: *"…OPUS_5_5_CHECKPOINT_WORK_IS_TERTIARY_AUDIT…"*), and all 12 open checkpoint rows are **wake-gated** (§6). So the system, by its own rules, does not currently schedule any internal work that could close the checkpoint on unchanged information. Closing it requires external reality events, not more internal proof.

---

## 1. The live verdict and its exact decomposition **[LIVE]**

`python3 -m canonical.runtime.terminal_reality_gate_v1` (schema `PROJECT_BRAIN_TERMINAL_REALITY_GATE_V3`), run this session:

```
terminal_real = false        declared_terminal = false
phase = FROZEN_PROTOCOL_ACCEPTANCE_AND_OWNERSHIP
frozen_family_count = 19     verified_owned = 7     open = 12
blockers = [CLOSE_AGGREGATE_FROZEN_PROTOCOL_AND_OWNERSHIP_PREDICATE]
closure_failed_predicates (16):
  DONOR_AUTHORITY:DONOR_AUTHORITY_REPOSITORY_ROOT_REQUIRED
  FAMILY_OPEN:<12 families listed in §4>
  PREDICATE_NOT_TRUE:all_frozen_opus_acceptance_predicates_pass
  PREDICATE_NOT_TRUE:donor_dependent_required_behaviors_zero
  PREDICATE_NOT_TRUE:final_donor_deletion_cleanroom_pass
  PREDICATE_NOT_TRUE:proof_bundle_frozen
```

Frozen terminal predicate (critical-path plan §1, unchanged):
**T = (19/19 families acceptance PASS) ∧ (8/8 meta closed) ∧ (donor V2 requalification complete) ∧ (aggregate frozen predicate + scheduler root sound) ∧ (global postconditions re-proved).**
Current: **7/19 ∧ 0/8 ∧ 0/12-requirements ∧ false ∧ invalidated.** Each conjunct is expanded below.

Optional stronger route (not required for T, all false): `abc_closed`, `current_U_empty_proved`, `d_finality_field`, `selected_cover_complete`. `closed_ABC_refinement_family_count = 6`, `open = 13` (`CURRENT_TERMINAL_AUTHORITY.json live_truth`).

What is **not** blocking (so no effort is wasted there): raw terminal execution 3352/3352 PASS; 12/12 whole-scope behavioral contracts; 19/19 provisional behavioral family rows; all 7 non-acceptance counters zero; `root1 positive_gap_count = 0` (no admitted *capability* gap anywhere — every blocker is acceptance-evidence, ownership-proof, carrier, or policy). Anti-bureaucracy flags: generator completeness and global rank/resource potential are **not** prerequisites.

---

## 2. Layer A — the four false aggregate predicates + the donor-authority root

Source: `canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json` (8 true / 4 false), live gate.

| # | Predicate | Why false | What would make it true |
|---|---|---|---|
| A1 | `all_frozen_opus_acceptance_predicates_pass` | 18/38 registry atoms proved, **20 unresolved** (§4); only 7/19 families pass strict Opus-5.5 acceptance | All 20 atoms resolved → 19/19 families |
| A2 | `donor_dependent_required_behaviors_zero` | Revoked 2026-10-11 by `CAPABILITY_TRANSFER_V2_DONOR_AUTHORITY_INVALIDATION_20261011_V1` — the old boolean "donor independence" was proved by network denial only, which does not exclude a local/rehosted model | Donor V2 requalification (§5) |
| A3 | `final_donor_deletion_cleanroom_pass` | Same invalidation; the clean-room replay must be re-run under protocol V2 after the final route bytes are frozen (`post_u_tail`: FREEZE → LOCAL_C → RECOMPUTE_D → DELETE_DONORS → CLEAN_ROOM_REPLAY → REDUCER) | Re-execution after A1 closes (it is **not** allowed to run as parallel research — `scheduling_lock`) |
| A4 | `proof_bundle_frozen` | `FINAL_TERMINAL_PROOF_BUNDLE_20261002_V1` **invalidated** (`FINAL_TERMINAL_PROOF_BUNDLE_INVALIDATION_20261002_V1.json`): it treated provisional 12-contract→19-family behavioral adjudication as if it closed the predeclared acceptance protocols | A new bundle can only be frozen after A1–A3 |
| A5 | `DONOR_AUTHORITY:DONOR_AUTHORITY_REPOSITORY_ROOT_REQUIRED` | `donor_authority_reconciliation.current_donor_independence_proved = false`; checkpoint manifest additionally lists `GLOBAL_OWNERSHIP_RECEIPT_{NOT_INDEPENDENT_PASS, PREDICATES_MISSING, REDUCER_BLOB_STALE, UNBOUND:BINDING_SHAPE_INVALID}` | Bind a current hardened reducer blob + independent pass (§5 req. 12) |

Dependency: A2–A5 are **downstream** of A1 by rule (`DO_NOT_SCHEDULE_D_FINALITY_AS_PARALLEL_RESEARCH`). So the whole terminal is serialized behind the 12 open families.

---

## 3. Layer B — the 12 open families → 20 unresolved atoms → 13 independent obligations

Closed (7): COMPLEX_MULTI_TOOL_AGENCY, INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT, LONG_HORIZON_MEMORY_AND_CONTINUITY, SUBAGENT_DELEGATION_AND_COORDINATION, SELF_VERIFICATION_DEBUGGING_AND_RECOVERY, TOOL_DISCOVERY_SELECTION_AND_LEARNING, EXACT_SYMBOLIC_COMPUTATION.

All 12 open families carry `unresolved = [OPUS55_ACCEPTANCE_PROTOCOL_RESULT_OPEN]`, `acceptance_basis = null`, ownership `PROVISIONAL_TERMINAL_BEHAVIORAL_PASS__…`. Atom status from `OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json` × `…EVIDENCE_BINDINGS_V3.json` (18 atoms have **no claim row at all**; 2 are `EXTERNAL_BLOCKED`). Per-row "remaining class" from `CURRENT_ALL_OPEN_CHECKPOINT_WAKE_GATE_RECONCILIATION_20261011_V1.json` (**12 open rows, 0 same-information-runnable, 12 wake-gated, 1 parked**).

### 3.1 ADVANCED_AGENTIC_CODING — 3 atoms, all open

| Atom | Bar | State & causes | Remaining class (wake) |
|---|---|---|---|
| `CODING_TB4_GE_66_4` | Terminal-Bench 4: ≥66.36% = **219 of 330 trials** (66 tasks × 5; owner refresh 2026-10-08) | **No claim row.** Two ledgers: (i) 2026-10-02 `TB4_ATTAINABILITY_CUT_VERDICT`: upper bound **180 < 220 → IMPOSSIBLE** under no-replay rules (independently verified); (ii) 2026-10-08 `TB4_CURRENT_OWNER_TARGET_ATTAINABILITY_RECOMPILE`: 44 creditable tasks → 220 slots vs 219 required → **attainable with slack 1** (newer, supersedes for the matched target; `score_proved=false`, `execution_authority=false`). Physics: 220–225 trials × ~15 min ≈ **≥55 wall-hours on a 16-core carrier ≈ 880 core-hr** at **≥99.5% success** (Opus 5.5 itself scores 66.4%). Zero-cost capacity: Codespaces 7.5 wall-hr/mo of 16-core; Actions 2,000 min/mo (currently billing-blocked, §6); CircleCI candidate 625 min/mo 8-core; Buildkite preflight unexecuted. `TB4_EXISTING_SUCCESS_EVIDENCE_EXHAUSTION`: pass and fail completions both satisfy current bound evidence → nothing internal distinguishes. `private_exact_opus_capacity_state = UNKNOWN__GITHUB_ACTIONS_PRE_STEP_INFRASTRUCTURE_BLOCK`. | `DISTINGUISHING_OFFICIAL_VERIFIER_INFORMATION_OR_STRONGER_SCOPE_COMPLETE_CERTIFICATE`; wake conditions: distinct frozen official verifier slot outcomes / new scope-complete cross-slot premise / canonical tree change adding admissible success evidence. `same_information_retry_authority = false`. |
| `CODING_FRONTIERCODE_GE_54_4` | FrontierCode 1.1 Main ≥54.4 (owner target refreshed 54.64) | **No claim row.** Private tasks cannot be self-run; evaluation only on request from Cognition via Mercor Apex. Partner information request **sent 2026-10-11** to apex@mercor.com cc info@cognition.ai (`action_intents/FRONTIERCODE_PARTNER_INTAKE_REQUEST_20261011_V1.json`): `response_pending=true`; eligibility, harness, zero-cost terms, protocol binding all **unbound**. Classified "optional measurement wake event", not a capability gate. | `OWNER_OR_SCOPE_MEMBERSHIP_SCORE_MASS_OR_STRONGER_CERTIFICATE` |
| `CODING_CURSORBENCH_GE_57_8` | CursorBench 4.0 ≥57.8 | **No claim row.** Direct owner reply 2026-10-03 (`CURSORBENCH_OWNER_ACCESS_BOUNDARY_V1.json`): internal suite, **no owner-run evaluation of external systems, no public submission interface, private tasks stay private**. Internal route `OPEN_BLOCKED`: two exact 4.0 scoring objects unbound (per-task grader output domain & score contribution rule; aggregation denominator/weights). Five constructive regions proved (34 condition atoms) but `cursorbench_five_region_complement_emptiness_identified=false`; internal state `DORMANT_INFORMATION_BOUNDARY`; sixth-region work forbidden until a genuinely new Brain-owned coding policy strictly expands the union. | `OWNER_GRADER_RESULT_OR_NEW_CONSTRUCTIVE_PARENT_EVIDENCE`; reopen only on material owner policy/interface change |

Also open at the capability level (not acceptance): `coding_whole_specification_cover_closed=false`, `coding_v5_common_policy_certificate_ready=false`.

### 3.2 PROFESSIONAL_KNOWLEDGE_WORK — 2 atoms

| Atom | Bar | State & causes | Remaining class |
|---|---|---|---|
| `PROWORK_GDPVAL_GE_1846` | GDPval-AA Elo ≥1846 (frozen epoch; current public Opus 5.5 reference **1866 ±26**, methodology 4.3.2, Crowd-BT, 3-model LLM judge panel) | **No claim row.** No Brain owner Elo exists (`hard_nonclaims`). Routes: matched-score `OPEN_SLEEP`; target-relative pairwise `OPEN_SLEEP_CHECKED_PUBLIC_SURFACES`; absolute-dominance `OPEN_ACTIVE` but `gdpval_w_cover_proved=false`, `gdpval_w_quality_proved=false`; `24_of_24_property_truth_sufficient_for_target=false`. Public 220-task surface fully compiled (rubric manifest, imperative directives, submission contract, Crowd-BT kernel) but the owner's historical judge-quality/fit state is not public, so the public kernel cannot reproduce the owner Elo. Full judge panel not callable at $0. | `MATCHED_EPOCH_SCORE_RECEIPT_OR_STRONGER_SCOPE_COMPLETE_FIXED_BAR_CERTIFICATE` |
| `PROWORK_AA_BRIEFCASE_GE_1822` (shared truth with `ARTIFACT_AA_BRIEFCASE_GE_1822`) | AA-Briefcase v1.1 Elo ≥1822 (frozen 2026-09-22; current epoch 1807) | **No claim row.** `AA_BRIEFCASE_OUTREACH_STATE_20261011_V1.json`: 3 messages sent to contact@artificialanalysis.ai (10-03, 10-05, 10-07), **0 inbound replies**; threaded follow-up **drafted, not sent** — `reason_not_sent = GMAIL_SEND_DRAFT_REQUIRES_USER_REVIEW_OR_EXPLICIT_SEND_REQUEST`. Proved: Professional 24/24 does **not** entail the private 91-task pairwise result. No official no-fee full-agent contract published. | `MATCHED_EPOCH_RECEIPT_OR_OWNER_ADMISSIBLE_PRIVATE_SCOPE_RELATION_OR_SCOPE_COMPLETE_DOMINANCE_CERTIFICATE`; wake = authenticated AA reply satisfying `AA_BRIEFCASE_OWNER_EXECUTION_DECISION_V1.schema.json` |

Internal precondition also stuck: Professional property truth is **24/24** with 0 open leaves, but promotion requires the full private current-main regression, whose carrier is blocked (§6) → `exact_next = SLEEP_FULL_PRIVATE_CURRENT_MAIN_REGRESSION…`.

### 3.3 BUSINESS_WORKFLOW_AUTOMATION — `AUTOMATIONBENCH_GE_40`
No claim row. Public 600 tasks + zero-paid-provider runtime are bound; **public→private scope transfer not proved**; the finite-API-grammar shortcut was **falsified**. Remaining: `PRIVATE_TASK_CONTRACT_SCOPE_OR_EXACT_PRIVATE_RESULT_OR_STRONGER_TARGET_SCOPED_CERTIFICATE`.

### 3.4 MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING — `HLE_TOOLS_GE_67_7`
No claim row. Dataset location/size known (2,500 items) but access is **authenticated, terms-gated**; Anthropic's "with tools" protocol is **publicly under-specified** → no comparable protocol can be bound. Remaining: `AUTHENTICATED_FULL_2500_ACCESS_PLUS_COMPARABLE_PROTOCOL_OR_SOUND_CONSERVATIVE_SCORER_RELATION_PLUS_THRESHOLD_RECEIPT`.

### 3.5 AGENTIC_SCIENTIFIC_RESEARCH — `TB_SCIENCE_GE_58_7` (**parked**)
`CURRENT_TB_SCIENCE_EXECUTION.json` (2026-10-11): **20 benchmark trials consumed, 0 successes, 20 FINAL_ZERO**; status `RANK23_UNREAD_UNSTARTED__BENCHMARK_AUDIT_FROZEN__GENERAL_CAPABILITY_CLOSURE_REQUIRED`. Failure roots on record: controller protocol fatal abort (rank 15), planner/controller failure before first action (18), identity version skew V2 runner vs V1 agent (19, non-consuming), external Qwen cognition producer path → credit revoked (21), typed-action admission mismatch + planner truncation + stale start-CAS import (21), zero-model route rank 22 → reward 0. No retry/replacement authority on any consumed slot (no-replay). `next = EXPAND_TASK_INDEPENDENT_SCIENTIFIC_SEMANTIC_COMPILATION…KEEP_RANK23_UNREAD_UNSTARTED`. Cause class: **real capability shortfall on the zero-model scientific route**, plus serial one-slot consumption physics.

### 3.6 VISION_AND_DENSE_DOCUMENT_UNDERSTANDING — 2 atoms
- `CHARTOGRAPHY_TOOLS_GE_89`: no claim row. Public runner has **no authorized HF credential**; official git/raw/dataset-viewer routes are **401/auth-gated**; **zero gold parsed**; reasoning/harness gap explicitly *false* (it is an access problem). Remaining: `AUTHORIZED_OFFICIAL_HF_BYTE_ACCESS_OR_OWNER_EQUIVALENT_CONTENT_ADDRESSED_100_TASK_PACK_OR_STRONGER_CERTIFICATE`.
- `VISION_DENSE_NONCHART_SCOPE`: collapsed into the shared AA-Briefcase professional-quality fact → blocked by 3.2.

### 3.7 COMPUTER_AND_BROWSER_USE — `OSWORLD_2_1_PARTIAL_GE_81_8`
No claim row. Exact 108-task identity-hash universe closed; public-semantics route exhausted. Remaining: `AUTHENTICATED_PINNED_TASK_AND_ASSET_BYTES_PLUS_MATCHED_EXECUTION_OR_STRONGER_SCOPE_COMPLETE_CERTIFICATE`. Capability-side residual tracked in open issues **#4340** (typed OSWorld action + deterministic text grounding — prototypes pass focused tests, not internalized) and **#4343** (layered GUI perception fallback; OmniParser detector is a 281 MB model → conflicts with "models are not configured components" unless qualified).

### 3.8 FINANCIAL_ANALYSIS — 3 atoms
- `FINANCE_ACCOUNTING_INDEX_GE_61`: no claim row. Outer weights/threshold kernel closed; **numeric scale (inner normalization) binding unavailable** from owner. Remaining: `OWNER_INNER_NORMALIZATION_OR_NORMALIZED_COMPONENT_RECEIPT_OR_OWNER_ACCEPTED_EQUIVALENT_RESULT_OR_SCOPE_SAFE_DIRECT_NUMERIC_CERTIFICATE`.
- `FINANCE_AGENT_V2_GE_58_59`: no claim row. Held-out mass bound; published analytical-contract shortcut **falsified** by first-party implicit sector-convention requirements. Remaining: `EXACT_OFFICIAL_RESULT_OR_PRIVATE_SCOPE_BIND_OR_COMPLETE_CONVENTION_SEMANTICS_BOUND_OR_STRONGER_SCOPE_COMPLETE_CERTIFICATE`. Vals private execution: **`VALS_API_KEY_ABSENT`** on the independent carrier (`VALS_CREDENTIAL_PRESENCE_INDEPENDENT_RUNNER_20261007_V1.json`).
- `FINANCE_UNCOVERED_SCOPE_AUDIT`: **EXTERNAL_BLOCKED** — two frozen direct oracle leaves **unexecuted** (`POST_SOURCE_GATE_ROOT1_RECLASSIFICATION_V1.json`); `r2_task_specific_external_observation_frontier = FINANCE_SEMANTIC_ADEQUACY_TAIL` (the single remaining R2 external frontier; `finance_tail_globally_closed=false`).

### 3.9 ARTIFACT_CREATION — `ARTIFACT_AA_BRIEFCASE_GE_1822`
Duplicate truth of 3.2 (same measurement). Necessity audit (2026-10-14) flags it as alias-duplication deletion candidate p=0.40 — not yet falsified/verified.

### 3.10 COMMUNICATION_AND_SYNTHESIS — `SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR`
Metric identity removed as an independent job; raw semantics routed to ABC admission (`current_U_empty_proved=false`). Deletion candidate p=0.30.

### 3.11 UNKNOWN_DOMAIN_ADAPTATION — `MYSTERYMECHANISM_GE_49_55`
State `EXTERNAL_REQUIRED__NOT_PROVED`. Public owner scope does not bind an exhaustive private mechanism grammar or sufficient private success mass; scope-superset route saturated on the unchanged public source set; Brain has exact linear-polytope and noisy-minimax kernels (general assets) that do not create private 222-task evidence. Vals key absent (above). Wake: new owner mechanism class/generator, new scope relation, permitted comparable result receipt, or material benchmark change. Deletion candidate p=0.30.

### 3.12 MULTI_CAPABILITY_COMPOSITION — 3 atoms
- `COMPOSITION_COMPONENT_SCOPED_PROOFS`: **EXTERNAL_BLOCKED** — `COMPOSITION_COMPONENT_PROOF_CURRENT_AUTHORITY_V6.json`: **4 of 12** frozen component interfaces scoped-proved (memory, recovery, delegation, tool discovery); **8 open**: research, tool use, artifact creation, browser/computer action, coding, debugging, evidence synthesis, artifact production. Rule: no parent credit until all 12 + parent-matched + invariant predicates close; no credit by name/analogy.
- `COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR`, `COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES`: derived inside ABC; blocked by the above and by `complete_selected_context_ABC_closed=false`. Strongest deletion candidate (p=0.45, direct precedent) — unexecuted falsifier.

### 3.13 Cross-cutting evidence rules that make every row hard (registry V2)
All atoms of a family must pass before family promotion · matched predicates need exact Opus case-level access **or** a scope-complete stronger proof · **no Terminal V3 replay** · public bar cases are forbidden while `route_ready=false` · owner replies are route-boundary evidence, not scores · no private score/slot inference.

### 3.14 The 13 independent score obligations (frozen 13 claim V3)
TB4, FrontierCode, CursorBench, GDPval, AA-Briefcase (shared), AutomationBench, HLE, TB-Science, Chartography, OSWorld, Finance Index, Finance Agent v2, MysteryMechanism. **External-owner-gated: 8** (FrontierCode, CursorBench, GDPval, AA-Briefcase, AutomationBench-private, HLE access, Finance ×2 via owner/Vals). **Access/bytes-gated: 2** (Chartography HF, OSWorld pinned assets). **Compute/physics-gated: 1** (TB4). **Capability-real + serial-slot: 1** (TB-Science). **Scope-unbound external: 1** (MysteryMechanism).

---

## 4. Layer C — the 8 meta obligations (`ROOT1_TERMINAL_FAMILY_ENVELOPE_AUDIT_V6.json`)

| # | Obligation | State |
|---|---|---|
| M1–M5 | Domain mappings: CYBERSECURITY, BIOLOGY_R&D, AUTOMATED_AI_R&D, HEALTHCARE, MATHEMATICAL_REASONING_ARXIVMATH | Mapping checks unexecuted (necessity audit p≈0.75 each that they reduce to existing families — **not proved**) |
| M6–M7 | Conditions: MULTILINGUAL, LONG_CONTEXT parity | Open |
| M8 | CREATIVE_DIAGRAM composite performance | Basis repaired; **no cases generated** |

Rule: **no finality from 38/38 atoms alone** — these 8 must close independently.

---

## 5. Layer D — donor V2 requalification, postconditions, clean room

`canonical/verification/CAPABILITY_TRANSFER_V2_DONOR_AUTHORITY_INVALIDATION_20261011_V1.json` lists **12** requirements (the plan's "10/10" wording is stale): (1) protocol V2 bound; (2) external contribution census; (3) full runtime dependency inventory; (4) cognition class model-independent; (5) model dependency count zero; (6) external model runtime dependency zero; (7) online teacher calls zero; (8) teacher fallback paths zero; (9) copied/rehosted teacher absent; (10) Brain-owned operative artifact; (11) independent post-donor-removal qualification; (12) current hardened reducer blob bound (`terminal_global_ownership_postconditions_reducer_v1.py`, protocol `DONOR_DELETION_AND_DEPENDENCY_ACCOUNTING_PROTOCOL_V2.json`).
**Current: 0/12 re-proved.** Evidence that the risk is real: TB-Science rank 21 result credit was **revoked** for an `EXTERNAL_QWEN_COGNITION_PRODUCER_PATH`; `sitecustomize.py` must force `ASTRA_DISABLE_MODEL_PLANNER=1`.
Sequencing constraint: by rule these run **only after** U-empty/ABC or 19/19 — they cannot be pre-closed in parallel.

---

## 6. Layer E — carrier / infrastructure (verified live today unless noted)

| # | Factor | Live evidence | Effect |
|---|---|---|---|
| E1 | **GitHub-hosted Actions billing block** | Check-run annotation on today's failed jobs: *"The job was not started because recent account payments have failed or your spending limit needs to be increased."* Last 15 runs on main/PRs: all `failure`/`cancelled` with **0 steps**. | No hosted verification, no independent reverification on this carrier, no Actions share of TB4 compute. Repo-wide since 2026-10-02. **User action (Billing & plans); must stay $0.** |
| E2 | **Self-hosted `brain-regression` runner offline** | `Full private current-main regression` run 38510464438 is `pending` with **0 jobs**; `runs-on: [self-hosted, Linux, X64, brain-regression]`; `github_actions_runner_assignment_observed=false`. Runner list API → 403 (token). | **Both 24/24 promotions stuck** (Professional, Assurance UVCK V2) → `full_current_main_regression_open=true`. **User action (start runner).** |
| E3 | **Ubuntu-26 migration 2026-10-19** | Platform notice in annotations; **275 of 314 workflows** use `ubuntu-latest`. | In 5 days the hosted surface changes under every workflow; no pinning decision recorded. |
| E4 | **Token scope** | 403 on runners, billing, permissions, branch protection; plan notes no `issues:write`. | Agent cannot repair E1/E2/E3-infra, cannot close #3739, cannot enable protection. |
| E5 | **No branch protection on main** | Rulesets API: *"Upgrade to GitHub Pro or make this repository public"*; protection endpoint 403. | `REPOSITORY_PROMOTION_ENFORCEMENT` human half open; promotion gates are honor-system at the Git layer. **User action.** |
| E6 | **712 open PRs** + one-intent-per-PR serialization | `gh pr list --state open` → 712. | Merge queue is the real throughput ceiling (plan §6.3); independent-verifier capacity is shared across all lanes. |
| E7 | **Pre-existing failing test** | `python3 -m unittest tests.test_bytes_canonical_wiring` → `FAIL: test_bytes_authorities_are_live_and_exist` (stale V9 expectations vs V10 pointer). | Any "all tests green" gate on this path fails until repaired. |
| E8 | **Val→GitHub private migration incomplete** | `MIGRATION_STATUS_2026-09-10.json`: `cutover_allowed=false`, `source_retirement_allowed=false`, anonymous-access proof not verified. | Durable substrate / privacy postcondition not closed. |
| E9 | **Four zero-step carrier failures** on the full-regression carrier | Professional pointer: `full_private_regression_carrier_diagnosis = EXECUTION_CARRIER_BLOCKED__FOUR_ZERO_STEP_ACTIONS_FAILURES__NO_REGRESSION_RESULT`. | Confirms E1/E2 are the only blockers on the 2×24/24 credit. |
| E10 | **Astra scarce access** | `ASTRA_SCARCE_ACCESS_EXECUTION_ATTEMPT_20261006_V1.json`: 1 attempt, UI error, 0 results, retry on hold (quota cost unknown). | One intended external proof route unavailable. |
| E11 | **Vals API key absent** on independent carrier | §3.8. | Finance Agent v2 / Finance Index / MysteryMechanism private execution impossible from the carrier. |
| E12 | **No HF credential** on public runner | §3.6. | Chartography gold = 0 parsed. |
| E13 | Open issue **#3739** (R4 claim-binding defect) | Verified already repaired at HEAD (W1.2) but **still OPEN** — cannot be closed by the agent (E4). | Bookkeeping; no logical block. |

---

## 7. Layer F — scheduler / structural limits (live scheduler output)

`plan_current_post_composition_frontier()` **[LIVE]**: `ready = [BYTES_V81_NEXT_PHYSICAL_CUT, CHARTOGRAPHY_BRAIN_NATIVE_PROFESSIONAL_SEMANTICS_V2, CODING_GENERAL_SOFTWARE_REPAIR_LOOP_V10]`; **`vector_complete_candidate_ids = []`**; all three ready items are **read-only evidence work**; `parallel_full_execution_work_ids = []`; `execution_authority=false`; `promotion_authority=false`; `open_checkpoint_obligation_count=12`, `row_specific_same_information_runnable_count=0`, `wake_gated=12`, `parked=1`.

Consequences:
- F1 **Nothing with execution authority exists right now.** The selection law forbids scalar weights; incomplete vectors are evidence-only.
- F2 **Every checkpoint row is wake-gated** → the system will not spend effort on them until a content-addressed external event arrives (`DO_NOT_SPIN_ON_OPEN_CHECKPOINT_ROWS_USING_UNCHANGED_INFORMATION`).
- F3 **Four zero-reality kernel input classes** remain unproduced (normalized atoms for 11 predicates; complete matched universe for 6; finite judgment worlds for 2; frozen composition interfaces for 1) — the "cheapest truths" can't fire without inputs.
- F4 `router_registry_real_selected_cover_complete=false`, `current_U_empty_proved=false`, `D_finality_closed=false` — the optional universal route is further from closure than the frozen-19 route.
- F5 Independent verification is mandatory for every credit (`universal_route_fail_closed_requirements`), and the independent carriers are E1/E2-blocked.

---

## 8. Layer G — self-imposed policy constraints that are binding (not bugs; they define the goal)

G1 **$0 incremental spend, hard stop** (every artifact's `incremental_spend_usd=0`; Actions limit must not be raised if it risks spend).
G2 **No replay / no retry** of consumed benchmark slots (TB4, TB-Science) — failures are permanent.
G3 **No invention of private results**; owner replies are boundaries, not scores.
G4 **Models are not configured components; donor deletion required** (`CANONICAL_POINTER.json` policy flags) — closes off the easiest route (wrap a model).
G5 **No manual flags** (`NO_MANUAL_SELECTED_COVER_COMPLETE_FLAG`); only exact predicate sets.
G6 **No public bar cases while `route_ready=false`**; **no case-level Opus preference search for public fixed-bar scopes**.
G7 **Fail-closed everywhere** → any uncertainty resolves to "open", never to "pass".
G8 **D-finality cannot be parallelized** (serial tail after acceptance).

---

## 9. Layer H — actions only the user can take (exact list, unchanged across plans)

1. GitHub **Billing & plans**: fix the failed payment or wait for the included-minutes reset; keep spend at $0. (Unblocks E1, hosted verification, Actions compute share.)
2. Start / re-register the **`brain-regression` self-hosted runner** (unblocks E2 → both 24/24 promotions; state whether the host has ≥16 cores → TB4 self-host option).
3. **Approve/send the AA-Briefcase threaded follow-up** (only armed AA route; drafted, not sent).
4. Decide **Ubuntu-26 pinning** before 2026-10-19 (275 workflows).
5. **Enable branch protection + required checks** (needs Pro or public repo per API).
6. **Close issue #3739** manually (repair verified).
7. Provide or authorize credentials the policy allows at $0: HF (Chartography), Vals key (Finance/Mystery), HLE terms acceptance.
8. Decide whether a second **Astra** attempt is justified.

---

## 10. Internal record inconsistencies (so the wrong number is never trusted)

| Field | Stale value | Current value |
|---|---|---|
| `TERMINAL_CLOSURE_MANIFEST_V1.ownership_summary.verified_owned_families` | 5 | **7** (gate, `opus55_acceptance_summary`) |
| `…acceptance_calibration` | 2/19 | **7/19** |
| Plan docs "donor V2 10/10" | 10 | **12** requirements listed in the invalidation file |
| Plan memory "TB-Science 0/14 slots" | 14 | **20 consumed / 0 success** (pointer 2026-10-11) |
| TB4 attainability | 180<220 IMPOSSIBLE (2026-10-02) | **219 ≤ 220, slack 1** (2026-10-08 recompile; execution still unauthorized) |
| `ONE_SHOT_FRONTIER_EXECUTION_PLAN_20261014.md` | contains a literal `[truncated 9113 chars]` gap between Step 2 and §6 | section missing from the file |
| `scheduling_lock` text | "CURRENT_13_OPEN_ACCEPTANCE_OBLIGATIONS" | 13 obligations / 12 families (both correct: AA-Briefcase is shared) |

---

## 11. Forecast (repo's own, deflated per §6 adversarial review of the one-shot plan)

P(T ≤14 d) ≈ 0.005–0.01 · P(T ≤45 d) ≈ 0.02–0.05 · P(T ≤120 d) ≈ 0.08–0.15 · E[time | eventual success] ≈ 60–120 days.
Binding terms in order: (1) TB4 execution physics; (2) owner-reply latency on 5 external channels (AA 3 sends/0 replies; Cursor closed by policy; Mercor/Cognition pending; HLE/Vals credentials absent); (3) TB-Science serial slot consumption with 0/20; (4) remaining real capability bars (composition 8/12 interfaces, TB-Science kernel, OSWorld grounding). Joint sums in the plans are upper bounds (shared verifier capacity + Actions minutes).

---

## 12. One-page causal map

```
USER: billing ─┐                     USER: runner ─┐
               ▼                                   ▼
   hosted Actions alive            self-hosted regression runs
               │                                   │
               ├──► independent reverification     ├──► Professional 24/24 PROMOTED
               │    on any lane                    └──► Assurance UVCK V2 PROMOTED
               │
               └──► Actions share of TB4 compute ──┐
Codespaces 7.5h/mo ────────────────────────────────┼──► ≥55 wall-hr 16-core @ ≥99.5% ──► TB4 (p≈0.10 agent-side)
CircleCI / Buildkite (unverified) ─────────────────┘

OWNER REPLIES: AA (user must send) ─► AA-Briefcase + Artifact + Vision-nonchart
               Mercor/Cognition ──► FrontierCode     Cursor: CLOSED by owner policy ─► CursorBench needs policy change
               AA GDPval route ───► GDPval            Vals key ─► Finance Agent v2, Finance Index, MysteryMechanism
CREDENTIALS:   HF ─► Chartography   HLE terms ─► HLE   pinned bytes ─► OSWorld

CAPABILITY-REAL: TB-Science zero-model kernel (0/20) · Composition 8/12 interfaces · OSWorld grounding (#4340/#4343)

ALL 12 FAMILIES ──► 8 META ──► freeze routes ──► donor V2 (12 reqs) ──► clean-room replay ──► reducer TRUE
(serial by rule: D-finality may not run in parallel)
```

**Bottom line:** nothing currently open is a proof the agent can finish alone on unchanged information. Every one of the 20 atoms, 8 meta items and 12 donor requirements is gated by (a) an external party's reply or credential, (b) compute the $0 policy cannot buy, (c) a real capability that has not yet been built (TB-Science, composition interfaces, OSWorld grounding), or (d) a carrier the user controls (billing, runner, protection). The two largest immediately recoverable items — both 24/24 promotions — are blocked solely by E1/E2.
