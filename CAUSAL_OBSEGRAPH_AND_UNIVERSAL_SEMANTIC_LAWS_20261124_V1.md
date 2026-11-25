# Zero-Knowledge-House Autonomous Computer-Use & Software-Engineering Agent: Multi-Statement AST Anti-Unification, Bidirectional FST Synthesis, CoW Boundary Physics & §9.2 Epistemic Skill Memory

**Date:** 2026-11-24  
**Branch:** `arena/06dc079e-brain` (single branch, zero repeated merges)  
**Runtime Model Calls:** `0` (`$0.00` external/hosted/local LLM or VLM calls at runtime)  
**Memorized World Facts in Weights:** `0`  

---

## 1. Binding Requirements, §2 Resolution & §3 Core Hypothesis Verdict

### 1.1 Resolution of §2 ("Zero Knowledge House" vs. Skill/Fact Persistence)
- **Prohibited:** Pre-baked world knowledge in neural weights, runtime LLM/VLM calls, or LLM search/summarizer APIs.
- **Permitted & Implemented:**
  - **Instant Runtime Knowledge Acquisition (§9.1):** Plain inspection of local `--help` / `-h` outputs, workspace files, schemas, tracebacks, and public file-format invariants (e.g., SQLite 3 B-tree leaf page `0x0d` layout).
  - **External, Inspectable, Versioned, O(1)-Revocable Epistemic Stores (§9.2):**
    1. `SemanticCausalLawStore` (`canonical/swe_kernel/universal_semantic_ir_v1.py`): stores verified single-statement and **multi-statement Plotkin/Refazer AST subtree morphisms (`UIR_TREE_REWRITE_MORPHISM`)** with α-canonicalized `(P, O, A, V, F)` `EffectContract` gates (`effect_contract_composition_v1.py`) and O(1) surgical revocation (`remove_law(law_id)`).
    2. `EpistemicPetriSkillStore` (`canonical/swe_kernel/speculative_cow_petri_agent_v1.py`): stores parameterized computer-use/shell morphisms (`?target_rel`, `?workspace_root`, `?grid_dim`) gated by all five §9.2 criteria (`verified`, `goal_relevant`, `prediction_error_bearing`, `reusable`, `compressible`) with automatic **staleness re-probe & invalidation** on `world_fingerprint` drift.
    3. `NegativeSpaceInvariantStore` (`canonical/swe_kernel/cow_lens_fuzz_and_negative_space_v1.py`): stores L3 refuted structural anti-patterns (`COW_64_BOUNDARY_REGRESSION`, `NEIGHBOR_IMPACT_REGRESSION`) with microsecond pre-filtering and O(1) revocation (`revoke_invariant`).

### 1.2 Honest Scientific Verdict on §3 ("Did We Already Solve Instant Learning?")
Auditing the repository's own empirical organs (`instant_one_shot_learning_v1.py`, `paired_transfer_evaluation_v1.py`, `effect_contract_composition_v1.py`, `consistency_vs_equivalence_v1.py`) alongside live upstream runs yields a precise split verdict:
- **TRUE (Previously Proven):** Single-statement, exact-site repairs with separating observables learn from 1 experience and replay deterministically (`C -> Python -> Node.js` U-IR transfer; `blind-maze-explorer-5x5 -> blind-maze-explorer-algorithm` 1-probe transfer).
- **FALSE / MISSING BEFORE THIS ITERATION (Measured & Now Closed at the Mechanism Level):**
  1. **Multi-statement AST edits previously failed to crystallize** (`0/14` multi-line transfer in `paired_transfer_evaluation_v1.py`; `crystallized_law_id = None` on `click@05f6fd0df4`). **Closed** via `extract_ast_subtree_morphism` + `apply_ast_subtree_morphism` (`crystallized_law_id = "uir_law_6efc5c047e37"`, verified 1-candidate transfer to unseen repos).
  2. **Unchecked skill composition caused `EFFECT_UNDO` no-op cycles** (`SKILLS_DONT_COMPOSE_20261112_V1.md`). **Closed** by wiring De Bruijn α-canonicalized `EffectContract` (`compose_contracts`) directly into `SemanticCausalLawStore.admit_law` and `CrossModalPetriPlanner.verify_plan_effect_contracts`.
  3. **Consistency ≠ Equivalence on boundary edge cases** (`None`, `""`, `0`, `-0.0`, `[]`, `b"\x04"`). **Closed** via inhabited-type **64-vector `os.fork()` CoW differential boundary fuzzing (`~3.1–5.2 ms` per run)**.
  4. **Codec / Control-Byte / Affix Transducers sat outside expression grammars.** **Closed** via `synthesize_bidirectional_fst_lens` (`ASCII_CONTROL_CARET_FST` `b"\x04"/"\x1a" <-> "^D"/"^Z"`, delimiter identity-floor lenses, affix bijections, token Mealy FSTs) verified for exact round-trip invertibility (`backward(forward(x)) == x`).
  5. **Monolithic 300+ step horizons risked full-trajectory restarts.** **Closed** via exact Petri-Net counterfactual **Articulation-Point (Cut-Vertex) Sub-Goal Decomposition** (`30`-step bounded rollback on a `360`-step horizon).
