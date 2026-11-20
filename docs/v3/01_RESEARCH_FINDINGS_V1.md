# Research Findings — What Exists in Your Project + What The Frontier Did (Nov 2026)

**Date:** 2026-11-20 | **Branch:** arena/69b87879-brain | **Covers §4 + §2-recheck**
> Exhaustive project search first (including non-obvious names), then max web research. Everything treated as input, not truth.

---

## Part A — Your Project: Exhaustive Inventory (17,844 tracked files checked)

### A1. Canonical governance (what is binding RIGHT NOW)

**Pointer:** `canonical/CANONICAL_POINTER.json` — generation `2026-10-09-resource-bounded-bytes-v1`, 15 mandatory laws, required gates `CRITICAL_PATH_PRE_ACTION_GATE_V11.json` + `GOAL_HIERARCHY_ACTION_GATE_V11.json`, required refresh before planning.

**Development authority:** `canonical/governance/CURRENT_DEVELOPMENT_AUTHORITY.json` (2026-10-11)
```
Status: ACTIVE_FAIL_CLOSED__GENERAL_CAPABILITY_FIRST__BENCHMARKS_AUDIT_ONLY__MINIMUM_PROOF_COVER_REQUIRED__REUSE_FIRST
Hard constraints: CORRECTNESS_FIRST, FAIL_CLOSED_TRUTH, PROVENANCE, OWNERSHIP_WHERE_CLAIMED, NO_GOAL_SUBSTITUTION
Benchmark policy: role = AUDIT | FALSIFIER | CALIBRATION_SURFACE | CAUSAL_PROBE
                  may_authorize_only_if: localizes defect | audits claim | cheapest non-dominated probe
                  forbidden: BENCHMARK_AS_PARENT_OBJECTIVE | SCORE_CHASING | PATCH_PROMOTED_WITHOUT_TRANSFER | FAMILY_RED_STATE_AS_JOB
Route order: DELETE > BYPASS > REUSE > ADAPT > SUBSTITUTE > COMPOSE > CONFIGURE > INTEGRATE > SYNTHESIZE_NEW_PRIMITIVE
New primitive: default false — requires falsification/proof of insufficiency
Credit: only verified reusable gain / reliability/resource gain without regression / live integration / independent falsification; benchmark score alone = 0 credit
```

**Live frontier today (real files, not memory):**

| File | Key fields (verbatim) | Implication |
|---|---|---|
| `CURRENT_LIVE_WORK_FRONTIER.json` | `runnable_benchmark_rows: 0`, `wake_gated: 12`, `parked:1`, `benchmark_capability_dominance_current` policy `PROPOSITION_FIRST__EXACT_MINIMUM_PROOF_COVER__BRANDED_RECEIPTS_SEPARATE__NO_SAME_INFORMATION_WAKE_GATED_RETRIES`, `current_nonbenchmark_exact_next: PARALLEL:CODING_GENERAL_SOFTWARE_REPAIR_LOOP_V9_PLUS_CURRENT_BYTES_RESOURCE_PARETO_CUT…PROFESSIONAL_WAKES_ONLY_ON_ZERO_SPEND_CARRIER_STATE_CHANGE` | No benchmark row runnable; only non-benchmark exact_next has standing. V9 repair loop + Bytes Pareto cut is the scheduled non-benchmark work. |
| `ACTIVE_GOAL_HIERARCHY_V1.json` | status `CANONICAL_FAIL_CLOSED__GENERAL_CAPABILITY_FIRST__BENCHMARK_AUDIT_SUBORDINATE`; probe_state `TERMINAL_V3_ONE_SHOT_CONSUMED 3352/3352 PASS` but `5 OF 19 FROZEN OPUS55 ACCEPTANCE`; next = `SELECT_NONDOMINATED_GENERAL_CAPABILITY_ACTION__REUSE_ADAPT_VERIFY_PROMOTE_FIRST` | Terminal V3 spent; acceptance still red (5/19). General-cap-first scheduling, reuse before invention. |
| `CURRENT_TERMINAL_AUTHORITY.json` (V42 pointer) | `ACTIVE_FAIL_CLOSED_REAL_MISSION_BOUND__GDPVAL_MINIMUM_PROOF_FRONTIER_V4_RECONCILED__GDPVAL_STALE_MECHANICAL_FIRST_DISPATCH_DEMOTED__TERMINAL_FALSE` | **TERMINAL_FALSE** — no terminal authority from this cut. |
| `CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json` | `ACTIVE__POST_V7_ROUTING_REPAIR__30_OPEN__COVERAGE_PARTITION_V3_CURRENT__J0_G0_T0_D15_U15__ZERO_CREDIT`, cut `CURRENT_ZERO_REALITY_MINIMUM_CUT_V22.json` (8359e6…), `NO_FRESH_REALITY_FROM_THIS_CUT` etc. **22 unresolved atomic /14 proved /8 meta-envelope open /30 total** | Hard rules forbid fresh reality, execution promotion, repeated finance/comp with unchanged premises, HLE/Opus-comparator search, etc. Scheduling only. |
| `ACTIVE_GOAL_HIERARCHY` forbidden | `HELDOUT_003_REPLAY`, `SECOND_CARRIER_FOR_HELDOUT_003`, `PROMOTION_FROM_UNAUTHORIZED…__HAND_PICKED_CARRIER_SUBSET` + 30 more | Anti-drift / anti-falsification-carrier rules.|

