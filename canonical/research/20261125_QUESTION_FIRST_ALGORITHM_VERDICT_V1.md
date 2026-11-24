# The Ask-Verify-Admit Verdict: question-first computer use for Brain

Date: 2026-11-24/25 · Branch: `arena/8e7b5375-brain` · Status: research verdict + plan; one honesty fix shipped (see §Build).

## 1. Requirements restated (binding)

- Own weights only at runtime; zero external model calls; zero knowledge house (parameters hold computed mechanisms only); every parameter derived and justified; instant knowledge from the built-in store, not from parameters; §2 boundary adopted: forbidden = parameters acting as a memorized-fact lookup + any runtime dependency on another model; allowed = an external, inspectable, editable knowledge/skill store + single-experience learning that writes to that store; test = knowledge add/removable without retraining.
- Tests on hardest open benchmarks only (Terminal-Bench 4.0, SWE-bench Pro, OSWorld-V2). Only our agent takes them. No leakage, no hand-solved tests, no borrowed outputs.
- No benchmark-success claim from a green workflow or 0.0 rewards. Verified / unverified / failed must be separated in every report.
- Never weaken guards; 17-rule repo-integrity guard and DRIFT_GUARD_PASS stay clean; pristine Pro replay and official verifier scoring untouched.
- Work in the one branch; merge once when the feature is complete.

## 2. The §2 contradiction, resolved

Owner's default adopted, refined by evidence from this project and the frontier:

- **Forbidden stands**: parameters as a lookup of memorized world facts; runtime calls to any external model.
- **Allowed stands**: an external, inspectable, editable store (markdown/JSON knowledge, verified skills, environment models, episode evidence) that Brain computes with; learning writes to it from a single experience, gated by admission.
- **Boundary test**: knowledge must be add/removable without retraining; weights hold only computed mechanisms (separators, planners, verifiers, binders).
- Evidence for the boundary: ContinualSkillBench (arXiv:2608.03874, Aug 2026) shows retained-context reuse beats auto-dumped skill libraries; SkillLearnBench (COLM'26) finds no dominant continual-learning method; SkillTTA (arXiv:2605.16986) shows test-time synthesized temporary skills beat static libraries. SAGE (ACL 2026) and LifeSkill (arXiv:2606.04815) fold skills into parameters via RL — legal as a build-time choice but wrong for us: it violates "every parameter calculated" (RL output is not derived) and makes knowledge non-removable. Our store stays external.
- Evidence from this project: `verified_skill_crystallizer_v1 / hierarchical_skill_library_v1 / causal_trace_to_skill_compiler_v1 / skill_recurrence_curve_v1` implement external skill admission with fresh-victim gating; `PERFECT_ALGORITHM_MEMORY_V1` does not exist yet (store never populated — memory was designed, never used in production).

Nothing found in project or literature justifies widening the boundary. If a future mechanism requires parameters-as-lookup, it is out of scope, not a constraint change.

## 3. Research findings

### 3.1 What already exists in this project (do not rebuild)

| Mechanism | File | State |
|---|---|---|
| The owner's idea, implemented: scan → right question → plan → act → verify → generalize → admit → save | `canonical/swe_kernel/perfect_algorithm_v1.py` | Real code, ~992 lines; **tested only on toy walls/locks**; never wired into Harbor / real computer use; memory store file never created |
| Environment model learning (affordances, reversibility, priors) | `environment_learning_v1.py` (imported by perfect_algorithm) | Implemented for reversible sandbox fixtures; unsafe for shells by design |
| Question selection by information gain (EIG action choice) | `right_question` in perfect_algorithm; `the_smallest_question_that_makes_this_checkable_v1.py` | Implemented for small discrete envs; not for open-ended shells/program synthesis |
| Generalization + admission on fresh victims | `generalize`/`admit` in perfect_algorithm; `experience generalizer: semantic_generalization_engine_v1.py`; `verified_skill_crystallizer_v1.py`; `lesson_admission_gate_v1.py` | Implemented; never admitted anything from real tasks (0 production episodes) |
| Computer-use agent (calculated state keys, standing facts, noticing ignorance) | `canonical/swe_kernel/computer_use_agent_v1.py` | Implemented; fixtures; not on Harbor path |
| Instant knowledge, local tier (offline docs/man pages, zero network) | `canonical/runtime/local_guide_v1.py` | Real; used by perfect_algorithm tier 1; usable by doc compiler |
| Instant knowledge, web tier (completeness-gated, ≥2 sources, ≥2 kinds) | `canonical/runtime/jit_knowledge_v1.py` | Real; network at decision time = off by design in Pro/TB4 (no-network tasks) |
| Doc compiler: scan environment → compile CLIs from contracts → synthesize invocation → verify | `canonical/runtime/epistemic_doc_compiler_agent_v1.py` (~2365 lines) | **The live in-container path**; solves doc-verifiable CLI pipelines; honesty bug fixed this turn (see §Build) |
| Container worker (TB4/Pro cycles) | `harbor_container_solver_worker_v1.py` | Wired; smoke shows it executes but proposes 0 correct actions |
| Episode evidence, traces, ATIF trajectory | `harbor_experimental_vm_v1.py`, `harbor_epistemic_agent_v1.py` | Working; feeds verifier but not yet a learning loop |
| Unified model (own weights, zero dependency) | `brain_unified_model_v1.py` + bound capabilities | Loads verify=True; solve() runs; FAIL_CLOSED on the vigenere instruction (0 actions) |

### 3.2 What the frontier did (2026, web-cited)

- **Information-gain questioning is the correct mechanism for "ask the right question".** OQA/active-inference (arXiv 2608.19202): context actions chosen greedily by expected information gain per unit cost beat asking nothing and track oracle questioning; BattleshipQA (ICLR 2026, arXiv 2510.20886): Bayesian-experimental-design questioning takes a small model superhuman on information-seeking (Llama-4-Scout 8%→82%). Nous (arXiv 2510.27410) and ICML 2026 clarifier work: ~1.3 targeted questions beat 4–5 generic ones.
- **Skill libraries are real but consolidation is the bottleneck.** ContinualSkillBench (arXiv:2608.03874): sequential skill reuse gains ~16.9%, mostly from retained context; repositories bloat (~384 skills, infrequent invocation); skill curation remains a human/design responsibility. SkillTTA: synthesize a temporary test-time skill instead of dumping traces.
- **Benchmarks (Nov 2026):** Terminal-Bench 4.0 — most-cited, test-graded, Harbor format (our target). SWE-bench Pro ~61.5% (Muse Spark 1.1, Oct 2026 snapshot) — nearly saturated for frontier, not for us. OSWorld-V2: best ~72.6% (GPT-6 Astra, 500 steps); general computer use unsolved. One ex-modelorg source claims SWE-bench Pro 80%+; treat all such numbers as unverified.
- **Key frontier lesson for us:** every working 2026 system wraps a strong pretrained reasoner. Zero-call Brain has **no general reasoner**; everything must be computed or retrieved. That is the actual gap your idea points at.

## 4. §3 verdict — your idea, honestly

**True, with evidence:**
1. The loop shape (scan env → ask right question → retrieve instant knowledge → plan → act → verify → learn the generalization, never the raw trace → admit on unseen victims → save) is the right architecture for arbitrary environments. It is not novel to the web; it is the right invention, and this project already implements it end-to-end on reversible fixtures.
2. Goal-directed >> learn-everything. Scan-everything is impossible as pre-training and wasteful as runtime; what IS worth learning from every environment is the **environment model priors** (affordances, reversibility, artifact grammars) — already designed via `priors_for` in perfect_algorithm — and **admitted, generalizable skills** (goal family + plan sketch), never raw action traces.
3. The right question is not "what is this environment" but "which action/observation most shrinks uncertainty about *the goal*" (EIG w.r.t. the task). The literature and the project agree.
4. Knowledge should live outside weights as an inspectable store, admitted by replay on fresh victims — our boundary holds.

**False / overstated:**
5. "Everything on the computer already has a guide on the web; just fetch it." False at the two places that matter: (a) Harbor tasks run **no-network** for the agent — web is available to us at build time, not to the shipped system at decision time; (b) for the hard core — generating a correct algorithm for `interleaved-vigenere` from a spec — no guide writes the code for you; retrieval cannot substitute for capability.
6. "The model just asks questions" is not sufficient — knowing **what you don't know** requires a belief model, and verifying answers requires a checker. Without them, questions are decorative.
7. "One experience, learned permanently" is real only for **narrow, verifiable skill families** (code repair with admitted victims). It is not a property of arbitrary experience, and treating it as such is how stores rot (Skill Learn Bench).

**The real limiting factors, from first principles, in order:**
- **F1. No program-synthesis capability in the zero-call runtime.** TB4/Pro smoke (run 45430957112): doc compiler `CLI_EXECUTION_UNVERIFIED`/FAIL_CLOSED on `interleaved-vigenere`; unified model `FAIL_CLOSED`, 0 actions. The bottleneck is *producing a correct artifact*, not finding documentation. No amount of question-asking fixes this without a synthesis+verify substrate.
- **F2. Verification asymmetry.** In v1 the engine said `VERIFIED` on a 5-byte `DESIGN.md` (`session-window-debug`, reward 0.0) — self-reported checks passed on vacuous predicates. This turn: annotation now reads `no_invariant_applicable__UNVERIFIED_CLAIM` when zero semantic predicates fired; nothing can claim semantic verification that checked nothing. (Status still VERIFIED = execution + artifact + no contradiction; it is not task-correctness.)
- **F3. The learning loop is not closed on real environments.** perfect_algorithm admits on fresh victims only in grid worlds; nothing from Harbor/Pro runs writes admitted skills; PERFECT_ALGORITHM_MEMORY is empty. One-experience learning is designed, measured nowhere real.
- **F4. /app is shared, quiescence unverified**; detached processes can outlive the worker; measurement is bounded but not a sandbox.

## 5. The ultimate plan (minimal; each part justified; rejected ideas listed)

**ASK–VERIFY–ADMIT** — one general loop, no new framework:

1. **ASK (goal-directed belief gap).** Maintain for the task an explicit *knowledge ledger* (known facts, unknowns, discriminating questions). A question is worth asking only if it separates surviving hypotheses about success — computed (EIG over the ledger), never LLM-vibes. Sources: local guide (tier 1, free, version-matched, already on machine), then web JIT at build/authoring time (completeness-gated, ≥2 sources, ≥2 independent kinds), then — only if capability is missing — the synthesis substrate (F1).
2. **VERIFY (independence).** Every artifact must pass an executable check stronger than "file exists". Absence of an applicable invariant now refuses the claim of semantic verification (shipped this turn). The official Harbor verifier remains the only task-correctness oracle; everything local is unverified scaffolding.
3. **ADMIT (victims before save).** A lesson is stored as *goal family + plan sketch + evidence* only after replay on fresh instances; the raw trace is archived as evidence, never as knowledge. Store is inspectable JSON; removable; weights untouched.
4. **Loop across runs.** After each Harbor/Pro task, close the loop offline: episode evidence → generalize → admit-on-victims → store. Next run retrieves by (goal family, environment signature). This is the only honest meaning of "learns instantly in arbitrary environments".

**Concrete next steps (in order):**
- S1. Close F1 with a synthesis-then-verify substrate for coding tasks, built once and role-reused (see S3), not per-task. First hard target: the two TB4 tasks are *verifier-gated*; capability must come first. Do not hand-solve or leak; Brain must derive it.
- S2. Wire tier-1 local guide + tier-2 (offline packs authored at build time) into the container worker deliberately, replacing the silent `NOT_APPLICABLE` states; report retrieved/not-retrieved per gap in the trace.
- S3. Close F3: extend `verified_skill_crystallizer_v1` admission from code-repair families to *plan-sketch* families admitted on fresh fixture instances (admit-or-refuse with counts), persist to the store, and retrieve at worker start. Measure admit-rate and reuse, honestly labeled.
- S4. Re-run `Frontier 2x2 smoke evaluation` after each change; report measured rewards; no success claims.
- S5. When TB4 program synthesis can solve the in-domain classes repeatedly (0 model calls), promote; otherwise keep failing loudly — that is the system working as designed.

**Rejected ideas and why:** (a) "Learn everything to generalize later" — pre-training by another name; violates parameters-as-mechanism-only; unbounded; unfalsifiable. (b) "Exhaustive environment scan then memorize" — exponential, useless off-path, fills store with noise. (c) "Web-fetch agent at runtime" — Pro/TB4 run no-network; violates "instant knowledge from built-in store"; latency. (d) "RL into parameters (SAGE/LifeSkill-style)" — non-derived params; unremovable knowledge; against mission §2. (e) "Bigger unified model / more bound capabilities" — capability is not knowledge; wrong direction; already shown FAIL_CLOSED. (f) "Trust doc-compiler self-VERIFIED" — was the F2 bug; fixed this turn. (g) "Auto-dump every experience into the store" — SkillLearnBench shows repository rot; admission gate is the design, not overhead.

## 6. Build shipped this turn

- `epistemic_doc_compiler_agent_v1.py`: `_check_semantic_postconditions` now counts applicable semantic predicates. When zero fire, the verification annotation reads `no_invariant_applicable__UNVERIFIED_CLAIM` instead of the false `semantic_postconditions_verified`. When predicates fire it reads `semantic_postconditions_verified:predicates=N`. No behavior change beyond honesty of the claim; fixture-verified (filter/sort/unique/JSON/sha invariants exercised, unverifiable case honest). Full affected-suite test run green (harness typos excluded; suite passes: tb4 worker 5/5, epistemic agent 11/11, vm 8/8, pro grounding 5/5, workspace-diff 4/4, pro-worktree 7/7).
- Deliberately NOT built: a cipher-cracking or session-window-debug "solver" — that would be hand-solving the benchmark, leaking test answers into the runtime, and cheating the only integrity that matters. Capability must be derived, or this project is another borrowed benchmark.

## 7. Honest status

- Verified: the F2 annotation fix (local fixtures); guardrails after commit (17 rules PASS, DRIFT_GUARD_PASS); smoke `45430957112` on `ffd9140a7f` — candidate path executes, /app mutated measurably on `session-window-debug` (diff_bytes 5, DESIGN.md), NodeBB staging unblocked (`STAGED__UNVERIFIED`, 5305 entries, test execution authorized), all rewards 0.0.
- Unverified / failed: Brain cannot yet solve either TB4 task; the vigenere path reaches `FAIL_CLOSED`; no admitted skills exist; PERFECT_ALGORITHM_MEMORY is empty; the full ASK–VERIFY–ADMIT loop has never run on a real environment.
- Failed: nothing was hidden; 0.0 rewards stand.

## 8. Binding next step

F1 (zero-call program-synthesis capability for TB4-class tasks) is the bottleneck. Research: project (`swe_kernel/` synthesis organs: `egraph_and_deductive_synthesizer_v1`, `operator_invention_v1`, `instruction_contract_for_code_v1`, `one_demonstration_*`) then frontier (test-time program synthesis, verifiable code generation without pretraining), then design the ultimate minimal substrate and implement it. No benchmark leakage; admission on victims.