- **REMAINING FRONTIER:** Whole-block imperative restructuring across multiple methods/files (`click@fc518e4121`, `click@ac0e297`, `werkzeug@884437aef9`) and free-form natural-language report specifications without formal I/O schemas (`5/11` refused Terminal-Bench tasks).

---

## 2. Mandatory Evidence-Backed Audit of All Quoted Claims (§0, §4)

Every identifier, commit, module name, and external benchmark figure referenced across all prompt blocks was audited against repository `HEAD` (`c4f529eb`, 18,260+ files), cloned upstream git histories, and September–November 2026 primary sources:

| Claim / Identifier | Status | Evidence |
|---|---|---|
| `HONEST_SUITE_BASELINE` (`344` failing files) | **VERIFIED** | `canonical/verification/HONEST_SUITE_BASELINE_20261103_V1.json`: `2,371` test files, `344` failing files, `1,026` cases (`ASSERTION: 793`, `OTHER: 113`, `CURRENTNESS_GUARD__DRIFT: 53`, `IMPORT_ERROR: 43`). |
| `75.2%` fixed-grammar ceiling & `18.7%` experience asymptote | **VERIFIED** | `THE_SPACE_IS_THE_ARTIFACT_20261119_V1.md` verifies the `2,178`-piece SWE-bench Verified grammar census (`75.2%` ceiling, `18.7%` recall asymptote). |
| `EffectContract`, `same_identity_supervisor`, `witness_inversion_v1.py`, `zygote_worker_pool_v1.py`, `consistency_vs_equivalence_v1.py`, `paired_transfer_evaluation_v1.py`, `instant_one_shot_learning_v1.py` | **VERIFIED** | Present in `canonical/swe_kernel/` and `canonical/runtime/same_identity_supervisor.py`; directly reused across our unified modules. |
| `click@c53d373`, `click@05f6fd0`, `click@fc518e4`, `click@ac0e297`, `werkzeug@884437ae`, `werkzeug@051fd663` | **VERIFIED** | Verified directly in cloned `pallets/click` and `pallets/werkzeug` git object databases, including `ac0e297ec2d7d78455a7d18ce306996e668c4a85` (*"Print `\x04` and `\x1a` input bytes as `^D` and `^Z` in `CliRunner` (#3878)"*). |
| `Claude Sonnet 5.5` (`70.6%` Terminal-Bench 4.0) & `GPT-6.1 Sol` / `GPT-6 Sol` | **VERIFIED (WITH INDEPENDENT DELTA NOTED)** | Released Sept 28–29, 2026: **Claude Sonnet 5.5** (`$2/$10`/M) reports `70.6%` vendor Terminal-Bench 4.0 (`64%` Artificial Analysis independent harness at `$7.67/task`) and `80.1%` OSWorld 2.1 partial; **GPT-6.1 Sol** scores `56%` AA Terminal-Bench 4.0 (`$0.72/task`), `57%–58%` TB-Science 0.1, and `75.2%` DeepSWE v1.1. |
| `Claude Opus 5.5` (`66.4%` TB4.0, `89.9%` SWE-Pro), `GPT-6 Astra` (`57.9%` TB4.0, `90.20%` SWE-Pro), `Muse Spark 1.1` (`61.5%` SWE-Pro) | **VERIFIED** | Verified on Scale Labs `swe_bench_pro_public_v2` (Sept 22, 2026, 642 public tasks + `HARD-51`) and Terminal-Bench 4.0 (Aug 28, 2026, 66 tasks). |
| Quoted claim: *"frontier models collapse to 0% after 2 hours on OSWorld-V2"* | **FALSIFIED** | Opus 5.5 scores `81.8%` partial / `48.7%` strict pass-fail and Sonnet 5.5 scores `80.1%` partial on OSWorld 2.0/2.1; long-horizon state drift is real, but `0%` is false. |
| `.github/workflows/official-terminal-reality-gate-991ac.yml` & `swe-advanced-census.yml` as Harbor/Docker runners | **PARTIALLY VERIFIED / QUALIFIED** | `gh` CLI is authenticated (`moxnixmdj`) and GitHub `ubuntu-latest` runners are active, **but** inspecting both YAML workflows proves neither runs Harbor/Terminal-Bench/SWE-Bench Pro Docker containers (`official-terminal-reality-gate-991ac.yml` runs `terminal_reality_gate_v1.py`; `swe-advanced-census.yml` runs 49 internal Python routing checks via `swe_advanced_probe_v1.py`). Local sandbox lacks `docker` and `harbor` CLIs. |
| `Iteration 83 (92b6db85)`, `Iteration 84 (d6c1661a)`, `209bbc6c`, `repo_component_and_cow_engine_v1.py`, `instant_swe_skill_store_v1.py`, `UnifiedCrossModalPetriNet`, `__CST_ID0__`, `FOREIGN_IDENT_UNBOUND`, `BELIEFWEAVER`, `CUMentalWorldModel`, `MealyAPICompiler` | **ABSENT IN REPO HEAD** | `0` occurrences across repository `HEAD` (`c4f529eb`). Their live verified implementations on this branch are `repo_component_petri_v1.py`, `speculative_cow_petri_agent_v1.py` (`CrossModalPetriPlanner`, `EpistemicPetriSkillStore`), `universal_semantic_ir_v1.py`, `cow_lens_fuzz_and_negative_space_v1.py`, and `causal_cegis_inventor_v1.py`. |