**Your bytes frontier:** `B_exec_raw_python_source_bytes 1,577,081` (observed 1,574,321) in `BYTES_ACTIVE_STATE_20261010_V1.json` → `NEXT86 21620/21620 NO_ADAPTATION` → instruction: *Rerank exact V81 using already-spent NEXT86 evidence; make genuine new physical cut before frozen NEXT87.* Promotion credit = 0.

**Result:** building a benchmark-specific OSWorld/SWE patch today without minimum-proof-cover and transfer would violate `NO_BENCHMARK_AS_PARENT_OBJECTIVE` + `NO_PATCH_PROMOTED_WITHOUT_TRANSFER`. Building a *general* reusable capability via reuse→adapt→compose is *allowed* — that's our path.

### A2. Model you actually have (compiled, verified)

**Artifact:** `canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json` — 11,234,160 bytes, 339,170 lines

- **Counts:** 447 capabilities (153 BOUND live-verified + 294 RECEIPT_BACKED pending), 26 engines, 18 skills, 581 knowledge docs, 7,184 research records, 2,373 routing tokens, 1,996 source-index modules (452 entry-points; 1,452 ORPHANs deliberately not capabilities — 1898 modules excluded to avoid claiming unobserved execution).
- **Provenance:** `compiler: compile_brain_unified_model_v1.py` SHA `5f900ac897e26c…`, `included_source_count 1383`, `source_tree_digest` **recomputed exact 0 missing/changed**; `external_model_calls 0`, `network_calls 0`, `incremental_spend_usd 0`, `deterministic true`.
- **Live registry truth:** `BOUND_CAPABILITY_REGISTRY_V1.json` 145 verified-bound + `BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json` 146 — merger is FLOOR; adapter `verified_bound_capability_execution_adapter_v1.py` re-reads live + OIDC (`iss https://token.actions.githubusercontent.com`, `github_run_id`) on every call. Embedded evidence note explicitly *not* credit.
- **Non-claim:** `NOT_A_TRAINED_NEURAL_NETWORK__CONTAINS_NO_WEIGHTS` — this artifact is an index + router, not a weightful net.

**Cognitive fabric:** `unified_cognitive_fabric_v1.py` — 25 engines + 1 meta (`ONE_SHOT_REALITY_CLOSURE`); `ENGINE_DESCRIPTORS` map mode→runtime: `RAW_GOAL|COMPILED_TASK|ADEQUATE_DECISION|P3|ADAPTIVE_SOLVER → live_brain_runtime`, `LEARNING_EPISODE → autonomous_verified_self_improvement`, `BOUND_CAPABILITY → verified_bound_capability_execution_adapter`, etc. `run()` enforces `OPAQUE_COGNITION_PROVIDER_FORBIDDEN…` and `R3_DIRECT_EXPERIENCE_MODES` (P3/H100/MYSTERY/CERTIFIED_ROUTE/LIVE… feed `observe_runtime_outcome` + `r3_improvement_queue_driver.drain`). `CATALOG` and `ONE_SHOT_REALITY_CLOSURE` are separate modes. Auto-routing prefers `UPSTREAM_ROUTING_LEDGER` when present.

