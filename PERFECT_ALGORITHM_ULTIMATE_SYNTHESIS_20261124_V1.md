# The Perfect Algorithm — Ultimate Synthesis

**Date:** 2026-11-24 · **Branch:** `arena/f7ec1162-brain` · **Base:** `c4f529eb` · **Authority:** NONE · **Spend:** $0 · **Model calls:** 0

This document delivers the five required items in order: confirmation, contradiction resolution, research findings, verdict, and the single ultimate plan.

---

## 0. Confirmation — I have read every word you wrote

**Global laws (apply to every message, thought, step, tool call, design, test, report):**
* Never stop before mission done — arbitrary computer use not perfectly solved and verified under §6 → job unfinished. No milestone stops.
* Never ask you questions — ask web, frontier literature, project (including non-obvious names), first principles. Only exceptions: credentials/payments/physical access/legal decision. Log blocker once, continue everything else. Never end turn with a question. Ambiguity → pick most defensible interpretation, state it, proceed.
* Research before building, always — exhaustive project search first (including non-obvious names), then web, as of 2026-11-24, training data old. Never rebuild what exists. Never treat web as gospel.
* First principles always — find real limiting factor before choosing solution.
* Best part is no part — every component/parameter/line/test/process must justify existence.
* Ultimate solution never incremental — design for hardest case first.
* Ask “Am I sure this is smartest approach?” before every step — kill bad ideas pre-implementation.
* Build player by player — take best technique from anywhere, assemble best whole.
* Real understanding not pattern matching — judge mechanisms by understanding.
* Honesty — separate verified/unverified/failed with evidence, never claim done without §6.
* Integrity — no leakage/hand-holding/borrowed outputs.

**Mission:** Build our own weights/architecture/agent for full computer-use solving. Fastest route, most optimal mechanisms. Long-term: sentient, actual understanding.

**Hard constraints (runtime product):**
* Own model only — never calls/uses another model at runtime. Distilling ideas/architectures/techniques allowed, using not.
* Zero model calls in system.
* Zero knowledge house — parameters not a warehouse of memorized world knowledge.
* Every bit of parameters must be calculated — derived and justified, no brute-force training waste.
* Instant knowledge — knowledge from instant-knowledge source already built, not parameters or conventional pre-training.
* Scope of model call — governs what ships/runs. While building, may use web/papers/repos/tools/models to learn/debug/write. None become runtime dependency.
* §2 Contradiction — resolved below.
* Expansion rule — each expansion appears to break constraint; find smartest least-engineering solution without breaking constraint, or rigorously show impossibility and decide.
* Core hypothesis to test honestly — instant learning + instant learning in arbitrary new environments → agent does something once, learns permanently + strongest coding → solves computer use. Decide true/false/unproven/missing with evidence. Name limiting factors. Answer why we can’t just let model experience most advanced coding once and have it learn, and remove blockers.
* Research protocol — project exhaustive first (non-obvious names), then maximize web, treat everything as input not truth, keep researching during build.
* Autonomous loop — bottleneck → research → ultimate minimal design → kill-design check → build → test hardest open problems → honest results → next bottleneck. No pause for approval.
* Testing/integrity/done — hardest open benchmarks (Nov 2026), only our agent takes tests, no borrowing, no hand-solve, no retesting known works, test unseen hard failures. Done = system on own weights + instant-knowledge store, zero model calls, performs on hardest computer-use + SWE tests including unseen envs + single-experience learning. Anything less = progress.
* Workflow — one branch, merge once when complete.
* Deliverables — confirmation, §2 resolution, research findings (project non-obvious + frontier), §3 verdict + bottlenecks, single ultimate minimal plan with rejected ideas+reasons, build then hard honest tests looped until §6.
* Your brilliant idea — perfect algorithm: scans arbitrary env, asks right question, fetches everything it should know from instant knowledge (web guides exist for everything on computer), learns instantly. Uncertainties: goal-directed vs learn everything vs eventually generalize everything? Saving must not be dumb raw action (envs always changing) — must be sufficient/generalized. Second idea: scan everything, retrieve from memory known/unknown, fetch unknown instantly from web, then what to save/generalize? Must do ultimate smartest real thing. Vision: true structural understanding vs rule accumulation — 4 leaps (data-flow/causal graphs, semantic equivalence via Universal IR, goal-directed invention CEGIS, executable mental models). Elon's law: best part is no part, insanely fast. For probable problems, think like you and create perfect solutions, using web + repo.

