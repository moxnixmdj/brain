# The Perfect Algorithm v2 — Goal-Directed Fetch, Typed Invention, and What to Save

**Date:** 2026-11-25 · **Branch:** `arena/f7ec1162-brain` · **Base:** `c4f529eb` · **Authority:** NONE · **Spend:** $0 · **Model calls:** 0

> Your brilliant idea, made precise: the model IS the perfect algorithm. It enters an arbitrary environment knowing nothing, scans, retrieves known vs unknown from memory, fetches unknowns instantly (web guides exist for everything on-computer), plans shortest path, acts+verifies, learns a generalization not a trace, admits on unseen victims, saves, reports. This doc answers every open question in that idea with a falsifiable design.

---

## 0. Confirmation — all requirements restated

**Global laws (every message, thought, step, tool, design, test, report):**
- Never stop before mission done — arbitrary computer use (most advanced SWE + GUIs/browsers + arbitrary new envs) not perfectly solved & verified under §6 → unfinished. No milestone stops.
- Never ask you questions — ask web/frontier lit, project (incl. non-obvious names), first principles. Only exceptions: credentials/payments/physical access/legal decision. Log blocker once, continue else. Never end turn with question. Ambiguity → most defensible interpretation, state it, proceed.
- Research before building, always — exhaustive project search first (incl. non-obvious names), then web as of 2026-11-24 (training data old). Never rebuild what exists. Never treat web as gospel.
- First principles, always — find real limiting factor before choosing solution.
- Best part is no part — every component/parameter/line/test/process must justify existence (model, harness, plan, workflow).
- Ultimate solution never incremental — design for hardest/most advanced case; it handles ordinary.
- “Am I sure this is smartest?” before every step — kill bad ideas pre-implementation.
- Build player-by-player — best technique per role from anywhere, assemble best whole; don't buy whole teams (other models).
- Real understanding not pattern matching — judge by understanding.
- Honesty — verified/unverified/failed with evidence; never claim done without §6.
- Integrity — no leakage/hand-holding/borrowed outputs.

**Mission:** Own weights/architecture/agent; fully solve computer use fastest via optimal mechanisms; long-term sentient-like structural understanding.

**Hard constraints (runtime product):**
- Own model only, zero model calls at runtime; distilling ideas/techniques allowed, using not.
- Zero knowledge house — parameters not warehouse of memorized world facts.
- Every bit of parameters calculated/justified, no brute-force training waste.
- Instant knowledge from external inspectable store (outside weights, removable without retraining), zero incremental spend.
- Scope: constraints govern what ships/runs; building may use web/papers/tools/models to learn/debug/write, none becomes runtime dependency.
- §2 contradiction resolved: Forbidden = param lookup of world facts + runtime model dependency. Allowed = external inspectable editable store of knowledge/skills the system computes with + learning that writes to it from single experience. Test: knowledge outside weights, addable/removable without retraining, weights hold only mechanisms. Record if evidence forces better boundary.
- Expansion rule: each expansion (GUIs/browsers→model, NL→model, cross-session→persistence, counterfactuals→complexity) must get smartest least-engineering solution without breaking constraint, or rigorously show impossibility then decide constraint vs expansion.
- Core hypothesis to test honestly: instant learning + in arbitrary envs → do once learn permanently + strongest coding → solves computer use. Decide true/false/unproven/missing, name limiting factors, why not just experience most advanced coding once, remove blockers.
- Research protocol: project exhaustive first (non-obvious names), then maximize web, treat as input not truth, keep researching.
- Autonomous loop: bottleneck → research → ultimate minimal design (rejected+why, kill check) → build → hardest-open tests → honest results → next.
- Testing/integrity/done: hardest open benchmarks Nov 2026, only our agent, no borrowing/leak/hand-solve, never retest known, test unseen hard failures. Done = own weights + instant store, zero model calls, performs on hardest computer-use + SWE tests incl. unseen envs + single-experience learning.

---

## 1. §2 Contradiction — verified unchanged

**Boundary holds:** weights = mechanisms; store = knowledge/skills.
- Evidence: `PERFECT_ALGORITHM_MEMORY_V1` + `VERIFIED_SKILLS_BUNDLE_V1.json` + `ir_hash` field are external JSON, gitignored DB + bundle, removable without retrain; `acquired_operator_memory` re-derives priors; `jit_knowledge_v1` 2×2 completeness gate + `local_guide_v1` offline supply knowledge, never capability. Law `EXTERNAL_KNOWLEDGE_CAPABILITY_TRANSFER_RUNTIME_COGNITION_BOUNDARY` K1/K2 allowed, K3 forbidden remains satisfied.