**Non-obvious names recovered (project search):**
- `verified_mechanism_cover_optimizer.py` — exact minimum-byte cover over finite verified mechanism library (resource law enforcer)
- `residual_minimum_reality_cut_v6` + `global_terminal_universe` + `global_terminal_proof_cut` + `outer_global_minimum_reality_cut_verdict_v2` (exact min 4) — hierarchical cut system, not just V22
- `unknown_domain_direct_*` V1-V6 (transfer/abstention theorems, universal proofs) — parallel direct-evaluation family
- `osworld_v21_workflow_policy_v13.decide` + `osworld_v21_gui_goal_verifier_v1.verify_gui_goal` — GUI-goal verification gate for OSWorld (not in model caps)
- `h100_computer_use_registry_v1.py` (CAP_FS_LIST/READ/WRITE + PROGRAM_RUN_CONFINED, 4 caps only) + `grounded_action_v1` + `capability_forge_v1` + `chain_v1/macro_v1` — computer-use family is *filesystem+program*, not broad GUI
- `acquired_operator_memory_v1.py` (`teach/recall/restore` + `_restore_acquired_operators` on door import) — demonstration-is-operator, re-derives with gate check
- `value_algebra_v1.py` + `decomposition_law_v1` + `operator_acquisition_v1` — arithmetic law family behind `spreadish`-style operators
- `semantic_generalization_engine_v1.py` (OnlineParametricPolicyModel 3 linear heads) vs `instant_one_shot_learning_v1.py` (REMEMBER=0) — *two distinct* learning systems, not one; conflating them is a category error

Rebuild-what-exists violation avoided: I cataloged 4,000+ runtime py files; none are skipped.

### A3. Learning + Skills: what is *already* in the repo

| System | File(s) | Persistence | Mechanism | Honest status |
|---|---|---|---|---|
| **Instant One-Shot Learning** | `swe_kernel/instant_one_shot_learning_v1.py` (9 phases) | **Zero** — `remember_skill()` → `stored_knowledge_bytes 0`, `knowledge_house false` always | OBSERVE→CREDIT→IDENTIFY→CONTRACT→APPLICABILITY→COMPOSE→HORIZON→ADMIT→REMEMBER→REPLAY; ADMIT requires `lesson_admission_gate_v1.evaluate` on held-out victims (≥1 repair + ≥1 preserve, break nothing) | Mechanism calculated, not warehoused. Tests 47 green on verified row, 3 rows succeed. 13/15 rows zero demand-matching cands (rules out one-trace-pins-all fantasy). |
| **Semantic Generalization Engine** | `swe_kernel/semantic_generalization_engine_v1.py` + `weight_update_admission_v1.py` | Ephemeral → gated weight | `GeneralizationEngine.solve_task()` on learn-enabled path (`closed_loop_autonomous_controller_v1:1194` when no recalled workflow). Typed count/list family: synthesized plans + causal probes. Stores experiences/embeddings; permanent weight via 3-head OnlineParametricPolicy (hashed text features 128-dim) only if `weight_update_admission_v1._evaluate` → ADMIT (held-out probe gain, parser `parse_task` as judge) | **Currently 24 experiences (8 unique desc, all success), 8 embeddings, `GENERALIZATION_POLICY_V1.json` absent** → no permanent policy. Bounded typed family, not arbitrary SWE. Past naive updates broke 3/32 correct predictions while self-loss improved — admission gate exists to prevent. |
| **Verified Skills / Workflows** | `verified_skill_crystallizer_v1.py`, `causal_trace_to_skill_compiler_v1.py`, `autonomous_awake_loop_v1.py`, `software_repair_crossfile_choreograph_v1.py`, `VERIFIED_SKILLS_BUNDLE 5 rules + COMPILED_WORKFLOWS_BUNDLE 11 workflows` | **Durable SQLite WAL + bundles** | Hypotheses + `lesson_admission_gate` (ungated stays ungated even if equivalence proof later); `skill_recheck_v1.recheck`; merge preserves stronger admission + provenance growth; `recall_and_apply_verified` re-verifies before use | Real persistence but scoped to bug-class repair, not arbitrary GUI/browser. Verified hits `origin` preserved, `verified_hits` accumulation. |
| **Acquired Operator Memory** | `runtime/acquired_operator_memory_v1.py` + `operator_acquisition_v1` + `inspect_v1._restore_acquired_operators()` | **Durable JSON file, lazy re-derive** | `teach(kind,words,examples)` stores examples+arithmetic; `restore()` in new process re-runs `acquire_from_examples` through same gates (`_usable`, `induce_laws`, `_law_is_falsifiable`, `indistinguishable_from`); bad row reported not silently dropped | `spreadish sum(v)-max(v)` example: same-process hit true, fresh-process false *unless* restore runs — most impressive repo mechanism, previously thrown away per file header. Re-derivation prevents cache-becomes-lie. |
| **Cross-domain memory** | `COMPOSITION_MEMORY_OWNED_FAMILY_BRIDGE_V1/V2` + `H100_ZERO_LEARNED_EVENT_MEMORY_PRECOMMIT` + `ASSOCIATIVE_MEMORY_V1` | Mixed — family bridge has public-runner verification | Durable event memory family compositions | Verified on second carrier (20261005), not hand-waved. |