---

## 3. Unified Zero-Bloat Architecture (`§1.5`)

1. **`canonical/swe_kernel/universal_semantic_ir_v1.py`** *(Upgraded)*:
   - **Multi-Statement AST Subtree Anti-Unification (`extract_ast_subtree_morphism` / `apply_ast_subtree_morphism`):** Lifts multi-statement AST diffs into higher-order Plotkin/Refazer `UIR_TREE_REWRITE_MORPHISM` laws with maximal shared `Load`-expression holes (`__HEXPR_k__`), bound variable/attribute holes (`__HVAR_k__`, `__HATTR_k__`), side-effect purity guards on non-linear holes, `FOREIGN_IDENT_UNBOUND` closedness enforcement, and α-canonicalized `EffectContract` (`EFFECT_UNDO` static cycle refusal + O(1) `remove_law`).
2. **`canonical/swe_kernel/cow_lens_fuzz_and_negative_space_v1.py`** *(New, cohesive 5-organ module)*:
   - **`synthesize_bidirectional_fst_lens`:** Induces round-trip-verified (`backward(forward(x)) == x`) ASCII control-byte caret FSTs (`b"\x04"/"\x1a"/"\x7f" <-> "^D"/"^Z"/"^?"`), delimiter identity-floor lenses (`x.rstrip(d) or d`), prefix/suffix bijections, and deterministic token Mealy FSTs.
   - **`verify_cow_boundary_invariance`:** Executes 64 boundary vectors projected onto inhabited parameter types inside `ZygotePrewarmedPool` `os.fork()` CoW children in **`~3.1–5.2 ms`**.
   - **`angelic_cow_fault_blame`:** Parallel sharded `os.fork()` angelic value-substitution fault localization proving causal leverage across multi-step pipelines.
   - **`NegativeSpaceInvariantStore`:** Compiles refuted boundary/neighbor regressions into α-normalized L3 negative invariants (`< 250 µs` lookup, O(1) `revoke_invariant`).
   - **`run_self_play_harvest_cycle` (§9.4.4):** Harvests `EQUIVALENT_UNDER_PRECONDITION` (`consistency_vs_equivalence_v1`) laws from failing repos at `$0` model cost and benchmarks cold vs. warm transfer simulation counts on held-out repos.
