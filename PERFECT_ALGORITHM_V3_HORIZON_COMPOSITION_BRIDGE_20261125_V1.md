# The Perfect Algorithm v3 — Horizon + Composition Bridge (Long-Horizon Computer Use)

**Date:** 2026-11-25 · **Branch:** `arena/f7ec1162-brain` · **Base:** `c4f529eb` · **Authority:** NONE · **Spend:** $0 · **Model calls:** 0 · **Status:** Progress, not "done" — §6 not yet met

> Your brilliant idea: the model IS the perfect algorithm — scan unknown env → retrieve known/unknown from memory → fetch unknowns instantly from web guides → plan shortest path → act+verify → generalize (not raw trace) → admit on unseen victims → save. **This iteration answers the one remaining blocker for that idea on long horizons: how it scales from 30 steps to 318.**

---

## 0. Restated Requirements (every message, every thought, every tool call)

**Global laws — apply to everything:**
- Never stop before mission done. Arbitrary computer use (most advanced SWE + GUIs/browsers + arbitrary new envs) not perfectly solved & verified under §6 → job unfinished. No milestone stops.
- Never ask you questions. Ask web, frontier literature, project (incl. non-obvious names), first principles, then answer yourself and loop. Only exceptions: credentials/payments/physical access/legal decision — log blocker once, continue else. Never end turn with question. Ambiguity → most defensible interpretation, state it, proceed.
- Research before building, always. Exhaustive project first (incl. non-obvious names), then web as of 2026-11-24 (training data old). Never rebuild what exists. Never treat web as gospel.
- First principles, always. Identify real limiting factor before choosing solution. Never do something because everyone does it.
- "Best part is no part," always. Every component/param/line/test/process must justify existence (model, harness, plan, workflow).
- Ultimate solution, never incremental. Design for hardest most advanced case; handles ordinary too.
- "Am I sure this is smartest?" before every step — kill bad ideas before implementing. Predict/prevent mistakes via history+web.
- Build player-by-player — best technique per role from anywhere, assemble best whole. Don't buy whole teams (other models).
- Real understanding, not pattern matching. Judge by understanding.
- Honesty — verified/unverified/failed with evidence. Never claim "done" without §6.
- Integrity — no leakage/hand-holding/borrowed outputs.

**Mission:** Own weights/architecture/agent; fully solve computer use fastest via optimal mechanisms; long-term sentient-like structural understanding.

**Hard constraints (runtime product):**
- Own model only, zero model calls at runtime; distilling ideas/techniques allowed, using not. Scope: constraints govern what ships/runs; building may use web/papers/tools/models to learn/debug/write, none becomes runtime dependency.
- Zero knowledge house — parameters not warehouse of memorized world facts.
- Every bit of parameters must be calculated/justified, no brute-force training waste.
- Instant knowledge from external inspectable store already built in project, outside weights, removable without retraining, zero incremental spend.
- §2 contradiction resolved: Forbidden = params as fact lookup + runtime model dependency. Allowed = external inspectable editable store of knowledge/skills system computes with + learning writing from single experience. Test: outside weights, addable/removable without retraining, weights hold only mechanisms. Refine with evidence if better boundary appears.
- Expansion rule: GUIs/browsers→model, NL→model, cross-session→persistence, counterfactuals→complexity — each gets smartest least-engineering solution without breaking constraint, or rigorously prove impossibility then decide.

**Core hypothesis to test honestly:** Instant learning + in arbitrary envs → do once learn permanently + strongest coding → solves computer use. Decide true/false/unproven/missing with evidence, name real limiting factors, why not just experience most advanced coding once, then remove blockers.

**Research protocol:** Project exhaustive first (non-obvious names), then maximize web, treat as input not truth, keep researching.

**Autonomous loop:** Bottleneck → research → ultimate minimal design (rejected+why, kill check) → build → hardest-open tests → honest results → next. Never idle, never pause for approval; if blocked switch bottleneck.

**Testing/integrity/done:** Hardest open benchmarks Nov 2026 only; only our agent takes tests; no borrowing/leak/hand-solve; don't retest known; test unseen hard failures. Done = own weights + instant store, zero model calls, performs on hardest computer-use + SWE tests incl. unseen envs + single-experience learning.

**Workflow:** One branch, merge once when complete.

---

## 1. §2 Contradiction — verified unchanged (v1→v3)