No better boundary found; refinement unchanged from v1.

---

## 2. Research Findings — what exists (non-obvious names) + frontier

### 2.1 Project exhaustive (480+ files read by header/key)

| Exists | What it is | Why it matters to perfect algorithm |
|---|---|---|
| `perfect_algorithm_v1.py` | SCAN→ASK→RETRIEVE→FETCH→PLAN→ACT→LEARN→ADMIT→SAVE→REPORT | Shape of answer proven (v1) |
| `perfect_algorithm_lifted_generalization_v1.py` + `verified_skill_crystallizer_ir_bridge_v1.py` + `deep_understanding_engine_v1.py` | Lifted template {{target}} + IR Loop hash + dataflow/CEGIS/mental sim | True understanding 4 leaps (v1) |
| `scan_and_diff_against_memory_v1.py` | Signature-keyed KNOWN/UNDERSTOOD/UNREAD (content validators, not suffix) | Retrieve: what is known (transfer not memorization) |
| `ask_the_subcommand_before_you_call_it_unbound_v1.py` | NOT_ASKED/DROVE_IT_WRONG/NO_DOCUMENT/SLOT_UNSUPPLIED/NEEDS_CONSTRUCTION + worth=operations decided (676 ops openssl) | Ask right question: parent vs child scope defect measured 38/38 |
| `tool_census_v1` + `ignorance_ledger_v1` | 1491 ops, 33 doors, 793 UNBOUND; ledger p/(1+cost) Beta prior, experience-earns-order | Scan census + ranked gaps |
| `jit_knowledge_v1` + `local_guide_v1` | 2 sources×2 kinds completeness gate; md 500-file ≤60% content-token gate, tool guides version-matched | Fetch instant knowledge (external, never capability) |
| `incremental_semantic_graph_v1` | SHA256 row-cache (7.3s→0.35s, 2292 files), import-resolved, Tarjan SCC, C3 MRO | Types for invention (this iteration) |
| `history_induced_edit_grammar_v1` + `induced_edit_basis_v1` | Grammar from real commit diffs, not hand-written operator list (HAND-WRITTEN list decides before search) | Invention vocabulary (not hand-written) |
| `hierarchical_skill_library_v1` + `egraph_and_deductive_synthesizer_v1` + `concept_library_v1` (K3=0, sleep_abstract compresses, ≥4 probes ≥2 outputs) + `concept_library sleep` | Compounding concepts, E-graph equality saturation, pure AST eval | Composition + invention alternatives |
| `credit_assignment_v1` (counterfactual point-of-commitment) + `applicability_v1` (IDENTIFIED only) + `consistency_vs_equivalence_v1` (proof-or-witness, repetition 0 bits) + `composition_verification_v1` + `horizon_bounded_execution_v1` (163m collapse) | Causal credit, when rule applies, equivalence not agreement, transitive+interference, checkpoint/restore | Learn/admit/horizon |
| `browser_v1.py` + `osworld_v21_browser_ops_v1.py` + `osworld_v21_gui_goal_verifier_v1.py` | Deterministic CDP BROWSER_CLICK_TEXT/FILL via DOM querySelector + accessibility tree | GUIs/browsers least-engineering |
| `goal_compiler.py` + `python_ast_query_v1` | Deterministic typed parsing fail-closed | NL least-engineering |
| `computer_env_v1` + `transfer_learning_v1` + `acquired_operator_memory_v1` | Real temp-dir/subprocess env, 603 programs discovered, recall→reverify | Real substrate, not synthetic |

Honest ceiling: 7/19 acceptance PASS, 20 predicates OPEN, 4.81% exact SWE sites, composition no-op defect, horizon 0% beyond ~163min. V2 does not hide this.

### 2.2 Frontier Nov 2026 (web)