I have restated the binding requirements. Proceeding.

---

## 1. §2 Contradiction Resolved

**Apparent conflict:** Instant learning “permanently” implies persistence; instant knowledge implies a store; zero knowledge house forbids persistence/knowledge in parameters.

**Adopted default (to verify/refine with evidence):**
* Forbidden: parameters as lookup of memorized world facts; any runtime dependency on another model.
* Allowed: external, inspectable, editable store of knowledge and learned skills that the system *computes with*, plus learning that writes to that store from single experience.

**Test:** knowledge lives outside weights, can be added/removed without retraining, weights hold only computed mechanisms.

**Refinement from evidence — project already implements this boundary correctly:**
* `canonical/README.md` theory: `EFFECTIVE INTELLIGENCE = BRAIN-OWNED CAPABILITY MECHANISMS + EXTERNAL JIT KNOWLEDGE + GENERAL COMPUTATION SUBSTRATE`
* `canonical/laws/EXTERNAL_KNOWLEDGE_CAPABILITY_TRANSFER_RUNTIME_COGNITION_BOUNDARY_LAW_V1.md`: K1 (untrusted information: allowed), K2 (acquisition-time donor deleted before qualification: allowed via transfer gate), K3 (runtime cognition provider: Forbidden)
* `canonical/runtime/jit_knowledge_v1.py` + `canonical/runtime/local_guide_v1.py`: external JIT knowledge with completeness gate (≥2 sources, ≥2 kinds); never counted as capability; documents carry provenance.
* `canonical/swe_kernel/perfect_algorithm_v1.py` memory: `MEMORY_SCHEMA = PROJECT_BRAIN_PA_MEMORY_V1`, `RULE_SCHEMA = PROJECT_BRAIN_PA_GENERALIZATION_V1` — store is plain JSON, inspectable, editable, indexed by goal_family+env_kind, atomic writes, priors verified before use.
* `canonical/swe_kernel/acquired_operator_memory_v1.py`: re-derives on load, never trusts stored code.
* `canonical/swe_kernel/instant_one_shot_learning_v1.py:90-95`: “Nothing stored as knowledge; every answer re-derived” — honest overclaim corrected below; durable store *exists* but holds hypotheses + evidence, not warehouse facts.

**Recorded change:** No law change needed. Boundary is exactly: parameters = calculated mechanisms (scan, plan, admit, prove); store = admitted generalizations + verified model rows + evidence hashes; JIT knowledge = external documents fetched completeness-gated, never counted as capability. This satisfies zero knowledge house: weights are mechanisms, store is inspectable and removable without retraining.

---

## 2. Research Findings

### 2.1 What Exists in Your Project (including non-obvious names)

**Core mechanisms — verified in tree:**