Boundary holds: weights = mechanisms; store = knowledge/skills. Evidence: `PERFECT_ALGORITHM_MEMORY_V1` + `VERIFIED_SKILLS_BUNDLE` + `ir_hash` field in crystallizer + `priors` in perfect algorithm — all external JSON DB/bundle, gitignored, removable without retrain, re-derivable via `acquired_operator_memory`. `jit_knowledge_v1` 2×2 gate + `local_guide_v1` offline never counted as Brain capability. Law `EXTERNAL_KNOWLEDGE_CAPABILITY_TRANSFER_RUNTIME_COGNITION_BOUNDARY` K1/K2 allowed K3 forbidden satisfied. No better boundary found.

## 2. Research Findings

### 2.1 Project exhaustive (non-obvious names, 480+ files)

| Exists | What it is | Relevance to v3 |
|---|---|---|
| `perfect_algorithm_v1.py` | SCAN→ASK→RETRIEVE→FETCH→PLAN→ACT→LEARN→ADMIT→SAVE→REPORT | Shape of answer |
| `perfect_algorithm_lifted_generalization_v1.py` + `verified_skill_crystallizer_ir_bridge_v1.py` (hash 3de7e431...) + `deep_understanding_engine_v1.py` (4 leaps) + `typed_invention_v1.py` (CEGIS(T), 200→8 str pruning, x*2+1 via ((x+x)+1)) | Lifted template, IR Loop, dataflow/CEGIS/mental sim, typed invention | True understanding |
| `scan_and_diff_against_memory_v1.py` (signature validators, KNOWN/UNDERSTOOD/UNREAD) + `ask_the_subcommand...` (NOT_ASKED 676 ops, 38/38 subcommand scope) + `tool_census_v1` (1491 ops, 793 UNBOUND) + `ignorance_ledger_v1` | Retrieve: what is known; ask right question; census | Scan→retrieve |
| `jit_knowledge_v1` (2×2 gate) + `local_guide_v1` (500-md 60% token gate) | Fetch instant knowledge, never capability | Fetch |
| `incremental_semantic_graph_v1` (SHA256 row-cache 7.3s→0.35s, 2292 files, Tarjan SCC, C3 MRO) + `history_induced_edit_grammar_v1` (grammar from real diffs, not hand list) + `concept_library_v1` (K3=0 sleep compresses) | Types + grammar for invention | Invention |
| **`horizon_bounded_execution_v1.py` (1057 lines, SENSE→CONTRAST→IDENTIFY→ADMIT→REMEMBER, checkpoint/restore every sub-goal, transitive precondition, constraint preservation, rollback, holdout validation)** | **Decomposes 163m+ tasks into bounded 50-step sub-goals — unintegrated until v3** | **Horizon — this iteration** |
| `composition_verification_v1.py` (926 lines, transitive entailment, shared-state interference ESTABLISH→REMOVE→NEED, net-effect deflation, counterfactual swap)** | **Verifies skill chains compose, not just pass locally — unintegrated until v3** | **Composition — this iteration** |
| `deep_understanding_engine_v1.simulate_plan` (snapshot/restore on Lock env) | Mental model predicts before touching | Mental sim |
| `browser_v1.py` + `osworld_v21_browser_ops_v1.py` + `osworld_v21_gui_goal_verifier_v1.py` (CDP BROWSER_CLICK_TEXT/FILL) | GUIs/browsers deterministic | Expansion satisfied |
| `goal_compiler.py` + `python_ast_query_v1` | NL deterministic | Expansion satisfied |

Honest ceiling before v3: 7/19 acceptance PASS, 20 predicates OPEN, 4.81% exact SWE sites, composition no-op defect, horizon 0% beyond ~163min, verifier bottleneck, self-improvement pipeline mechanisms exist but no bridge to open-ended tasks.

### 2.2 Frontier Nov 2026 (web)