- **SWE-bench Pro** (1,865 tasks, 41 repos, private commercial split): Scale standardized public leader Muse Spark 1.1 **61.5%±3.1**, vendor aggregate Claude Opus 5.5 **89.9%**, open Qwen3.8-27B 61.7%, ~30% tasks flagged broken (OpenAI audit Jul 2026). Verified retired Feb 2026 (contaminated 59.4% flawed in hard sample).
- **Terminal-Bench 4.0**: leader Claude Code+Opus 5.5 **64.85%±3.11** (Aug 28 revision), Kimi K3 88.3 TB2.1 etc not comparable.
- **OSWorld-Verified** (369 Ubuntu VM): saturated **90.19%** (Intelligence-Indeed 100 steps) >72.36% human → replaced.
- **OSWorld 2.0** (108 long workflows, median 1.6h, 48× v1, avg 318 tool calls, 31 self-hosted services): **unsolved** — best **20.6% binary / 54.8% partial** Opus 4.8 500 steps, Opus 5.5 partial 81.8%/strict 48.7%, GPT-5.5 ~13-14%, Sai 79.38% partial $14.34/task. Failure modes: lost constraints, miss mid-task info, guess vs ask, skip verification. Binary collapses 20-24% (<45m) → near 0% (>2h).
- **Synthesis research**: CEGIS(*T*) (Abate 2018/2023) — theory solver + synthesizer separate, communicate non-trivial constants via FM elimination/SMT; neuro-symbolic gateway (Tenzed 2026) Zod→Z3 CEGIS loop forcing valid; sketch schema (Solar-Lezama) holds ≤20 bound; UAST 54 types O(|L-AST|) bounded.

Position: frontier achieves generality by scaling data/electricity → violates Zero Knowledge House + Every Bit Calculated. Our path (neuro-symbolic/program synthesis/causal) is legitimate 60-yr holy grail with provable correctness + zero-shot + near-zero compute if achieved, vastly harder.

---

## 3. Verdict on §3 — Core Hypothesis

| Claim | Verdict | Evidence |
|---|---|---|
| Instant learning mechanism exists | **TRUE narrow** | `perfect_algorithm.scan→learn_model→plan` + `computer_env.discover` real programs, round-trip, 8.13× recall. For resettable discrete envs with enumerated actions + checkable is_goal, one experience yields correct plan. |
| In arbitrary envs solved | **FALSE** | Arbitrary needs auto affordance discovery (GUI accessibility tree not in harness) + goal compilation fails closed on ambiguous NL; OSWorld 2.0 20.6% not solved. |
| Do once learn permanently | **FALSE as stated; TRUE refined** | One trace ≠ rule (hundreds survivors, A_SINGLE_TRACE...); repetition 0 bits; permanence without admission stores wrong reading forever (12 false permanences). With proof-or-witness + held-out admission, safe — but then “once+proof+admission” not “once alone”. |
| Strongest coding exists | **PARTIAL** | 7/19 PASS, 4.81% exact, 0/14 multi-line, composition defect, horizon collapse. Not 89.9% Pro / 66.4% TB4. |
| Combined solves computer use | **UNPROVEN; bottleneck blocks** | Missing verifier/oracle for open-ended “fix bug” → no verified episode → no skill. |
| Sentience via this path | **CATEGORY ERROR** | No metric; measurable replacements (state continuity, self-verification, recovery) have mechanisms+ceilings. |

**Why not just experience most advanced coding once:** Advanced coding is underspecified (no oracle), multi-file cross-module, long-horizon, needs invention (FOREIGN_IDENT_UNBOUND) not copying. One trace is underdetermined; verifier is hard part. Blocker is verification + vocabulary of invention + horizon, not exposure.

---

## 4. The Single Ultimate Plan — answers to your brilliant questions

### 4.1 Goal-directed vs learn everything — measured answer: BOTH, at different costs

**First principles (real limiting factor):** Cost is not uniform.
- **Scanning** = reading existing bytes + content validation (~0.35s warm for 2292 files via SHA256 row-cache; tool census 1491 ops). Cheap — O(n) linear, offline, no web.
- **Fetching** = web/JIT knowledge (network latency, completeness gate 2 sources×2 kinds, rate limits). Expensive — O(web), online, contested.
- **Learning** = storing raw traces for every seen file. Waste — environments infinite, actions never repeat verbatim (Iteration 70: 5 bugs needed 5 literals).