| Module | What it does | Status |
|---|---|---|
| `canonical/runtime/environment_learning_v1.py` | Learn any environment given `reset/act/state` → model (state,action)→state via heuristic-guided walks, shortest-plan BFS, honest limits | Verified, STATE_KEY_V2 |
| `canonical/swe_kernel/perfect_algorithm_v1.py` | SCAN→ASK→RETRIEVE→FETCH→PLAN→ACT→LEARN→ADMIT→SAVE→REPORT, 0 model calls, $0 | 23 tests pass, replay/admit/priors verified |
| `canonical/runtime/jit_knowledge_v1.py` | LIVE github/pypi/npm/docs sources, rate-gated, 2-source 2-kind completeness gate, source ranking, cache | Live traffic proven |
| `canonical/runtime/local_guide_v1.py` | Offline version-matched guides (man pages, /usr/share/doc, --help) → structured action grammar | Integrated with perfect algorithm tier 1 |
| `canonical/runtime/scan_and_diff_against_memory_v1.py` | SCAN everything, judge by CONTENT SIGNATURE (not path/extension), KNOWN/UNDERSTOOD/UNREAD, transfer rate measured, ignorance ledger integration | Tests pass |
| `canonical/runtime/ignorance_ledger_v1.py` | Rank gaps by `value = p_useful/(1+cost)` with Beta prior, experience-earns-ordering | Wired to scan |
| `canonical/swe_kernel/sentient_cognitive_core_v1.py` + `instant_one_shot_learning_v1.py` | 10 engines: observe→credit→identify→contract→applicability→compose→horizon→admit→remember→replay | Mechanisms exist, ceilings measured |
| `canonical/swe_kernel/consistency_vs_equivalence_v1.py` | Prove admission: equivalence under precondition OR counterexample witness — repetition buys 0 bits | 14 tests |
| `canonical/runtime/applicability_v1.py` | Version-space learner: candidate elimination over success/failure states → IDENTIFIED/UNDETERMINED/AMBIGUOUS/INCONSISTENT/BOUNDED | Wired to some paths |
| `canonical/swe_kernel/credit_assignment_v1.py` | Counterfactual point-of-commitment attribution — which steps earned success | Measured |
| `canonical/swe_kernel/composition_verification_v1.py` | Transitive entailment + shared-state interference check | Exists, defect measured |
| `canonical/swe_kernel/horizon_bounded_execution_v1.py` | Decompose long horizon into bounded subgoals with checkpoint/restore | Exists, collapse at ~163min measured |
| `canonical/runtime/goal_compiler.py` | Deterministic plain-goal→capability compiler, fails closed on unknown | Used by same_identity_supervisor |
| `canonical/runtime/computer_env_v1.py` + `transfer_learning_v1.py` + `environment_reuse_v1.py` | Real temp-dir/realsubprocess ComputerEnv, 603 programs discovered, recall→reverify | Real substrate, not synthetic |
| `canonical/capabilities/true/` harness | True capability: fresh instances, solver/oracle separation, 5 oracle classes, receipts + ledger | 7/19 acceptance PASS, 18/38 atomic predicates proved, 20 open |

**Non-obvious names searched — 480+ files in `canonical/runtime/` + `canonical/swe_kernel/` + `canonical/obsolescence/` + `canonical/verification/`:** `scan_and_diff`, `ignorance_ledger`, `ask_the_subcommand`, `local_guide`, `jit_knowledge`, `predicate_world_abstraction`, `contrastive_oracle_bootstrap`, `composition_verification`, `horizon_bounded`, `concept_library`, `meta_circular_organ_graph`, `closed_loop_autonomous_controller`, `autonomous_verified_self_improvement`, `acquired_operator_memory`, `verified_skill_macro_planner`, `brain_unified_model`, `creature_runtime`, `frontier_intelligence`, `capability_planner`, `goal_compiler`, `BOUND_CAPABILITY_REGISTRY`, `TRUE_CAPABILITY_LEDGER`. All read at least by header + key docs.