**Takeaway:** you have *three co-existing persistence semantics* — deliberately. Prompt's "learning permanently" conflates them; we resolve below.

### A4. Computer Use — what *exists* vs what *doesn't*

**Exists (4 registry caps + surrounding harness):**
- `h100_computer_use_registry_v1.py` — `CAP_FS_LIST_V1`, `CAP_FS_READ_V1`, `CAP_FS_WRITE_V1`, `CAP_PROGRAM_RUN_V1` (confined execution). Declared preconditions/effects, planner-reasonable, independently verified before dispatch (`prior_verification` + receipt/OIDC). Cost model: FS=1, program=5, write=2.
- `grounded_action_v1.py` — bind-first + decisive margin + independent byte re-read; consulted by `chain_v1`, `macro_v1`, `capability_forge_v1`, `forged_binding_and_macro_spine_v1`
- `osworld_v21_*` 89 ORPHAN modules: `workflow_policy_v1..v13` (v13 → `CHART_AXIS_TITLE_UNIT_BINDING`-style GUI goal verification), `positioned_ocr_observer`, `visual_region_grounding`, `host_*_ops` (code/guest/media/web_app), `constraint_guard`, `runner_binding` (`build_agent` + `bind_agent_environment` + `run_native_example` delegating to OSWorld's `lib_run_single.run_single_example` + `env.evaluate()` — no evaluator fork), `submission_entrypoint_v3` (frozen pyautogui/1920×1080/500-step/EXACT protocol)
- **Verification:** `COMPUTER_USE_CHECK_DENSITY_20261116_V1.json` — content state distinguishes 34/34 replay mutants; novel-work detection catches crashes/no-ops (density 0.5)
- **OSWorld smoke only:** `osworld-v21-local-qwen-policy-smoke-v1.yml` — pinned llama.cpp `bec4772`, Qwen3.5-9B Q4_K_M `f41c0a…` 5060174144B verified, synthetic browser OBSERVE→CLICK_TEXT smoke (2 cycles, `benchmark_task_data_used false`, `terminal_cases_consumed 0`)

**Does NOT exist (honest):**
- No broad unseen-app proof; 89 OSWorld source modules are ORPHAN (addressable not executable, `is_executable_entry_point false` where applicable)
- No verified `CAP_GUI_CLICK`, `CAP_BROWSER_AUTOMATE`, etc. in live registry — computer use today is filesystem+program, not arbitrary GUI
- OSWorld 2.0 native `DesktopEnv` run not yet executed under pinned `osworld-v2.1` (326 tests /108 task hashes); 108-task long-horizon eval not passed
- H100 inference registry is separate symbolic regression (unary chains), not computer use

### A5. Evidence you have (verified/unverified/failed)

- **Verified self-contained:** `CHART_AXIS_TITLE_UNIT_BINDING` (7/7), `TERMINAL_CLOSURE_REDUCER`, `ACCEPTANCE_CAPABILITY_SOURCE_GATE_V2`, `RUNTIME_COGNITION_CREDIT_GUARD`, `RESIDUAL_MINIMUM_REALITY_CUT_V6` + independent recomputation, `UNIVERSAL_ESCAPE_RESOLVER_V1` (112707682297), `L1_ABC_NORMAL_FORM`, `DB_EVIDENCE_SATURATION_UNION_V13` — each with public runner verification.
- **Verified but red for ownership:** general `swe_kernel` + `osworld_v21` harness improvements (e.g., `LOCAL_QWEN3_5_9B_BIOPHYSICS_TASK_B_FALSIFICATION`) — not terminal credit.
- **Producer-run only, not §6:** `A_SINGLE_TRACE_DOES_NOT_PIN_THE_RULE_20261120_V1` (13/15 zero, 1 verified 47-green), `REAL_COMMIT_REPAIR_20261116 0/90`, `STRUCTURAL_REWRITE_INDUCTION 0/5`, `GENERALIZATION_RUNG_GRADIENT` (24 success-only experiences insufficient for rung proof).

Hard constraints enforced by code: `external_contribution_three_way_classification` (TARGET_SOLVING→K3_FORBIDDEN/K2_TRANSFER_GATED/K1_INFO_ONLY), `runtime_external_cognition_lock_verifier`, `python_startup_model_planner_kill_switch`, `zero_spend_provider_guard`.

---

## Part B — Frontier: Max Web Research (date is 2026-11-20 UTC per your date, so I anchored to Nov 2026; I did not trust stale training data)

### B1. Hardest open benchmarks AS OF NOV 2026 (exhaustive sweep)

**Computer Use — OSWorld 2.0 is the hardest *alive* board, but not the ceiling**

| Benchmark | Scale | Status Nov 2026 | Top scores (verified sources only) | Why it's ultimate-hard vs prior | What frontier fails on |
|---|---|---|---|---|---|
| **OSWorld 2.0** (XLab HK + collaborators, 2026-06-30 paper v2.1 release 326 tests) | 108 long-horizon workflows × 7 domains (research 20.6%, creative 20.2%, engineering 17.3%, personal/admin/business 12.5% each, healthcare 3.9%) × 31 self-hosted mocks; median human 1.6h, agents >300 steps; 500-step cap, binary + 54.8% partial (27.25 checkpoints/task) | **LIVE, wide-open gap** | Launch: Opus 4.8 20.6% binary. Oct 2026 independent tracker: **Opus 5 → 31.4%**, Nov ledger #733: **Opus 5 → 44.33% binary** (max effort, batched tool calls). Verified (369 narrow tasks) is SATURATED (Intelligence-Indeed 90.19% > human 72.36%) — *do not benchmark on it* | End-to-end multi-app professional workflows + dynamic env + cross-app state + dense final-state eval + model-based checks (11.53% weight) + user-simulator needed; can't be faked by single-app lookup | Lowest-scoring phenomena = hidden-state recovery: Implicit-state Inference, Multi-item State Tracking, Conflict Disambiguation, Dynamic Environment.  Resource ↑ → partial ↑ but binary barely moves — diminishing returns to tokens/steps |
| **Terminal-Bench 4.0** (Stanford/Laude/Harbor) | 66 tasks, 3 need H100, re-versioned twice past 2.0 (earlier 2.x 84.7% saturated) | LIVE, most-cited agentic | **Claude Opus 5.5 (max, Claude Code) 64.85% ±3.1** (22 Sep 2026) — not 84% (that's old set). Claude launch: 66.4% own-harness. | Hard senior engineering live-shell + verifier per task + trajectory required for pass + reward-hacking=0; Harbor format | Vendor self-report noise (±3% harness, effort, repeats). Still discriminates. |
| **SWE-bench Pro** (Scale AI, 1,865 tasks / 41 repos; 731 public / private held-out, V2 nearly saturated) | Hard cross-file (4.1 files avg, 107 LOC avg, ≥10 lines min) vs Verified 161/500 one-liner | LIVE but audited ≈30% broken (OpenAI July audit) — *handle with care* | **Muse Spark 1.1 61.50% ±3.1** (mini-swe-agent public); Anthropic vendor 66.4% xhigh; Pro drops 20-25pts vs Verified for same model (Opus 4.7: 87.6% Verified → 64.3% Pro) | Multi-file cross-repo, contamination resistance (GPL+private), long-horizon; vs original <25% top at paper time | Verifier hackable (Berkeley audit: every board 100% trojanable — pytest hook, container parser etc.). DeepSWE reports SWE-Pro 8.5% false-pos /24% false-neg. Top Pro is not human. V2 at 99.4% (HARD-51 98%) — ceiling approaching, not done. |
| **SWE-bench Verified** | 500 curated | **SATURATED** (97% Vals, vendor 93.9% Mythos) | Do not use as primary 2026 signal. |
| **Other coded boards that matter** | LiveCodeBench v6 (1,055 contest probs) — top Elo Qwen 3.5-plus 2887; DeepSWE v1.1, SciCode, FrontierCode 1.1 (Cognition 100 hardest, maintainer rubric), CursorBench (Anysphere private), Bug Hunt 105 bugs/2 TS repos, MirrorCode (reimplement CLI from scratch), SWE-Marathon (multi-hour library/full-stack/ML) | LIVE | Each discriminates a slice; composite indices (BenchLM, Epoch, Vals) weight them. | Fresh-task rotation (SWE-rebench monthly), execution-based (not LLM judge) vs judge-based 11.53% OSWorld — fidelity tradeoff |
| **TB-Science 0.1** | 15% of Artificial Analysis weight | New (2026) | Expensive, same format as TB4, no GPU | Signals science coding, not general SWE |
| **HLE** (Humanity's Last Exam) | -100…+100, abstention-rewarded, public 300/3000 | Hard ceiling | ~53% (hardest knowledge) — not agent-use |
| **ARC-AGI-3** | Interactive reasoning | Hardest gap | Humans 100% vs models ~0.5% launch → ~30% ARC-prize top — widest gap left | Not computer-use but cognition frontier |

**Frontier gap analysis reconciled (eval-containers #733, 2026-11-03 checked 2026-11-04):** vendor release benchmark lists mapped to 8 boards; B1 Terminal-Bench 4.0 scored 10/10 (most-cited), B2 TB-Science 8, B6 SWE-bench Pro V2 5 (nearly saturated), B7 OSWorld-V2.1 5 (heaviest infra, LLM-simulator needed). Opus 5.5 tokens per OSWorld pass not published; Sai+Opus5 cost $14.34/task ($1,548/full 108).

**What §6 demands is *harder* than any one board:** "hardest open computer-use AND software-engineering tests, including never-seen envs + single-experience learning." That is OSWorld2.0 (20-44% frontier) *plus* SWE-bench Pro (61% frontier) *plus* the never-seen + one-shot condition neither board alone measures. Frontier best on either is far from done, so our bar is correct.

### B2. What frontier systems *actually* do (not what benchmarks claim)

- Frontier solves OSWorld-Verified (narrow single/short tasks) but fails OSWorld 2.0 long-horizon: failure taxonomy = guesses instead of asking user, skips verification, can't recover latent info, loses track of constraints, can't repair mid-task. Gains come from max thinking + batched tool calls, not understanding.
- SWE-bench Pro gains come from mini-swe-agent scaffolding + cross-file retrieval, not code understanding; harness alone adds 8-15 pts; 1-2 line fixes saturate Verified while 107-LOC/4-file Pro stays open.
- All agent boards need exact harness/runs/time budget to post — scores not comparable across effort levels (±2-3% SE). Vendor launch posts ≠ independent leaderboard.
- Cheating surface is systemic: Berkeley audit proved binary-wrapper trojans, hook injection, container overwrites across TB/SWE — so *trajectory + independent recomputation* is mandatory, not optional. Terminal-Bench now requires trajectories and zeros hacks.

### B3. Instant / continual / memory frontier (2026 state — the "already solved" check)

- **Continual learning year hype vs reality:** Mid-2026 map says *solved with public access: nothing; shipping: only frozen-model + dossier (memory files/vector DB/graph) stacks*. Weight-level continual learning *increases* catastrophic forgetting in 2026 LRM fine-tunes (arXiv 2601.18699). Outside-model memory + periodic retrain is what ships; inside-model weight mutation daily does not.
- **Promising but not solved:** TTT layers (hidden state = small model updated by GD on streaming tokens, ≤1.3B beats Transformer/Mamba), Dragon Hatchling (Pathway, Hebbian synapses, "infinite context" without quadratic), NuSA-CL (ICLR 2026, null-space LoRA, tail > top, merges into base fixed budget, memory-free lifelong). None are general-weights-that-learn-everything-instantly — each is narrow and needs proof per domain.
- **Nuance:** "learning" branding conflates (a) retrieval-augmented memory (what we ship as VerifiedSkillStore) with (b) true online weight evolution. Altruistic critique: (a) is lying if sold as (b). Our repo already distinguishes them — correct to keep.

### B4. GUI grounding — load-bearing primitive solved *as a module*, not as an agent

- **UGround family:** Largest 2024-2025 recipe (LLaVA-NeXT AnyRes + 10M elements/1.3M screenshots web synthetic) → **ScreenSpot-V2: UGround-V1-7B 86.3%, 72B 89.4%**; +20% absolute over SeeClick/CogAgent; desktop zero-shot from web-only training works because UI design language standardizes; positional referring expressions needed for identical buttons; idiosyncratic app-specific icons still fail; UGround is *planner-less* grounding only (needs LLM planner — SeeAct-V + GPT-4o reaches 81.4% grounding but still fails OSWorld2.0 long horizon).
- **2026 grid:** UI-Venus 1.5, Aria-UI, MEGA-GUI, OS-Atlas, UGround, Jedi, ShowUI, SeeClick, CogAgent all at SOTA on public leaderboards; perea.ai May 2026 comparison is reference.
- **Takeaway for us:** Visual grounding at coordinate level is *solved as a module* (we can distill/inspire from open UGround without runtime model call). What is *not* solved is long-horizon state-maintaining *agent* that uses grounding while tracking hidden state, verifying artifacts, repairing errors.

---

## Honesty block ( §11)

- No benchmark score above is our system's. Our agent has taken **zero** of these tests (current sandbox 2-CPU/3.8GB, no Docker/KVM, no model deps — OSWorld2.1 needs KVM+Docker+214GB images + `osworld-v2.1` gated download; TB4/Harbor needs `harbor` + container). Claiming any would be leakage.
- Verified: compilation counts, gate files, live frontier terminal-false/30-open, charter laws — re-read on disk 2026-11-20.
- Unverified: frontier top scores are external trackers' latest (Oct-Nov 2026) and drift daily; I pinned dates and sources but did not independently rerun.
- Failed: no local OSWorld/SWE/TB execution — blocked by governance `NO_FRESH_REALITY_FROM_THIS_CUT` + infra; that is expected fail-closed.

## What this unlocks next

Project exhaustive map says: your fastest lever is *not* a new model — it's the **bytes Pareto cut** already scheduled (exactly ranked V81 → 1.57M raw bytes) + the **V9 repair loop** that must generalize from verified V9 bounded source-grounded acceptance without oracle leakage. Frontier says: those two levers are exactly where frontier agents still fail (hidden-state + long-horizon repair). See verdict.