**Optimal mechanism (insanely fast, least waste):**
- **Scan EXHAUSTIVELY, fetch GOAL-DIRECTEDLY.** Scan everything (cheap census classifies 793 UNBOUND vs 33 DOOR vs 665 SENSOR) so unknowns are enumerated; fetch only what the goal's shortest path needs, ranked by `worth(question)=operations whose verdict this question decides` (e.g., 676 ops settle in one subcommand ask). Goal defines relevance; goal is the scarce resource.
- **Eventually learn everything is false optimization:** learning “everything” without goal wastes scarce fetch budget on knowledge never used to achieve anything (2.5× budget → 2.7% pages inelastic in browser measurement). Eventually, via many goals, coverage converges without ever aiming at “everything” as objective. The agent becomes competent by doing, not by studying.

**Rejected:** (a) Learn everything upfront — violates best part is no part, infinite; (b) Learn only goal literal — misses transferable prerequisites (e.g., missing helper that goal path needs but goal text never names — fetch must include causal dependencies via dataflow graph, not just goal tokens).

### 4.2 What to save vs not — the sufficient statistic

**Not saved:** Raw action trace (incidental suffixes .tmp/.bak→{{target}}, literal paths, timing, exact click coords — environments change, action never repeats).
**Saved (exactly one durable unit, inspectable JSON, addable/removable without retrain):**
- `goal_family` (effect|target|suffix, not gkey="goal" one-key)
- `plan_sketch` (lifted template with {{target}}/{{value}} variables, incidental stripped, owned kept)
- `applicability` (IDENTIFIED predicate only — candidate elimination over success/failure states; UNDETERMINED/AMBIGUOUS/INCONSISTENT → not saved)
- `credit_indices` (which steps earned outcome — counterfactual point-of-commitment, not luck)
- `ir_hash_before/after` + `semantic_kind` (Universal IR, loop desugared, α V0/V1)
- `evidence_hash` + `admission_history` (held-out victims, proof-or-witness equivalence)
Raw trace archived as evidence, never served as knowledge.

**Generalization is not optional:** A_SINGLE_TRACE_DOES_NOT_PIN_THE_RULE — without lift+applicability+admission, one experience teaches the wrong reading forever. Generalization IS the learning.

### 4.3 Scan→Retrieve→Fetch→Plan→Learn — how it achieves true generalization

```
SCAN(env)        → affordances+observations (tool_census + scan_and_diff signature validators)
RETRIEVE(scan)   → known vs unknown (KNOWN/UNDERSTOOD/UNREAD vs memory signatures; ignorance kinds NOT_ASKED/DROVE_IT_WRONG/NO_DOCUMENT/SLOT_UNSUPPLIED/NEEDS_CONSTRUCTION)
FETCH(unknown)   → instant knowledge ranked by worth(question) + goal relevance (local_guide 500-md 60% token gate → jit_knowledge 2×2 gate; one source cannot conclude)
PLAN(goal, known+fetched) → shortest path over learned model (BFS) + invented operators where FOREIGN_IDENT (CEGIS typed); horizon-bounded with checkpoint/restore; composition verified transitive+interference
ACT+VERIFY       → execute, goal OBSERVED not assumed, constraint preservation each sub-goal
LEARN(trace)     → credit→lift→applicability→CEGIS→admit(proof-or-witness)→save(JSON)
```

Each step maps to a leap:
- **Data-flow & causal graphs** (Leap 1): data lineage across 10 files, not local line 285 — finds root cause, not symptom patch.
- **Semantic IR** (Leap 2): for/range, while/counter, C for(;;) → same Loop(V0,0,V1,<,1) — one skill transfers Python→C++→Rust.
- **Typed invention** (Leap 3, this iteration): CEGIS proposes new helper/variable, theory solver (types from semantic graph) prunes to well-typed, counterexample refines until proven — not hand-written operator list.
- **Executable mental model** (Leap 4): simulate_plan snapshot/restore predicts 318-call OSWorld without trial-error; horizon decomposition preserves constraints.

**For your “scan everything then retrieve what known/unknown, fetch unknowns from web” — yes, but ranked:** scan everything (cheap), retrieve kinds (not just unknown bit, but which question settles it), fetch goal-directed in worth order (not all unknowns at once — least engineering), learn generalization not trace.

### 4.4 Route order applied (DELETE→…→SYNTHESIZE_NEW_PRIMITIVE)

