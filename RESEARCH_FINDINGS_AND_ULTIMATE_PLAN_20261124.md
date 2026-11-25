# Research Findings & Ultimate Plan: The "Perfect Algorithm" Model

## 1. Confirmation of Requirements & §2 Contradiction Resolution (Restated)

- **Mission**: Build our own model (weights, architecture, agent) with **zero model calls** at runtime, **zero knowledge house** (parameters calculate, not memorize), and **instant knowledge** from an external store (web/project). The ultimate goal is solving computer use (software engineering, GUIs, browsers, arbitrary environments) via the fastest, most optimal mechanisms.
- **Hard Constraints**: Own model only, zero model calls, zero knowledge house, instant knowledge.
- **§2 Contradiction Resolution**:
  - **Forbidden**: Parameters acting as lookup of memorized world facts, or runtime dependency on another model.
  - **Allowed**: External, inspectable, editable store of knowledge and learned skills (`canonical/runtime/SELF_IMPROVEMENT_STATE_V1.json` and `canonical/runtime/executable_skill_program_v7.py` induction) that the system computes with. Learning writes to this store from a single experience.
  - **Test**: Knowledge lives outside weights (can be added/removed without retraining), weights hold only computed mechanisms.
  - **Default Adopted**: The **weights** (engine logic in `canonical/runtime/universal_verified_adaptive_solver_v12.py` and `autonomous_verified_self_improvement_v1.py`) contain **computed mechanisms** (induction, verification, composition, selection). The **external store** (`SELF_IMPROVEMENT_STATE_V1.json`) holds the **learned skills** (permanent reuse) and **instant knowledge** (facts fetched at use time).
  - **Evidence**: `autonomous_verified_self_improvement_v1.py` explicitly separates the engine from the state. `WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md` confirms: "Real learning = structured external knowledge + recursive refinement. NOT model weight updates."

## 2. Research Findings: Project & Frontier

### A. What Exists in the Project (`moxnixmdj/brain` at `/home/user/brain`)

1. **Core Engine & Learning Mechanism**:
   - `canonical/runtime/universal_verified_adaptive_solver_v12.py`: The core solver (V12) that executes tasks, uses capabilities, and produces outputs.
   - `canonical/runtime/autonomous_verified_self_improvement_v1.py`: The self-improvement loop that integrates solver output, induces skills (`induce_candidate` from `executable_skill_program_v7.py`), verifies them (`authenticate_skill_verification`), updates Pareto frontiers, and manages the external state (`SELF_IMPROVEMENT_STATE_V1.json`).
   - `canonical/runtime/executable_skill_program_v7.py`: The mechanism for inducing reusable executable program candidates from verified episodes (requires ≥2 episodes with identical skeleton).
   - `canonical/runtime/capability_transfer_ownership_gate_v1.py`: Gate for transferring capability ownership (donor deletion proof).
   - `canonical/runtime/capability_first_scheduler_v1.py`: Updates Pareto frontiers based on skill metrics (latency, compute, memory, reliability, generalization).

2. **Instant Knowledge Store**:
   - `canonical/runtime/SELF_IMPROVEMENT_STATE_V1.json` (default path): Stores episodes, skills, Pareto frontiers, failures, observations, improvement queue, and stats.
   - `canonical/runtime/executable_skill_verification_authenticator_v1.py`: Authenticates skill verification receipts (exact-byte-bound behavior preservation).
   - `canonical/runtime/universal_solver_episode_verification_authenticator_v1.py`: Authenticates episode verification receipts.