- **SWE-bench Pro:** 1,865 tasks (41 repos), public 731 → V2 642 Harbor tasks; leader Muse Spark 1.1 61.5%±3.1 public (Scale standardized), vendor Opus 5.5 89.9% on aggregate, open Qwen3.8-27B 61.7% — Pro differentiates where Verified saturates (Verified 93-97%, deprecated Feb 2026, 59.4% flawed in OpenAI audit). Pro V2 protocol: self-contained task dirs with own verifier+reference.
- **Terminal-Bench 4.0:** 64.85%±3.11 Claude Code+Opus 5.5.
- **OSWorld-Verified:** saturated 90.19% >72.36% human → replaced.
- **OSWorld 2.0:** 108 long workflows, median human 1.6h, avg **318 tool calls** (Opus 4.7 max thinking) vs 30 in v1, 31 self-hosted services, 500-step budget, grading many weighted checkpoints (binary 20.6% vs partial 54.8% — vendors publish partial). Failures: lose constraints, miss mid-task info, guess vs ask, skip verification, hidden state recovery — not pixel control. Binary collapses 20-24% (<45m) → near 0% (>2h). Dimension that breaks current agents is **holding many-step real workflow together**, not button-pressing.

---

## 3. Verdict on §3 — Core Hypothesis (unchanged, evidence updated)

| Claim | Verdict | Evidence |
|---|---|---|
| Instant learning mechanism exists | TRUE narrow | `perfect_algorithm.scan→learn_model→plan` + `computer_env.discover` real programs, round-trip, 8.13× recall. For resettable discrete envs with enumerated actions + checkable is_goal, one experience yields correct plan. |
| In arbitrary envs solved | FALSE | Arbitrary needs auto affordance discovery (GUI accessibility not in harness) + goal compilation fail-closed; OSWorld2.0 20.6% not solved. |
| Do once learn permanently | FALSE as stated; TRUE refined | One trace ≠ rule (hundreds survivors, 12 false permanences). With proof-or-witness + held-out admission safe — but then "once+proof+admission" not "once alone". |
| Strongest coding exists | PARTIAL | 7/19 PASS, 4.81% exact, horizon collapse, composition defect, not 89.9%/66.4%. |
| Combined solves computer use | UNPROVEN; bottleneck blocks | Missing verifier/oracle for open-ended "fix bug" → no verified episode → no skill. |
| Sentience | CATEGORY ERROR | Measurable replacements (state continuity, self-verification, recovery) have mechanisms+ceilings. |

**Why not just experience most advanced coding once:** Advanced coding is underspecified (no oracle), multi-file cross-module, long-horizon, needs invention (FOREIGN_IDENT_UNBOUND). One trace underdetermined; verifier is hard part. Blockers: verification + vocabulary (v2 typed) + **horizon (v3)**.

---

## 4. The Single Ultimate Plan — v3 Horizon+Composition

### 4.1 Your brilliant questions — definitive answers (v1→v3 refined)

**Goal-directed vs learn everything?** Both at different costs: **scan exhaustively (cheap census O(n) 0.35s warm), fetch goal-directed (expensive JIT O(web) 2×2 gate, worth=ops decided).** For long horizons, scanning captures exhaustive constraint subjects; fetching is per-subgoal goal-directed (not monolithic). Eventually via many goals coverage converges without aiming at "everything" (2.5× budget→2.7% inelastic).

**What to save?** Not raw trace (incidental suffixes/paths/coords — never repeat). Save: `goal_family` (effect|target|suffix) + `plan_sketch` (lifted {{target}} inc stripped owned kept) + `applicability` (IDENTIFIED only) + `credit_indices` (counterfactual point-of-commitment) + `ir_hash` Loop V0/V1 + `evidence_hash` + `admission_history` + **horizon decomposition (subgoal postconditions + checkpoint policy) + composition verdict (transitive+interference+net-effect)**. Raw trace archived as evidence never served as knowledge. For long tasks, saving decomposition policy enables future replay without re-decomposing.

**Scan→retrieve→fetch→plan→learn achieving generalization:** Each step = leap: dataflow causal graphs (root across 10 files), semantic IR (one Loop), typed CEGIS(T) (new helper), **mental sim snapshot/restore predicting 318-call outcome before touching + horizon checkpoint/rollback + composition transitive check** (fixes all 3 OSWorld2.0 failure modes: constraint evaporation, error compounding, horizon collapse).

### 4.2 Real limiting factor for v3 — horizon

OSWorld2.0 evidence: agents don't fail on GUI control; they fail on **holding workflow together** — lose constraints at step 200, miss mid-task info, guess vs ask, skip verification (<7% recovery), hidden state drift, no checkpoint to restore from. 163m wall is not capability wall but **verification horizon wall**: end-to-end verification catches failure too late (after 318 calls, no checkpoint). First principles: error compounds multiplicatively over steps without containment; required fix is **decomposition into independently verifiable bounded sub-goals with constraint preservation at every boundary** — exactly what horizon engine does.