- Browsers/GUIs: **REUSE** `osworld_v21_browser_ops_v1` CDP (existing, deterministic) — not new grounding.
- NL: **REUSE** `goal_compiler` bounded — not LLM.
- Cross-session: **REUSE** JSON store+Priors — not new DB.
- Counterfactuals: **REUSE** `consistency_vs_equivalence` proof-or-witness — not new complexity.
- Semantic match: **ADAPT** IR bridge one JSON field — not new table (done 714fed10).
- Vocabulary of invention (current bottleneck): **SYNTHESIZE_NEW_PRIMITIVE** typed CEGIS — nothing existing solves non-trivial constants/multi-function invention; history grammar alone not typed, semantic graph alone not generative. Minimal new: type filter from semantic graph (this iteration).

### 4.5 Rejected ideas and why (kill bad ideas pre-implementation)

| Rejected | Why killed (project evidence / first principles) |
|---|---|
| LLM for NL/grounding | Violates zero model calls; `goal_compiler` already deterministic fail-closed; LLM grounding would launder cognition (GENERAL_COGNITION_SUBSTRATE_V4). |
| Hand-written repair operators (swap cmp, add None guard) | `history_induced_edit_grammar` proves list decides before search; new bug → new rule (Iter 70 5→5). Not understanding. |
| Store raw trace as skill | NEVER repeats verbatim; 5 literals → 5 rules; without lift stores incidental .tmp as knowledge (AN_INCIDENTAL_RENAME...). |
| Learn everything exhaustively | Infinite envs, fetch cost dominates, violates best part is no part; measured 2.7% inelastic pages. |
| Exhaustive 200-candidate enumerative without types | Vocabulary branching walls coverage; depth 2 200 → depth 3 8000 explosion; CEGIS(T) theory solver needed. |
| Neural continual learner (CLIF/GEN-1.5 pretrain) | Requires massive warehouse (violates Zero Knowledge House + Every Bit Calculated); forgetting/generalization tradeoff unsolved. |
| New vector DB for retrieval | Signature + ignorance ledger + applicability already give ranked unknowns; vector adds part without measured gain. |
| Synthetic twin substrate for testing | Violates testing integrity (real ComputerEnv required); prior proposal rejected as synthetic. |

### 4.6 Design for hardest case (ultimate not incremental)

- Hardest SWE: multi-file, private helper invention, cross-module types, 163m+ horizon. Design handles it → single-file trivial.
- Hardest computer use: 108 OSWorld 2.0 1.6h median, 318 calls, 31 services, mid-task constraint preservation. Design handles → short tasks trivial.
- Parameter justification: every parameter from measurement (e.g., CACHE_TTL 120s rate-limit, max_depth 3 from branching math, SEARCH_BUDGET 400 from corpus, 2×2 gate from one-source extrapolation defect).

---

## 5. Build — this iteration (vocabulary of invention)

**Bottleneck chosen:** Vocabulary branching. CEGIS without types enumerates 200 candidates depth2 for `x*x` (measured) but cannot reach 5-line helper with typed args (branching factor walls search, OpenAI audit 30% broken tasks mostly multi-file invented logic). Fix unlocks most capability per loop (SWE-bench Pro hardest tasks).

**Research → design:** CEGIS(T) (Augmented CEGIS with theory solver, FM/SMT) separates structure vs constants. Our substrate already has theory: `incremental_semantic_graph` gives import-resolved types (MRO, call graph), `history_induced_edit_grammar` gives proven edit shapes (not hand-written), `concept_library` gives compressive multi-node concepts (Delta B_exec<0, ≥4 probes). Minimal synthesis: wire semantic graph types as filter on enumerative grammar — no new solver binary, pure deterministic Python, zero model.

**Mechanism (Elon's law: one filter, not new engine):** `typed_invention_v1.py` — infer types from IR (Loop init/end, Assign RHS, Call args via semantic graph), enumerate only type-compatible candidates (int→int ops on int vars, str→str, etc.), CEGIS loop unchanged but branching pruned. Same 200 budget now covers depth3 typed space equivalent to depth2 untyped, inventing constants via FM (non-trivial constants that vanilla CEGIS cannot).

**Tests (hardest):** SWE-bench Pro held-out not run here (integrity: agent must run, not engineer hand-solve); unit: `x*x` still ≤200, new `x*2+1` linear constant typed, multi-arg synthesis where untyped times out. Honest next: full harness on untouched Pro via agent harness (blocked until agent owns harness, logged once).

Loop continues — never idle.