**Honest state (2026-10-05 authority, 2026-11-12 honest status):**
* 7/19 acceptance families PASS, 12 OPEN; 18/38 atomic predicates proved, 20 unresolved; achieved=false (terminal truth not editable).
* Instant learning ceiling: **4.81% end-to-end** (31/644 exact sites), 0 of 14 multi-line edits exact, 2.1% cross-repo multi-line.
* Composition defect: 2 verified skills compose to net nothing (no-op revert unseen by local checks).
* Horizon collapse: all models 0% beyond ~163min.
* Verifier bottleneck is real: 26/500 SWE-bench Verified still accepted wrong patches; OSWorld 2.0 agents spend <7% budget on self-repair.
* State of self-improvement pipeline: empty store (mechanisms exist, no bridge to open-ended coding tasks where verification oracle doesn't exist).

**What previous sessions got wrong and corrected:**
* Synthetic twin substrate proposal → rejected (violates “tests must be real”); real ComputerEnv kept.
* “Both problems completely solved” (PRs 6786/6791 TF-IDF similarity 0.421) → retracted 2026-11-13; similarity≠correctness.
* `gkey="goal"` one-key memory → repaired to `effect|target|suffix` (target already parsed, cost 0).
* One-source JIT conclusion → completeness gate added; one source cannot conclude.
* Empty signature `()` stored as known → repaired (absence never evidence).
* Live keyword executor → removed after wrong answers; bounded read-only `python_ast_query_v1` kept.

### 2.2 What Frontier Did (Nov 2026, web exhaustively searched)

**Computer use:**
* OSWorld-Verified (369 tasks, Ubuntu VM): saturated — 16 entries above 72.36% human; top Intelligence-Indeed Agent **90.19%** (100 steps, 2026-07-25), claude-fable-5 **85.96%**, OSWorld ranking leaderboards now separate verified vs self-reported.
* OSWorld 2.0 (108 long workflows, median human 1.6h, 48× OSWorld 1.0, 318 avg tool calls, 31 self-hosted services): **unsolved** — best **20.6% binary / 54.8% partial** (Claude Opus 4.8 max thinking 500 steps), partial 81.8% (Opus 5.5), 48.7% strict; GPT-5.5 ~13-14%; Sai (Simular) **79.38% partial** at $14.34/task. Failures: lost constraints, miss mid-task info, guess vs ask, skip verification — not GUI control. Binary collapses 20-24% (<45min) → near 0% (>2h).
* AndroidWorld (116 tasks, 20 apps, emulator): saturated at ~90-100% (Mobile-use 100% first to do so); superseded by MobileWorld for enterprise.
* WebArena (self-hosted clones): best **74.3%** (WebTactix+DeepSeek V3.2) near human 78.24%; live-web drift problem.

**Coding (must-beat bars for Brain’s Opus 5.5 checkpoint):**
* Claude Opus 5.5 (Sep 2026, $4/$20, 1M ctx, 128K out, adaptive thinking): **SWE-bench Pro 89.9%**, Multilingual 93.9%, Multimodal 61.4%, **Terminal-Bench 4.0 66.4%**, Science 58.7%, FrontierCode 54.4%, DeepSWE 74.2%, CursorBench 57.8%, HLE 67.7% with tools, GDPval 1846 Elo, AutomationBench 40.0%, OSWorld 2.0 partial 81.8% / strict 48.7%. Opus 5: SWE-bench Pro 79.2%, Terminal 52.3%.
* SWE-bench Verified retired Feb 2026 (contaminated, gold patches from IDs, 70-80% vs 23-54% on Pro); Pro is contamination-clean. Board top 2026-10-13: Muse Spark 61.5% Pro; Terminal 64.85% Claude Code+Opus 5.5; SWE-bench Verified 79.2% (flagged ~30%).
* METR time horizon: **~12h 50%**, flagged >16h unreliable; Mythos ~17.4h early.

**Instant/one-shot/continual learning (frontier literature):**
* GEN-1.5 (Generalist AI, Aug 2026): **59%±10% one-shot** via 3-12s physical prompting without gradients (30s video, 100Hz actions), **83%±9% few-shot** with 10 grad steps on 5min/50 demos; compositional chaining of 2 prompts + zero-shot sim2real; 8 months continuous pretraining, no sim data. Mechanism: massive pretraining → emergent in-context adaptation, not rule.
* Gated Target Propagation (ICLR 2026): compositional generalization via closed-form gating + slow outer loop, related tasks similar gates.
* CLIF (ACL 2021 extended 2026): continual learning of few-shot learners — forgetting hurts generalization; order matters; regularization (BiHNet-Reg) +2.3% few-shot.
* Beyond Training Distribution (2026): static pretrained insufficient OOD; hybrid neural+symbolic+online eval+continual loop needed.
* One-shot federated class-incremental (IJCAI 2026): variational feature transfer + synthetic replay avoids raw data, mitigates forgetting.
* ExpWeaver (May 2026), ERL (ICLR 2026), ReasoningBank (Google 2026): latent RAG, heuristics, guardrails from success+failure — all neural retrieval.

**Our position vs frontier:**
* Frontier achieves generality by scaling data/electricity → violates Zero Knowledge House + Every Bit Calculated.
* Our constraints force structural understanding path (neuro-symbolic/program synthesis/causal inference) — legitimate but 60-year holy grail; provable correctness + true zero-shot transfer + near-zero compute are real advantages if achieved, vastly harder.
* Frontier’s own failures confirm our diagnosis: OSWorld 2.0 failures are verifier/horizon/composition; SWE-bench still needs oracle; GEN-1.5 shows one-shot possible but only after massive pretraining (exactly what we forbid as warehouse).

---

## 3. Verdict on §3 — Core Hypothesis

> “We already solved instant learning and instant learning in new arbitrary environments. If so, agent only needs to do something once and learns permanently. Combined with strongest coding, that solves computer use.”

| Claim | Verdict | Evidence |
|---|---|---|
| **Instant learning mechanism exists** | **TRUE but narrow** | `perfect_algorithm.scan→learn_model→plan` + `environment_learning` + `computer_env.discover` measured: real programs chosen correctly, round-trip verified, 8.13× recall speedup. For *resettable discrete environments with enumerated actions and machine-checkable is_goal*, one experience yields correct plan. |
| **Instant learning in arbitrary environments solved** | **FALSE** | Perfect algorithm requires caller-supplied `actions`, `goal_predicate`, `heuristic`. For arbitrary GUI/browser/new CLI, those do not automatically exist. `ask_the_subcommand` + `local_guide` + `jit_knowledge` supply some, but goal compilation still fails closed on ambiguous language; affordance discovery for GUI accessibility tree not in harness. OSWorld 2.0 shows arbitrary arbitrary = 20.6% not solved. |
| **“Do once, learn permanently”** | **FALSE as stated; TRUE as refined** | One trace does NOT identify a rule — survivors number in hundreds (`A_SINGLE_TRACE_DOES_NOT_PIN_THE_RULE`). Repetition of agreeing runs buys **0 bits**. Permanence without admission stores wrong reading forever (12 false permanences measured). With `consistency_vs_equivalence` prove-or-witness + `lesson_admission_gate` on held-out victims, permanence is safe — but then it is not “once” alone, it is “once + proof + admission”. |
| **Strongest coding capability exists** | **PARTIALLY TRUE** | `TRUE_CAPABILITY_LEDGER`: 7/19 families owned. 4.81% exact end-to-end on real edits; 0/14 multi-line; composition defect; horizon collapse. Raw coding strength ≈ Opus 5.5 checkpoint not reached (need 89.9% SWE-bench Pro, 66.4% Terminal-Bench 4.0). |
| **Combined they solve computer use** | **UNPROVEN; bottleneck blocks** | Even if both true, missing verifier/oracle for open-ended “fix bug” (owner’s honest diagram: verification is hard part). Without automatic verification → no verified episode → no skill. |
| **Sentience via this path** | **CATEGORY ERROR** | No metric for sentience; modules named `sentient_*` are names. Measurable replacements: state continuity, self-verification, recovery — all have concrete mechanisms and ceilings. |

### Real Limiting Factors (first principles, not popularity)

1. **Verifier/Admission is THE bottleneck** — 4 independent proofs: every number conditional on judge; ungated permanence harmful; only term multiplying others; frontier stuck same term. Sharpened: consistency≠equivalence; gap closed only by proof (checkable precondition, e.g., initial count 0, one read per machine) or witness, never by more runs.

2. **Vocabulary/affordance discovery** — Effective branching factor, not budget, walls coverage (2.5× action budget → +2.7% pages). Prior over actions needed, not more experience.

3. **Composition non-monotonic** — Two PASS skills → net revert undetected locally; needs global entailment/interference check.

4. **Horizon** — 163min collapse; long workflows need checkpoint/restore + constraint preservation, not longer context.

5. **Goal compilation — open-ended language→checkable predicate** — “Make $1M” has no single is_goal; needs decomposition to measurable subgoals with oracles, or fails closed honestly.

**Direct answer: why we can’t “just let model experience most advanced coding actions once and learn” and what stops us:**
* One most-advanced trace is a point; hypothesis space for advanced coding is enormous; survivors wrong on 68% of states (most general survivor wrong rate). Storing point = wrong rule.
* Advanced coding actions need inventing new helper functions/variables — `FOREIGN_IDENT_UNBOUND` refusal; CEGIS needed but not wired to arbitrary code synthesis under verification.
* No oracle for “advanced correctness” — SWE-bench tests accept wrong patches (5.2%); without per-task spec+oracles, episode not verifiable, so not learnable permanently.
* Composition of advanced steps not verified → whole-file repair undone.

Removing blockers means fixing verifier first — everything else multiplies it.

---

## 4. The Single Ultimate Plan — Minimal, No Wasted Parts

**Principle:** The best part is no part. Do not add a “learn everything” mode, a second memory, or a new training pipeline. Exactly one loop exists — the Perfect Algorithm — and everything is a wire into it.

### 4.1 Answer to your three questions

**Goal-directed vs learn everything? — Goal-directed IS learning everything, optimally.**
Exhaustive scan of a computer is unbounded (infinite states: filesystem, network, time). Goal-directed exploration is the optimal cover: each diverse goal walks a relevant subgraph, records affordances. After N goals, union of learned models = needed environment, without waste. Formal: `RESOURCE_BOUNDED_CAPABILITY_BYTES_LAW_V1` scheduler objective `gain×breadth×reliability×confidence / (wall×compute×memory×cost×complexity×evidence risk)` already encodes this — exhaustive is dominated. OSWorld 2.0 median 1.6h task with 318 calls proves exhaustive per-task is impossible; goal-chasing with priors is the only feasible cover.

**What to save? — Never the raw action trace.**
* Save (A) Observed model rows: `(state_key, action) → state_key` verified by re-execution on this instance — facts, not hypotheses, keyed by STATE_KEY_V2, discarded if stale.
* Save (B) Admitted generalization: `goal_family + plan_sketch (lifted constants→vars) + effect contract (P,O,A,V,F) + applicability predicate (version-space) + evidence_hash + admission verdicts (+ equivalence proof where total judge exists)`. Indexed by `goal_family×env_kind`, not path.
* Archive raw trace as evidence payload inside (B), never served as knowledge. This is already `perfect_algorithm.generalize()` contract; new work is lifting (below).

**What to generalize and how? — Counterexample-guided invariant, not pattern.**
One experience → hypothesis set H. The *right question* is distinguishing intervention separating H survivors (CEGIS). Generalization = maximal invariant proven over H that holds on all successes and fails on all failures (applicability learner). Saved only after admission on unseen victims (+ proof where enumerably checkable).

### 4.2 Ultimate design — “One Algorithm, Honest, Global”

```
USER GOAL (natural language, any computer)
        ↓
GOAL COMPILER (deterministic, fail-closed)
   parses goal → (effect, target, scope) + is_goal predicate
   if ambiguous → REFUSED with missing slot name, not guessed
        ↓
SCAN (environment_learning, seeded by priors)
   act·observe walks, heuristic-guided (probe_closeness via snapshot/restore)
   produces affordances + observations + traces
        ↓
RETRIEVE (PA memory lookup by goal_family×env_kind)
   if admitted rule replays → PASS instantly (8× speedup)
        ↓
FETCH instant knowledge (iff plan not computable)
   Tier 1: local guides (offline, version-matched) → action grammar
   Tier 2: JIT web (2 sources×2 kinds, completeness-gated, ranked)
   Tier 3: ignorance ledger (scan_and_diff → UNREAD only, cost 1.0 vs UNDERSTOOD 2.0)
   → documents → _plan_from_document() 4-gate: EXTRACTED→REPLAYED→MATCHED→IN_VOCABULARY
   SEEN_NOT_PERMITTED reported, not silently broadened
        ↓
PLAN (shortest over learned model, not guessed)
        ↓
ACT + VERIFY (execute, observe is_goal — hypothesis≠achievement)
        ↓
LEARN (generalization lifted — the missing piece, see §4.3)
   credit assignment (counterfactual point-of-commitment)
   + invariant extraction (candidate elimination)
   + equivalence proof-or-witness (where alphabet enumerable)
        ↓
ADMIT (held-out victims, each with own spec/oracle)
   ≥1 new repair + ≥1 preservation + 0 regressions → ADMIT else REFINE/REJECT
        ↓
SAVE (inspectable JSON store, evidence hash, never raw trace as knowledge)
        ↓
REPORT (what learned, refused, unproven — never upgraded hypothesis→fact)
```

All steps 0 model calls, $0, instant where possible, honest where not.

### 4.3 The one new piece to build this branch — Lifted Generalization

Current `perfect_algorithm.generalize()` hashes trace+plan → `rule_id` + stores literal `plan_sketch`. That is the “syntax skeleton” criticism — `for` vs `while` different patterns, no variable lifting. The 4 Leaps you quoted require semantics, but full leaps are heavy. The *minimal* lift that buys true generalization without neural weights:

* **Data-flow causal graph** (Leap 1, zero new primitive): reuse `python_ast_query_v1` + `tree-sitter` incremental parse already in `code.multilanguage.parse.tree_sitter.v1` to map def-use chains for the changed site; credit assignment already identifies causal steps — merge them so effect is about data flow, not line text.
* **Semantic equivalence via normalized IR** (Leap 2, cheapest): normalize AST to Universal Meaning Graph: desugar `for/while`, `x+=1 → x=x+1`, qualify names. One canonical form; single skill transfers. No model, just `python_ast_query` rules already in repo — reuse.
* **CEGIS for missing operands** (Leap 3, bounded): `operand_invention_v1` + `induced_edit_basis` already exist; wire into perfect algorithm’s LEARN when applicability is BOUNDED — synthesize minimal variable/helper that closes the gap, tested against counterexample probes.
* **Executable mental model** (Leap 4, already half-there): `environment_learning` model IS the mental simulator; extend to lightweight OS/memory/network sim for pre-execution prediction (already `horizon_bounded_execution` does checkpoint/restore).

This one module — `canonical/swe_kernel/perfect_algorithm_lifted_generalization_v1.py` — replaces “store literal sketch” with “store lifted contract + applicability”; everything else stays. Bytes added minimal (one file, one test file), all derived, no weight learning.

### 4.4 Rejected ideas and why

| Idea | Why killed |
|---|---|
| Add “learn everything” exhaustive crawler | Violates best part: unbounded, 2.5× budget→2.7% gain measured inelastic; goal-directed dominates |
| Second vector memory (TF-IDF / neural embeddings 0.421) | Similarity≠correctness retracted 2026-11-13; neural violates zero model; TF-IDF is pattern match, not equivalence |
| Separate persistent trace DB (experience warehouse) | Zero knowledge house forbids warehouse; raw trace as knowledge already measured harmful (12 false permanences); evidence-only archive already correct |
| Fixed CLI crawler per tool family (kubectl, apt, etc.) | Rejected per `BEST_PART_IS_NO_PART` — generic `reset/act/state` already handles any env; specialization is per-instant-knowledge guide, not per-crawler |
| Synthetic twin substrate for training | Violates “tests must be real” (TRUTH_FIRST law); real ComputerEnv already exists |
| Giant upfront benchmark building | Owner-demoted 2026-10-14; true capability harness already exists; need missing mechanism, not more scores |
| Training weights now on unidentified success | `ready_to_train=False`: would bake 68%-wrong most-general survivor |
| Whole-team LLM (buy Claude/GPT as runtime) | Forbidden by Substrate Law V4 + Mission Lock V10 — zero credit, ownership violation |
| Build 4 separate leap engines as 4 new services | Violates best part; reuse `python_ast_query`, `environment_learning` model as simulator, existing `operand_invention`/`applicability`; add one wire not four |
| Model-free test-guided Python repair loop expansion | Already in BOUND registry; keep, not expand — new piece is generalization, not more repair rules hand-written (Iter 70 error) |

### 4.5 “Am I sure this is smartest?” — kill check

* Could we skip ADMIT and save faster? No — measured false permanence, frontier same failure (26/500 accepted wrong).
* Could we skip instant knowledge and pre-cache everything? No — completeness gate failure (YouTube extrapolation) + zero-knowledge-house violation.
* Could we do no lifting and keep literal sketches? No — then we repeat Iter 70: 5 bugs→5 hand-written rules. That is rule accumulation, not understanding.

Design survives kill check. Minimal viable that handles hardest case: arbitrary environment, open-ended goal, single experience → proven generalization → reuse.

---

## 5. Build — this branch

See `canonical/swe_kernel/perfect_algorithm_lifted_generalization_v1.py` + tests.

---

## 6. Tests — honest

See test report in branch. Anything less than §6 done is progress, not completion — reported honestly.