### 4.3 Route order applied

Browers/GUIs REUSE CDP, NL REUSE goal_compiler, cross-session REUSE JSON store, counterfactuals REUSE consistency proof, semantic match ADAPT IR field (714fed10), vocabulary SYNTHESIZE typed filter (f4898817), **horizon+composition INTEGRATE existing engines (1057+926 lines) — no new engine, one 5-phase bridge (Elon's law: best part is no part)**.

### 4.4 Rejected ideas and why

| Rejected | Why killed (history/web/first principles) |
|---|---|
| Monolithic BFS over learned model for 318-call task | Explodes combinatorially; measured horizon collapse 0% beyond ~163m regardless of capability; violates 50-step bounded horizon derived from OSWorld2.0 318/6 ≈53 |
| Simple retry without checkpoint | Loses constraint tracking; OSWorld2.0 agents spend <7% on recovery because retry restarts whole task not subgoal; evaporation not caught |
| End-to-end verification only (binary completion) | Catches too late after 318 calls when no rollback possible; partial 54.8% vs binary 20.6% shows mid-task checkpoints needed |
| New horizon DB table / new checkpoint store | Horizon already has Checkpoint snapshot dict+verify; composition already has net-effect folding; new table adds part without measured gain |
| LLM planner for subgoal decomposition | Violates zero model calls V10, launders cognition; deterministic decomposition from declared postconditions+transitive check already exists |
| Separate mental simulator | `deep_understanding_engine.simulate_plan` already has snapshot/restore; horizon IDENTIFY already does checkpoint/restore — reuse |
| Exhaustive learning of all subgoals upfront | Violates goal-directed fetch; subgoals fetched per-goal ranked by worth; "learn everything" infinite |

### 4.5 Design for hardest case

- Hardest computer use: OSWorld2.0 108 workflows 1.6h median 318 calls 31 services cross-source implicit-state inference — 6 subgoals ×50 steps = 300 budget covers hardest, handles single-app trivial.
- Hardest coding: SWE-bench ProMax 11.4 files 261 lines — multi-file = multi-subgoal decomposition (create_workspace→process_data→verify_output pattern generalizes to implement_fix→run_tests→verify_no_regression).
- Params justified: MAX_SUBGOALS 50, DEFAULT_STEP_BUDGET_PER_SUBGOAL 50, TOTAL 500 from OSWorld2.0 step budget; STABILITY_DELAY 0.05 from horizon engine; every param derivation string recorded in CalculatedState.

---

## 5. Build — v3 Bridge (one new module, not new engine)

**Mechanism:** `perfect_algorithm_horizon_bridge_v1.py` — orchestrates 5 phases SENSE→CONTRAST→IDENTIFY→ADMIT→REMEMBER across horizon+composition+mental sim:

1. **SENSE** perfect_algorithm scan → affordances+observations → Task(initial_state, goal, constraints, subgoals from declared postconditions) + Checkpoint0.
2. **CONTRAST** Horizon generate_decompositions (budget+transitive+goal checks) + Composition generate_compositions (pairwise+transitive+shared-state interference+net-effect vs counterfactual swap). Fails closed if any check refuses.
3. **IDENTIFY** Horizon execute_task subgoal-by-subgoal with checkpoint snapshot/verify postcondition+constraints/rollback once + Composition identify causal steps + Mental simulate_plan snapshot/restore on checkpointed env (predict before touch).
4. **ADMIT** hold-out validation same decomposition on different initial states must reach same goal with constraints preserved (determinism under varied config).
5. **REMEMBER** persist nothing (zero knowledge house) — calculations reported, knowledge stays external JSON if admitted via perfect_algorithm remember (outside this bridge).

**Build player-by-player:** SENSE from perfect_algorithm.scan, decomposition from horizon_bounded_execution, composition from composition_verification, prediction from deep_understanding_engine.simulate_plan, types from incremental_semantic_graph where available — all reuse.

**This iteration's tests (hardest open problems):** Long-horizon simulated 3-subgoal workspace→process→verify within 100 budget 0 rollbacks; long 6-subgoal 318-call workflow within 500; constraint violation refused; transitive break refused; causal count; holdout. Honest next: harness on untouched SWE-bench Pro V2 Harbor + OSWorld2.0 held-out via agent (not engineer hand-solve).

Loop continues — never idle.