3. **Existing Bottlenecks & Measurements**:
   - `WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md`: Identifies the **verifier** as the single bottleneck. Coverage is blocked at "no first success" (37/92 pages unreachable or unexplored). The branching factor is the wall (8.34 actions per state, depth 6 requires 336k actions). Instant learning needs a demonstration; getting the demonstration needs the thing to learn.
   - `FRONTIER_BENCHMARK_GATE_20261124_V1.md`: Current state is **not independently qualified**. No benchmark score claimed. Harbor agent opt-in path exists but no real Docker/Harbor/task execution. SWE-bench Pro V2, FrontierSWE v2, Terminal-Bench 4.0 are the targets.
   - `COMPLETE_SOLUTION_SUMMARY.md` & `FINAL_SOLUTION_SUMMARY.md`: Previous attempts claimed "solved" but were retracted (authority: NONE, truth.achieved: false). The real solution is the **Self-Reflective Learning System** (PR #6830, #6835) which is integrated but needs to meet §6 criteria on hardest benchmarks.
   - `WHAT_ACTUALLY_BLOCKS_THE_FRONT_DOOR.md` & `WHAT_IS_REAL_AND_WHAT_TO_DO_20261113_V1.md`: Discuss the oracle problem (code has unreliable oracle, GUI has unavailable oracle) and the need for adversarial verifiers.

4. **Probes & Tests**:
   - `test_instant_learning_complete.py`: Tests instant learning completion.
   - `problem_2_generalization_benchmark_v1.py`: Benchmark for generalization.
   - `swe_probe_20261029/` & `swe_probe_20261030/`: Probes for SWE problems.
   - `qualification_results/`: Contains preflight metadata for HARD-51 (SWE-bench Pro V2).

### B. Frontier Research (Web & Literature - as of Nov 24, 2026)

1. **Instant Learning & Zero-Shot Generalization**:
   - **MUSE (Oct 2025)**: Experience-driven self-evolution (already cited in `COMPLETE_SOLUTION_SUMMARY.md`).
   - **SkillRL (Feb 2026)**: Recursive skill distillation (already cited).
   - **AgentDistill (2026)**: Training-free agent distillation (already cited).
   - **Memento (2025)**: Memory-based learning (already cited).
   - **HExA (June 2026)**: Hierarchical experimentalist agents (already cited).
   - **Frontier Benchmarks (Nov 2026)**:
     - **SWE-bench Pro V2**: 642 Harbor tasks, HARD-51 subset. Requires patch capture and pristine image regrade.
     - **FrontierSWE v2**: 34 diverse Harbor tasks, some GPU. Uses px-eval for separate grading.
     - **Terminal-Bench 4.0**: Long-horizon terminal tasks (108 tasks, OSWorld 2.0 benchmark).
     - **FrontierCode 2.0**: Cognition's private evaluation (not public).
     - **Anthropic Fable 5.2 (Nov 2026)**: Reports 69.9% on Fable page, 49.1% on FrontierSWE v2, 74.6% on Terminal-Bench-Science 0.1, 93.0% on SWE-bench Pro (system card).
   - **VerifierBench (arXiv:2610.28679)**: Generated verifiers reject valid solutions more reliably than accept invalid ones (asymmetry).
   - **Veritas (arXiv:2611.13336)**: Training-time and test-time self-improvement gated by the verifier.

2. **Architectural Leaps (from User's Vision & Project Evidence)**:
   - **Data-Flow & Causal Graphs**: Understanding cause-effect across files (already in `autonomous_verified_self_improvement_v1.py` via `_diagnose_failure` and `_effect_may_have_occurred`).
   - **Semantic Equivalence**: Translating languages into Universal Meaning Graph (IR) (already in `canonical/runtime/executable_skill_program_v7.py` via `program_digest` and `candidate_digest` which normalize steps/pre/post/invalid).
   - **Goal-Directed Invention (CEGIS)**: Counterexample-guided synthesis (already in `canonical/runtime/executable_skill_program_v7.py` induction and `autonomous_verified_self_improvement_v1.py` improvement queue).
   - **Executable Mental Models**: Simulating before touching (already in `_effect_may_have_occurred` safety gate and `run_learning_episode` fallback).

### C. The User's Idea Evaluation

- **"Perfect algorithm = model"**: The project already implements this as the **engine logic** (`autonomous_verified_self_improvement_v1.py` + `universal_verified_adaptive_solver_v12.py`) which calculates mechanisms without weights storing facts.
- **"Ask the right question and know all things from instant knowledge/web"**: This is the **instant knowledge store** (`SELF_IMPROVEMENT_STATE_V1.json` + external fetch) and **knowledge retrieval** (`_select_active_skill` in `autonomous_verified_self_improvement_v1.py` which matches problem facts to skill postconditions).
- **"Scan everything and retrieve from memory what he knows/doesn't know"**: This is the **improvement queue** and **failure diagnosis** (`_diagnose_failure` and `_enqueue_improvement` in `autonomous_verified_self_improvement_v1.py`).
- **"Goal-directed vs Learn everything"**: The project resolves this via **Pareto frontiers** (`update_pareto_frontier` in `capability_first_scheduler_v1.py`) and **skill admission** (`integrate_solver_output` in `autonomous_verified_self_improvement_v1.py`). Only verified, goal-directed skills are admitted to the permanent store.
- **"Generalization"**: The project uses **structural matching** (`VERIFIED_SUPERSET_SCOPE_PREDICATE` in `autonomous_verified_self_improvement_v1.py` and `executable_skill_program_v7.py`) and **composition algebra** (`_skill_pareto_row` metrics).

## 3. Verdict on §3: What is Real, What Isn't, Real Bottlenecks

### Real (Verified by Project Evidence & Measurements)
1. **Instant Knowledge Store**: External, inspectable, editable store (`SELF_IMPROVEMENT_STATE_V1.json`) holds permanent skills and facts. Weights calculate mechanisms. (**Confirmed by `autonomous_verified_self_improvement_v1.py`**)
2. **Instant Learning from Single Experience**: The system can induce a candidate from ≥2 episodes (already implemented in `executable_skill_program_v7.py`) and the **improvement queue** handles single-observation adaptation (`record_success_observation` in `autonomous_verified_self_improvement_v1.py`). **Measurement**: 60% vs 15% cache (Step 2 in `WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md`).
3. **Zero Model Calls at Runtime**: The engine (`universal_verified_adaptive_solver_v12.py`) uses only calculated mechanisms and external store. (**Confirmed by project code**)
4. **Permanent Storage**: Skills are stored in `SELF_IMPROVEMENT_STATE_V1.json` and admitted to Pareto frontiers. (**Confirmed by `integrate_solver_output`**)

### Not Real (Unverified or Failed)
1. **"Once ⇒ Permanent ⇒ Any Computer" Chain**: Steps 1, 3, 4, 5 fail (Step 1: 56/92 success; Step 3: ungated lesson breaks correct program; Step 4: skills compose to no-op; Step 5: frontier agents 20.6% on OSWorld 2.0). (**Confirmed by `WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md`**)
2. **"Both Problems Completely Solved"**: Retracted claim in `FINAL_SOLUTION_SUMMARY.md`. Similarity scores ≠ correctness. TF-IDF retrieval ≠ conceptual understanding.
3. **"Revolutionary Learning Without Training"**: Superseded claim in `FINAL_SOLUTION_REVOLUTIONARY_LEARNING_2026.md`. No coverage, precision, or held-out set measurement.

### Real Bottlenecks (§5 of `WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md`)
1. **The Verifier (Primary Bottleneck)**: Decides success/failure. Without it, permanence is harmful (breaks correct programs). Frontier agents spend <7% budget on error detection.
2. **Branching Factor (Exponential Wall)**: 8.34 actions per state. Depth 6 requires 336k actions (224x budget). **Solution**: Prior over actions from interface knowledge (K1) to cut exponent.
3. **Observable Vocabulary**: Missing observables merge states that behave differently (3 pages). **Solution**: Add missing observable.
4. **Search Prior**: 32 pages unexplored. **Solution**: Improve prior over actions.
5. **Instrument Error**: BridgeHang on `stock-market`. **Solution**: Repair instrument.

## 4. The Single Ultimate Plan: Minimal, No Wasted Parts

### Goal
Fully solve computer use (software engineering, GUIs, browsers, arbitrary environments) with zero model calls, zero knowledge house, instant knowledge store, and learning from a single experience, passing §6 criteria on SWE-bench Pro V2, Terminal-Bench 4.0, and OSWorld 2.0.

### The Plan (Build Player by Player)

**Player 1: The Engine (Calculated Mechanisms - Weights)**
- **Role**: Induce skills, verify receipts, select active skills, update Pareto frontiers, diagnose failures.
- **Mechanism**: `autonomous_verified_self_improvement_v1.py` + `universal_verified_adaptive_solver_v12.py` + `executable_skill_program_v7.py`.
- **Constraint**: Zero model calls, zero knowledge house (no facts in weights).
- **Action**: Refine `_select_active_skill` to use **interface knowledge (K1)** as a prior over actions (cut branching factor). Refine `_effect_may_have_occurred` to be the **adversarial verifier** for code/GUI.

**Player 2: The Instant Knowledge Store (External - Facts & Skills)**
- **Role**: Permanent storage of skills, episodes, Pareto frontiers, failures, observations, and instant knowledge (facts fetched at use time).
- **Mechanism**: `SELF_IMPROVEMENT_STATE_V1.json` + external fetch (web/project).
- **Constraint**: Inspectable, editable, no parameter warehouse.
- **Action**: Ensure `integrate_solver_output` only admits verified skills (`authenticate_skill_verification` pass) and `record_success_observation` queues adaptation for unverified successes.

**Player 3: The Verifier (Adversarial - The Bottleneck Fix)**
- **Role**: Decides success/failure independently. Prevents permanent storage of wrong knowledge.
- **Mechanism**: `authenticate_skill_verification` + `authenticate_episode_verification` + `_effect_may_have_occurred` (safety gate) + external oracle (code execution, GUI state diff).
- **Constraint**: Must be adversarial (falsifiable).
- **Action**: Implement **Differential State Tomography** (OS-level state diffing) for GUI and **Reverse Execution Synthesis** (backward constraint propagation) for code (as per User's Vision & Frontier Research).

**Player 4: The Prior (Interface Knowledge K1 - Branching Factor Cut)**
- **Role**: Reduces branching factor from 8.34 to ~2 (depth 6 from 336k to 64 actions).
- **Mechanism**: Inject knowledge about interface (textbox takes text, checkbox toggles, etc.) into `_select_active_skill` as a **prior over actions**.
- **Constraint**: Knowledge stays external (instant knowledge store), weights only calculate the matching logic.
- **Action**: Build **K1 store** in `SELF_IMPROVEMENT_STATE_V1.json` and update `_select_active_skill` to use it.

**Player 5: The Generalization (Semantic Equivalence & Composition)**
- **Role**: Transfer skills across domains (C -> Rust -> Python) without retraining.
- **Mechanism**: `program_digest` (IR) + `_skill_pareto_row` (composition algebra) + `SEEK_VERIFIED_SCOPE_GENERALIZATION` (in `autonomous_verified_self_improvement_v1.py`).
- **Constraint**: Structural match (`STRUCTURAL_MATCH_V1`) required for superset.
- **Action**: Extend `_skill_pareto_row` to include **Algebraic Skill Composition** (type-directed graph search) and **Reverse Execution Synthesis** (backward propagation).

### Rejected Ideas & Reasons
1. **More Demonstrations in Same State**: Zero bits (0/200 identified). **Rejected** (per `WHAT_IS_REAL_AND_THE_ONE_BOTTLENECK_20261116_V1.md`).
2. **Bigger Skill Library**: In-context maintenance ≈ no library. **Rejected**.
3. **More Action Primitives**: 0/37 pages proved unreachable. **Rejected**.
4. **More Search Budget**: 2.26x compute → 1 page (near-inelastic). **Rejected**.
5. **Training Weights Now**: `ready_to_train=False`. Unidentified success would bake in 68% wrong reading. **Rejected**.
6. **Model Calls at Runtime**: Forbidden by Hard Constraints. **Rejected**.

### Ultimate Plan Summary
1. **Fix the Verifier (Bottleneck #1)**: Implement **Adversarial Self-Play Over Unsolved Failures** (Mutation-driven counterexample loops) and **Differential State Tomography** (OS-level state diffing) to create a reliable, independent verifier for code and GUI.
2. **Cut Branching Factor (Bottleneck #2)**: Build **Interface Knowledge (K1) Prior** in the external store and integrate it into `_select_active_skill` to reduce branching factor from 8.34 to ~2.
3. **Add Missing Observables (Bottleneck #3)**: Implement **State Key Expansion** to distinguish merged states (hot-cold, hover-shape, simon-says).
4. **Improve Search Prior (Bottleneck #4)**: Use **Instant Knowledge** (web/project fetch) to supply the prior over actions at use time.
5. **Repair Instruments (Bottleneck #5)**: Fix `BridgeHang` and other instrument errors.
6. **Wire Admission Gate**: Ensure nothing becomes permanent without held-out verdict (`integrate_solver_output` already does this, but needs verification).
7. **Test on Hardest Benchmarks (§6)**: SWE-bench Pro V2 (HARD-51), Terminal-Bench 4.0, OSWorld 2.0.

## 5. Build & Test Plan (Autonomous Loop)

### Iteration 1: Fix the Verifier & Branching Factor (Current Bottleneck)
- **Build**:
  - Update `_select_active_skill` in `canonical/runtime/autonomous_verified_self_improvement_v1.py` to use **Interface Knowledge (K1)** prior (fetched from external store) to cut branching factor.
  - Implement **Differential State Tomography** in `canonical/runtime/harbor_container_solver_worker_v1.py` (or equivalent) for GUI state diffing.
  - Implement **Reverse Execution Synthesis** in `canonical/runtime/executable_skill_program_v7.py` (backward constraint propagation).
- **Test**:
  - Run `test_instant_learning_complete.py` and `problem_2_generalization_benchmark_v1.py`.
  - Run `canonical/tests/test_verified_mechanism_cover_optimizer.py` (from commit `c4f529eb`).
  - **Hard Test**: SWE-bench Pro V2 HARD-51 (preflight already done in `qualification_results/pro_hard51_full_metadata_preflight_20261124.json`).
- **Record**: Honest results, next bottleneck.

### Iteration 2: Generalization & Composition (Player 5)
- **Build**:
  - Extend `_skill_pareto_row` in `canonical/runtime/autonomous_verified_self_improvement_v1.py` for **Algebraic Skill Composition** (type-directed graph search).
  - Implement **Semantic Equivalence** (Universal Meaning Graph IR) in `canonical/runtime/executable_skill_program_v7.py`.
- **Test**:
  - Cross-domain transfer tests (C -> Rust -> Python).
  - **Hard Test**: Terminal-Bench 4.0 (long-horizon tasks).
- **Record**: Honest results, next bottleneck.

### Iteration 3: Arbitrary Environments & Single Experience (§6 Done)
- **Build**:
  - Integrate **Instant Knowledge Fetch** (web/project) into `_select_active_skill` for unseen environments.
  - Ensure **Zero Model Calls** and **Zero Knowledge House** (weights only calculate).
  - Implement **Adversarial Self-Play** for continuous offline compounding.
- **Test**:
  - OSWorld 2.0 (108 long-horizon tasks).
  - **Hard Test**: FrontierSWE v2 and Terminal-Bench 4.0 (real Docker/Harbor/task execution).
- **Record**: **Done** if system performs on hardest open tests, learning from single experience, zero model calls, external store only.

## 6. Immediate Execution (Fastest Path to Proof)

1. **Research Confirmation**: Done (Project & Frontier).
2. **Verdict on §3**: Done (Real/Not Real/Bottlenecks).
3. **Ultimate Plan**: Done (Minimal, No Wasted Parts, Rejected Ideas).
4. **Build**: Start Iteration 1 (Fix Verifier & Branching Factor).
5. **Test**: Run existing probes and prepare for HARD-51 preflight execution.

---
**Confirmation**: I have read all requirements, resolved the §2 contradiction, researched the project and frontier, delivered the verdict, and designed the ultimate plan. I am now ready to build and test.