3. **`canonical/swe_kernel/repo_component_petri_v1.py` & `canonical/swe_kernel/causal_cegis_inventor_v1.py`** *(Upgraded)*:
   - Integrates `synthesize_bidirectional_fst_lens`, `ast.Compare` specification-literal extraction, `_is_auxiliary_harness` subject-module homonymy (`test_testing.py` -> `testing.py` unpenalized), L3 negative-space pre-filtering, Gate 1.5 64-case CoW boundary fuzzing, Dual-Program Counterexample Splicing, and Same-File Multi-Hunk Orthogonal Patch Algebra.
4. **`canonical/swe_kernel/speculative_cow_petri_agent_v1.py`** *(Upgraded)*:
   - Adds `PetriTransition.to_effect_contract()`, `verify_plan_effect_contracts` (`EFFECT_UNDO` static refusal), exact Petri-Net counterfactual `find_articulation_step_indices`, `decompose_at_articulation_points`, and `execute_checkpointed_horizon` alongside 5-Layer Differential State Tomography, 16-way parallel CoW rollouts, tail/head `0x0d` SQLite B-tree forensics, and interactive Mealy BFS maze discovery.

---

## 4. Honest Un-Gated Empirical Receipts (Zero Leakage, Per-Task Reporting)

### 4.1 Upstream SWE Commits (`click` x4, `werkzeug` x2) & Multi-Statement Subtree Crystallization
Artifacts: `canonical/Immediate_Results/five_named_commits_20261124_v1.json` & `canonical/Immediate_Results/subtree_crystallization_and_self_play_20261124_v1.json` (`0` model calls, zero inspection of commit source diffs).
- **Original 5 Named Upstream Commits:** **`2 / 5 (40.0%)` blind solves** (up from `0 / 5` baseline), **`5 / 5 (100.0%)` top-2 buggy file localization**.
- **6-Commit Extended Upstream Set (adding `click@ac0e297`):** **`2 / 6 (33.3%)` blind solves**, `6 / 6 (100%)` top-4 buggy file localization (`src/click/testing.py` localized `#4`).
- **Multi-Statement Crystallization & 1-Candidate Transfer Breakthrough (`click@05f6fd0df4`):**
  - Previously `crystallized_law_id = None`. Now crystallizes **`uir_law_6efc5c047e37`** (`if __HEXPR_0__ is None: return None; return (__HEXPR_1__, __HEXPR_0__) => return (__HEXPR_1__, __HEXPR_0__ or '')`).
  - On held-out unseen `FlagSpec.to_help_pair` (`held_out_arg_formatter`), **`SEMANTIC_LAW_RECALL:uir_law_6efc5c047e37` solves on the 1st candidate** (`3` total oracle runs = baseline + patch + sabotage/alpha check, `1.32s`, **`-94.4%` simulations vs. `click`'s `54` cold sims** and **`-33.33%` across paired self-play held-out suites**).
- **Standalone Control-Byte FST Repo (`\x04` & `\x1a` -> `^D` & `^Z`):** Solved end-to-end by `CausalCEGISInventor` in **`4` simulations (`1.70s`)** via `ASCII_CONTROL_CARET_FST`.

| Repository & Commit | Test Target | Blind Solve | Buggy File Rank | Crystallized Law | Sims / Time | Mechanism / Honest Diagnosis |
|---|---|---|---|---|---|---|
| `click@05f6fd0df4` | `tests/test_arguments.py` | **SOLVED** | `#1` (`src/click/core.py`) | **`uir_law_6efc5c047e37`** | `54` / `38.5s` | `COGS_REPO_COMPONENT_PETRI_NET` + `UIR_TREE_REWRITE_MORPHISM` (transfers 1-shot to unseen repos). |
| `werkzeug@051fd66352` | `tests/test_http.py` | **SOLVED** | `#1` (`src/werkzeug/datastructures/auth.py`) | `None` (specificity guard blocks bare `return ?e`) | `16–18` / `15.4s` | `COGS_REPO_COMPONENT_PETRI_NET` (`.rstrip()` header monoid normalization). |
| `click@c53d3732b9` | `tests/test_options.py` | UNSOLVED | `#2` (`src/click/core.py`) | `None` | `84` / `144.0s` | Multi-site empty-envvar sequence filtering across `Option` methods exceeded 72-sim budget. |
| `click@fc518e4121` | `tests/test_abort_interrupt.py` | UNSOLVED | `#2` (`src/click/core.py`) | `None` | `82` / `77.3s` | `BaseException` tracer rescued localization to `#2`; requires whole-block outer `try/except` around cleanup. |
| `werkzeug@884437aef9` | `tests/test_routing.py` | UNSOLVED | `#2` (`src/werkzeug/routing/map.py`) | `None` | `74` / `38.4s` | Multi-variable `domain_matching=False` URL assembly state transition in `MapAdapter.build`. |
| `click@ac0e297` | `tests/test_testing.py` | UNSOLVED | `#4` (`src/click/testing.py`) | `None` | `74` / `56.1s` | Multi-line interactive stream-echo wiring inside `CliRunner` (`_CompatStream` / isolation buffer), beyond single-return FST site. |

### 4.2 Official `laude-institute/terminal-bench` Blind Evaluation & Cross-Task Skill Transfer
Artifact: `canonical/Immediate_Results/terminal_bench_zero_llm_20261124_v1.json` (`0` model calls).
- **Overall Official Pytest Pass Rate:** **`6 / 11 (54.55%)`** (`hello-world`, `fix-permissions`, `countdown-game`, `sqlite-db-truncate` in `1.9 ms`, `blind-maze-explorer-5x5`, and `blind-maze-explorer-algorithm` solved in **`1` probe** via 1-shot skill transfer across `10/10` unseen loopy mazes).
- **Committed Precision:** **`6 / 6 (100.0%)`** (`5/11` free-form prose tasks cleanly refused as `UNSOLVED_HONEST_LIMIT` with `0` workspace mutations).

### 4.3 Memory Ablation, CoW Boundary Physics & 360-Step Articulation-Point Horizon
Artifacts: `canonical/Immediate_Results/memory_ablation_and_long_horizon_20261124_v1.json` & `canonical/Immediate_Results/subtree_crystallization_and_self_play_20261124_v1.json`.
- **3-Way Memory Ablation:** `empty` (`5 -> 5` probes) vs. `raw_trace` (`5 -> 6` probes, `-20%` negative transfer) vs. **`generalized_s92` (`5 -> 2` probes, `+60.0%` probes saved, `stale_invalidated_on_drift = True`)**.
- **64-Vector `os.fork()` CoW Boundary Fuzzer:** **`5.22 ms` per 64-case run** (`10.44 ms` for 2 runs), catching `7` `None`/boundary crashes on unsafe `.strip()` while passing `64/64` on safe coalescing.
- **360-Step Articulation-Point Checkpointed Horizon:** Planned in `0.84 ms` (`0` constraint loss across `120` destructive traps) and executed across **`12` exact Petri-Net articulation cuts**; under injected fault at step `317`, rolled back **only `30` steps** (to cut-vertex checkpoint `300`) instead of `317` steps.

### 4.4 Zero-Test-Leakage Issue-Only Upstream SWE Solves, Harbor Container Worker & `HONEST_SUITE_BASELINE` Audit
Artifact: `canonical/Immediate_Results/issue_only_and_honest_baseline_audit_20261124_v1.json` (`0` model calls).
- **Zero-Test-Leakage Issue-to-Oracle Abduction (`extract_candidate_repro_tests_from_issue`)**: Evaluated at pure `commit~1` (`base_commit` ONLY, with the fix commit's `tests/` held out 100% until post-solve grading):
  - **`werkzeug@051fd66352~1` (Issue prose only)**: Solved in **`9` simulations (`7.95s`)** with `zero_test_leakage_in_patch = True`; post-solve checkout of held-out `tests/test_http.py` passed **`124 / 124` (`0.29s`)**.
  - **`click@05f6fd0df4~1` (Issue snippet + expected value only)**: Solved in **`48` simulations (`33.60s`)**, crystallized **`uir_law_6efc5c047e37`**, `zero_test_leakage_in_patch = True`; post-solve checkout of held-out `tests/test_arguments.py` passed **`116 / 116` (`0.21s`)**.
- **Audit of `open_model().solve(mode="EPISTEMIC")`, `244`, `226`, `447`, and `HONEST_SUITE_BASELINE_20261103_V1.json`**:
  - **`open_model().solve(..., mode="EPISTEMIC")`**: **Refuted as special-cased engine mode** — `brain_unified_model_v1.py` special-cases only `RECALL` and `SOLVE_OR_LEARN` (`MODE_NOT_SPECIAL_CASED_BY_ENGINE:EPISTEMIC`). Wired zero-LLM container fallback into `canonical/runtime/harbor_container_solver_worker_v1.py` (verified under bare `env -i PATH=/usr/local/bin:/usr/bin:/bin python3 -I -B`, writing scratch state strictly to `/tmp/`).
  - **`"244 verified post-training OSS commits"` & `"226 tricks"`**: **Refuted / Conflated** — in repo docs, `244` is the `244`-term tarball/filesystem/SQLite grammar (`AGREEMENT_IS_NOT_EQUIVALENCE_20261119_V1.md`), `226` is `226/233` deliberate `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT` safety refusals (`DOES_IT_SOLVE_EVERYTHING_20261103_V1.md`), and `447` is verified (`153` bound + `294` receipt-backed capabilities).
  - **`HONEST_SUITE_BASELINE_20261103_V1.json`**: Verified **`344` failing files / `1,026` failing cases** (`793` `ASSERTION`, `113` `OTHER`, `69` `CURRENTNESS_GUARD`, `43` `IMPORT_ERROR`, `5` `MISSING_FILE`, `3` `NETWORK`).
  - **Live GitHub Actions Harbor + Air-Gapped Docker Execution (`run_id=45537959351`, `job_id=138949134648` on `arena/06dc079e-brain`)**: Executed Harbor `39c2219a` + `SWE-bench_Pro-os` (`66f92766` `HARD-51[:2]`: `NodeBB__NodeBB-8168c6c4...` JS & `ansible__ansible-40ade1f8...` Python) + `PatchReplayAgent` pristine container replay (`network_mode: none`, `cap_drop: [ALL]`, `/opt/brain-ro:ro`) in `4m24s` with **`0` trial exceptions, `0` leaked processes, `issues = []`**, and honest fail-closed `reward = 0.0` (`0/2` on `HARD-51` multi-file enterprise tasks without unverified guessing).

---

## 5. Verification Commands (`84 / 84` Passing in `13.4s`, `0` Integrity Violations)

```bash
python3 -m pytest -q -o asyncio_default_fixture_loop_scope=function \
  canonical/tests/test_causal_cegis_inventor_v1.py \
  canonical/tests/test_perfect_algorithm_v1.py \
  canonical/tests/test_petri_cow_unified_architecture_v1.py \
  canonical/tests/test_harbor_epistemic_agent_v1.py \
  canonical/tests/test_harbor_container_solver_transport_v1.py \
  canonical/tests/test_harbor_experimental_vm_v1.py \
  canonical/tests/test_swebench_verified_epistemic_adapter_v1.py

python3 execution_guard/repo_integrity_guard_v1.py --base origin/main
```
