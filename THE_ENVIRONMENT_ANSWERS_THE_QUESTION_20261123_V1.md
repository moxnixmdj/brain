# The environment answers the question — and what that does *not* solve

**Date:** 2026-11-23 · **Branch:** `arena/6f8ac9ce-brain` (branched from `68bf0400`) · **Authority:** `NONE__PRODUCER_RUN_SANDBOX`
**Receipts:** `canonical/verification/THE_ENVIRONMENT_ANSWERS_THE_QUESTION_20261123_V1.json`, `THE_MINIMUM_EXPERIENCE_20261123_V1.json` (+ `_V0_SUPERSEDED_M4_MISDESIGNED.json`), `THE_RELATION_REFUSES_THE_UNSTATABLE_20261123_V1.json`, `THE_LOOP_REPEATS_ON_A_SECOND_GOAL_20261123_V1.json`, `THE_HOLDER_IS_NOT_THE_IDENTITY_20261123_V1.json`
**Research ledger:** `PRIMARY_SOURCE_RESEARCH_20261123_V1.md` (21 unique primary pages read through their final chunk; 81 distinct chunk reads, key passages, full-tail findings and conflicts recorded)
**Status:** five measured iterations (three all-criteria-met, two honestly failed, plus one superseded V0); **§6 is NOT met. Done is not claimed.** No PR, no merge, no capability registration, `truth.achieved` remains `false`.

---

## 0. Requirements read, and the §2 contradiction resolved (and refined)

I read the mission as new, in full: own weights/architecture/agent, zero runtime model calls, zero knowledge house, every parameter calculated, instant knowledge from the project's own source, fully solve computer use incl. advanced SWE/GUI/browser/new environments, single-experience learning, research project first then web, first principles, best-part-is-no-part, ultimate-not-incremental, build player by player, honesty, integrity, §5 loop until §6, hardest open tests, one branch, merge once when complete, deliver all items. The date conflict ("10/11/2026" vs the environment's 2026-11-23 and §6's "Nov 2026") is resolved as **2026-11-23 / Nov 2026**; every currency claim below is measured against that.

**§2 resolution (default adopted, then verified, then refined):**

- **Forbidden:** parameters acting as a lookup of memorized world facts; any runtime dependency on another model.
- **Allowed:** an external, inspectable, editable, deletable store of relations/skills the system computes with; single-experience learning writes to that store.
- **Test:** knowledge lives outside weights, can be added/removed without retraining, weights hold only computed mechanisms.

**Verification from the project:** `canonical/swe_kernel/perfect_algorithm_v1.py` keeps `PERFECT_ALGORITHM_MEMORY_V1.json` (external) with `rules`/`priors` in separate namespaces; `canonical/runtime/jit_knowledge_v1.py` is completeness-gated and never credited as capability; `canonical/runtime/local_guide_v1.py` reads this computer's own guides; `canonical/laws/GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V4.md` and `EXTERNAL_KNOWLEDGE_CAPABILITY_TRANSFER_RUNTIME_COGNITION_BOUNDARY_LAW_V1.md` encode K1/K2/K3. This turn's receipts record `model_calls: 0`, `parameters_stored: 0`, `network_calls_at_run_time: 0`, and a static AST audit of the entire transitive import chain of both new instruments found **zero** imports of `urllib/requests/httpx/socket/http/openai/anthropic/transformers/torch/tensorflow/boto3`. The literature agrees on *where* the boundary is, not on the runtime mechanism: external memory relocates the stability–plasticity dilemma to representation and retrieval, and raw trajectories hinder transfer while abstract insights help [1](https://arxiv.org/abs/2604.27003) [2](https://arxiv.org/pdf/2604.27003).

**Refinement recorded (evidence changed the boundary, so I changed it):** the store does **not** hold executable predicates or world facts; it holds *relation texts* (`monotone[probe_new_content]`, `final:count[probe_new_content]==1`). At replay the predicates are **recomputed from the new machine's own executed runs**; if a term cannot be recomputed, replay refuses (`REFUSED__VOCABULARY_NOT_RECOMPUTED`, measured 25 abstentions in iteration 3). Deleting the file restores the residual class (measured H5). So knowledge is not merely external — it is **machine-relative and re-derived**. This is stricter than the default: nothing stored can be trusted without re-execution. Justification: iteration 3's `MOVE` machine could not recompute the carried terms; blindly evaluating stored code would have produced a guess. The test remains: add/remove without retraining, weights hold only computed mechanisms.

**Second refinement, forced by iteration 5:** relation texts may not name an identity at all. `COMPUTED_HOLDER_RELATION_V1.json` stores only deictic holder-shape invariants (`holder_shape:first_final_different[probe_seed_content]`, `holder_shape:max_holders<=1[probe_seed_content]`) whose predicates are computed from the target machine's `(identity, content)` rows. The goal's content literal is still carried; a machine that does not emit it refuses (`REFUSED__GOAL_CONTENT_OR_TERMS_NOT_RECOMPUTED`). This is not a world fact in weights; it is an external, editable pointer. Content-literal portability remains an open bottleneck, not a hidden success.

---

## 1. Research findings

### 1.1 What already exists in this project (exhaustive sweep; non-obvious names included)

18,056 files, 392 MB, 653 markdown documents, ~7,000 merged PRs' worth of prior rounds. I read the live orientation (`python3 execution_guard/agent_orientation_check_v1.py brief`, `verify` → ok), `README.md`, `AGENTS.md`, `canonical/README.md`, `SOLUTION_INDEX.md`, the `PERFECT_ALGORITHM_*` trilogy, and the entire late round chain (`THE_BRANCH_IS_THE_MODEL_20261128`, `THE_COUNTEREXAMPLE_IS_THE_NEXT_EXPERIMENT_20261129`, `BREADTH_BUYS_WHAT_REPETITION_CANNOT_20261201`, `THE_REPERTOIRE_IS_A_QUERY_20261129`, `RECOGNITION_IS_THE_BOTTLENECK_20261121`, `THE_HYPOTHESIS_GRAMMAR_IS_THE_BOTTLENECK_20261122`, the `intake/` receipts, and the `WHAT_IS_REAL_*` / `WHY_*` series).

| Role | Already exists (name most sessions miss) | What it measured |
|---|---|---|
| The composed loop | `canonical/swe_kernel/perfect_algorithm_v1.py` (976 lines), `canonical/runtime/environment_learning_v1.py`, `goal_compiler.py`, `capability_planner.py`, `BOUND_CAPABILITY_REGISTRY_V1.json`, `brain_unified_model_v1.py` | SCAN → ASK → RETRIEVE → FETCH → PLAN → ACT → VERIFY → GENERALIZE → ADMIT → SAVE; 23 tests; local guide + jit tiers |
| Instant knowledge | `canonical/runtime/jit_knowledge_v1.py`, `local_guide_v1.py` (tool `--help`/man tier wired 2026-11-23), `canonical/astra_runtime/state/JIT_KNOWLEDGE_SOURCE_VALUE_V1.json` | completeness-gated, ≥2 sources; local tier first, web fallback; "how to use grid world" honestly `OPEN` |
| Goal as a relation | `canonical/tools/the_goal_is_a_discriminator_v1.py`, `the_goal_is_a_quotient_of_the_trace_v1.py`, `the_goal_is_a_relation_over_the_run_v1.py`, `the_vocabulary_is_the_artifact_v1.py`, `breadth_buys_what_repetition_cannot_v1.py` | median 12 survivors after one judgment; 555 runs / 244 terms / 29,890 hypotheses / 622 behaviours; residual **2 minimal statements** |
| Action repertoire | `canonical/tools/the_repertoire_is_a_query_v1.py` | 437 programs, 4,621 options, 47 s, **0 of 80** accepted options mutated state; no threshold separates serveable from unserveable needs |
| Planning without a world model | `THE_BRANCH_IS_THE_MODEL_20261128_V1.md` + git-repair tool | copy state, run, read exit status: 6/7 real damaged repos repaired, `transitions_predicted = 0`; the pruned stream lost one task to a deleted edge |
| Recognition / synthesis gap | `canonical/tools/the_assertion_is_the_demand_v1.py`, `the_space_is_the_artifact_v1.py`, `the_corpus_that_can_answer_the_question_v1.py`, `canonical/corpus/single_line_fix_{candidates,commits}_20261123_V1.json` | **1 verified repair in 134 real fixes**, and it had been solved before; 2/75 guard projections; 8/30 fixes are multi-region compositions |
| Learning gates | `canonical/swe_kernel/lesson_admission_gate_v1.py`, `verified_skill_crystallizer_v1.py`, `causal_trace_to_skill_compiler_v1.py`, `autonomous_awake_loop_v1.py`, `intake/authorized_answer_intake_v1.py`, `intake/residual_question_gate_v1.py`, `intake/purpose_gate_v1.py`, `intake/bulk_copy_environment_v1.py` | admission only on fresh instances; typed authorized answer; **one real BULK_COPY run separates the two residual statements** (goal mismatches `{1, 0}`); deleting the store restores the question |
| GUI/browser stack | `canonical/runtime/osworld_v21_brain_agent_adapter_v1..v3.py`, `osworld_verified_task_ledger_v1.py`, `osworld_sensor_request_bridge_v1.py`, `osworld_v21_host_web_app_ops_v1.py`, `canonical/swe_kernel/predicate_world_abstraction_v1.py` | receipt-gated `DONE`, fresh guest PASS, DOM/CNF projection — but the only local OSWorld 2.1 smoke workflow (`osworld-v21-local-qwen-policy-smoke-v1.yml`) launches a **Qwen** server, which the law forbids |
| Truth layer | `AGENTS.md`, `execution_guard/repo_integrity_guard_v1.py`, `canonical/governance/AGENT_ORIENTATION_CONTRACT_V1.json`, `HONEST_SUITE_BASELINE_20261014_V1.json` (11,525 cases: 11,166 passed, 344 failed) | tests run against the tree as it is; no pins, no self-promotion, no editable terminal truth |

Two deliberately non-obvious things I used: `intake/bulk_copy_environment_v1.py` (a 39-line adversarial machine whose one atom creates two copies at once) and `quotient.portable_judge` (the deterministic stand-in for the user's verdict on a run). Neither is a new mechanism; both are the previously measured contrast.

### 1.2 What the frontier is doing (inputs, never runtime dependencies)

- **Hardest computer use:** primary pages read to their final chunk (full-tail findings in the ledger): OSWorld 2.1 is the recommended bug-fix release of OSWorld 2.0's **108** long-horizon workflows, ~**1.6 h** median human time, >**250** agent steps, **31** self-hosted websites and **27.25** checkpoints/task; release binary **20.6%**, live 2.0 leaderboard top **44.33% binary / 77.67% partial**. The paper names the failure mode: constraint tracking, mid-task information, guessing instead of asking, and skipped verification — not basic GUI control [release](https://snorkel.ai/osworld-2-1-long-horizon-computer-use-evaluation/) [paper](https://arxiv.org/abs/2606.29537) [leaderboard](https://snorkel.ai/leaderboard/os-world-2-0/). Original OSWorld: 369 tasks, 72.36% human vs 12.24% best model at publication [project](https://osworld-v1.xlang.ai/).
- **Hardest coding:** primary pages read to their final chunk (full-tail findings in the ledger): SWE-bench Pro paper has **1,865** problems / **41** repos, public **731**, private **276**, held-out **858**, average reference patch **107.4 lines / 4.1 files**, strict fail-to-pass plus pass-to-pass Resolve Rate [paper](https://arxiv.org/abs/2509.16941) [Scale](https://labs.scale.com/leaderboard/swe_bench_pro_public). The live Scale public table lists **61.50 ±3.10** (Muse Spark 1.1), **59.10 ±3.56** (GPT-5.4 xHigh), **51.90 ±3.61** (Opus 4.6 thinking); the official repo's `v2/` tree adds **SWE-bench Pro V2: 642 Harbor tasks, HARD-51, locked-protocol tooling** (Sep 2026) [repo](https://github.com/scaleapi/SWE-bench_Pro-os). The official Terminal-Bench site now shows a **4.1-era** table with top **71.2% ±2.9** (Copilot Fusion, Nov 17 2026); archived 2.1 fixed **28/89** tasks and lists **87.4% ±1.8** top; 2.0 introduced 89 curated tasks [site](https://www.tbench.ai/) [2.1](https://snorkel.ai/leaderboard/terminal-bench-2-1/) [2.0](https://snorkel.ai/blog/terminal-bench-2-0-raising-the-bar-for-ai-agent-evaluation/). These are different generations and must not be merged into one score.
- **Instant/continual learning:** full primary paper + HTML fetched: memory-augmented agents do not escape stability–plasticity; the bottleneck moves to retrieval, abstract procedural memories transfer, raw trajectories produce negative transfer concentrated on the **hard** cases, and fine-grained organization can improve forward transfer while worsening forgetting [abstract](https://arxiv.org/abs/2604.27003) [HTML](https://arxiv.org/html/2604.27003v1). ACuRL adapts computer-use agents to specific environments with zero human data via exploration + curriculum RL but updates ~20% of parameters and uses CUAJudge [1](https://arxiv.org/abs/2602.10356v1). Dr. Zero makes an external search engine the *knowledge environment* and co-evolves a proposer and a solver without training data [5](https://arxiv.org/pdf/2601.07055) [2](https://github.com/facebookresearch/drzero). Relational/neuro-symbolic concepts from few demonstrations support compositional generalization [1](https://cacm.acm.org/research/building-intelligent-agents-with-neuro-symbolic-concepts/) [3](https://aair-lab.github.io/Publications/sns_corl25.pdf).
- **Asking:** full primary PDF fetched: uncertainty-aware clarification closes most of the underspecification gap (69.40% resolve rate) but uses frontier models (Claude Sonnet 4.5 / Kimi K2.6) as asker and judge [1](https://arxiv.org/pdf/2603.26233); goal clarification loses nearly all value after 10% of execution, so *when* to ask is part of the mechanism [3](https://arxiv.org/html/2605.07937v1).
- **Predicate invention / deictic transfer (new research for iteration 5):** full primary pages fetched for [dynamic predicate invention (arXiv:2602.17217)](https://arxiv.org/abs/2602.17217) and its [HTML](https://arxiv.org/html/2602.17217v1), [ExoPredicator (arXiv:2509.26255)](https://arxiv.org/abs/2509.26255), [ICALP 2026 canonical labelling](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ICALP.2026.114) and the [NeurIPS 2018 deictic OO-MDP abstract](https://papers.nips.cc/paper_files/paper/2018/hash/df0aab058ce179e4f7ab135ed4e641a9-Abstract.html). The 2026 predicate-invention papers use MIL/Bayesian/LLM proposals; the deictic paper proves zero-shot transfer from object-relative references; canonical labelling is a real operation but exact trace isomorphism cells proved too fine here. These are inputs, never runtime dependencies. The shipped relation is a computed deictic holder-shape conjunction, not a model-proposed predicate.

Everything above is an input to evaluate. Every one of them either uses a model for producer cognition or pays for breadth with training; neither is allowed here. The project's own late rounds cite WEVA (EMNLP 2026), TriCEGAR (arXiv 2601.22997), Skill-Pro, the ACL 2026 strict-evaluator memory study, OSWorld 2.0's failure analysis (arXiv 2606.29537), "Accepted but Wrong" (arXiv 2611.08269) and the SWE-bench Pro verifier audit (8.5% false accept / 24.0% false reject, DeepSWE arXiv 2607.07946) — I treat those as the project's prior findings, not as my own re-verification.

**The search result that mattered most:** no project or paper I found closes a residual goal class by *executing a contrast in a new environment with zero parameters and zero model calls*. The closest (ACuRL, Dr. Zero, TriCEGAR) all need a model or training. That is the gap this turn measured.

---

## 2. §3 verdict: what is real, what isn't, and the real bottlenecks

**Real (measured, in this tree):**
- A demonstrated action's state transition replays exactly (30/30 in prior rounds).
- The successor need not be predicted: copy the state, run the action, read the result; 6/7 real damaged git repositories repaired with `transitions_predicted = 0`.
- A goal is a **relation over a run**, recoverable as a version space from judgments; acting on the intersection of survivors produced **0 false accepts** (5/5 goals, 0/6 held-out states) in `THE_GOAL_IS_A_DISCRIMINATOR_20261126`.
- Instant adaptation to a new environment needs zero training: the environment is copied, not compiled into weights.
- **New this turn:** a residual goal class that three fitted machines cannot separate is closed by **one executed run in a fourth environment plus one judgment on that run** — 0 questions about statements, 0 parameters, 0 model calls. The collapsed relation predicted 31 held-out runs with 0 false accepts / 0 false rejects / 0 abstentions; the discarded statement was wrong on 6 of them.
- **New this turn:** the portable goal does **not** need exhaustive breadth. One environment at the right depth (FILESYSTEM depth 3, 75 runs / 163 sequences / 1.84 s) bought the same exact held-out prediction as the 555-run / 2,484-sequence / 148.99 s fit: **15.2× fewer sequences, 81× faster**, with 6 false accepts on every shallow rung.
- **New this turn:** the loop is not tied to one goal. Re-fitting on a holder-history goal (`moved_judge`, 25 runs) produced its own 2-statement residual, and one executed run in a third environment collapsed it with one judgment; raw traces abstained 43 times, the relation 0. **But** the literal-identity relation false-rejected 4 of 68 held-out runs — see §5, iteration 4.
- **New this turn:** that named grammar failure was repaired without a model or a hand-built 36th form. A computed deictic holder-shape term family produced two exact minimal statements on 83 fit runs; one real delayed-content run separated them and one judgment selected `first_final_different ∧ max_holders<=1`. The external relation predicted **68/68 OVERWRITE** runs and **127/127 third-name** runs with **0 false accepts, 0 false rejects, 0 abstentions**, and predicted true on all four prior witnesses. It refuses when the goal content literal itself changes. See §5, iteration 5.

**False:**
- "Learn an action once and own it." An action is two things — its form and the *demand* (which relation the failing run violated); a demonstration shows the form. 1/134 real fixes were derived-and-verified, and that one had been solved before; 2/75 guard projections, both the same `if x:` → `if x is not None:` relation.
- "One experience identifies." One judgment leaves a median of **12** minimal discriminators; 555 runs of three machines still leave **2** minimal statements for the goal.
- "Eventually he will learn everything in all environments and generalize." Breadth saturates: goal class 4 → 2 → **2** across three machines; the third machine removed **0** statements. Of 622 behaviours only 57.1% have a unique minimal statement (mean class 2.09, worst 38).
- "Everything on the computer already has a guide, so web knowledge solves it." 437 programs / 4,621 options re-derived in 47 s, but **0 of 80** accepted options changed a byte, and no lexical threshold separated serveable needs from impossible ones [project receipt `THE_REPERTOIRE_IS_A_QUERY_20261129_V1.json`]. This turn asked the local guide the exact contrast question and got `OPEN__LOCAL_GUIDE_NOT_FOUND`; the answer came from executing one atom.
- "Keep the exact experience." 43/43 stale prior rows failed to replay in the fresh-family receipt; this turn's raw-trace lookup abstained on **31/31** held-out runs while the relation abstained on 0. The 2026 literature reaches the same conclusion from the other direction [2](https://arxiv.org/pdf/2604.27003).
- "The residual is a question of words the user must answer." It is a **reachable-contrast** deficit; a new environment can pay it.

**Unproven:** that a general natural-language instruction can be compiled into a checkable purpose without an authorized typed answer; that a relation can refer to the goal's content by structure alone when the content literal itself changes; that any of this transfers to real GUI/browser computer use; that the relation survives SWE-bench Pro-class multi-file repair; that a learned proposer would beat 0.7% on real fixes without becoming a knowledge house.

**Missing:** the *content of a repair* (the author's decision is written nowhere in the environment — seven oracle sources returned 0 new pins); a hypothesis grammar with more than one production (8/30 real fixes are compositions); a reachable-contrast producer for real repositories; live wiring of this loop into the shipped agent; any run of OSWorld 2.1 / SWE-bench Pro V2 / Terminal-Bench 4.1 by our zero-model system.

### Why we cannot just let the model experience the most advanced coding actions once and have it learn them

Because **the trace records what an action did, not which relation the failing run violated**. A one-line fix is 19 characters; the engine can generate that form at 366 sites and is right at 2. A six-step repair from ten unordered actions is ~10⁶ candidate states; copying states is cheap, branching is not. A condition is not in the trace (0 of 10 action preconditions named), the successor is exact and free, verification is free — and still **1 of 134** real fixes was derived and verified. What stops us now, in order:

1. **Missing content** — the fix's *what* is authored; no schedule of exposure supplies content that is not in the environment.
2. **Reachable contrast** — two hypotheses can only be separated by a state the machine can actually produce; where none exists, no question exists (and no question is needed: act on the intersection).
3. **Vocabulary/grammar** — a relation you cannot state is a goal you cannot form; iteration 3 showed the store refuses when its terms cannot be recomputed from the new machine.
4. **Purpose-bearing command line** — which program, on which object, for what end; three successive goals in `THE_BRANCH_IS_THE_MODEL` were satisfiable by destroying the work the user cared about.

This turn **removed** one of the apparent blockers (the "one question of the user"), priced a second (breadth is not needed; the right environment is), and hit a third head-on and reported it as a failure (iteration 3).

---

## 3. The single ultimate plan (minimal; every part justified)

> **Do not learn everything. Carry the smallest class of relations the goal could still be; compute relation terms from the machine's own `(identity, content)` rows; enter the environment whose own atoms can separate the survivors; let one executed run supply the missing bit; save the relation, never the trace; recompute it from each machine at use; refuse where it cannot be recomputed.**

```
FIT      execute enough runs to expose a residual class (no world model, no weights)
COMPUTE  from (identity, content) rows derive deictic holder-shape invariants; no identity literals
CARRY    external JSON of relation TEXTS only (add/remove without retraining)
SCAN     in a new environment, execute its own atoms; read (ident, value) states
ASK      find a run where the carried relations disagree -> one JUDGMENT ON THAT RUN
                                                        (never a question about statements)
COLLAPSE drop every relation inconsistent with that verdict
SAVE     persist the surviving relation text + evidence hash (never the trace/actions)
REPLAY   re-derive the predicates from THIS machine's executed runs; predict; verify
REFUSE   if no separating run: act on the intersection, ask nothing, keep the class
         if a term or goal content cannot be recomputed: refuse, do not approximate
```

**Instant knowledge** (`local_guide_v1` → `jit_knowledge_v1`, completeness-gated) is used for exactly one job: extending the **vocabulary** of relations when a new environment exposes new literals. It never chooses the purpose; this turn measured it returning OPEN on the decisive question. Web is fallback only, offline by default, 0 network calls at decision time.

**Rejected ideas and why (route order `DELETE → BYPASS → REUSE → ADAPT → COMPOSE`, no `SYNTHESIZE_NEW_PRIMITIVE`):**

| Idea | Verdict | Reason |
|---|---|---|
| Web-first "learn everything about the new environment" | killed | guides supply knobs, not purpose or the object; measured 0/80 options mutating state; slow; forbidden to count as capability |
| A dialogue intake asking the owner to choose between sentences | **deleted** | violates "never ask me questions", and `PURPOSE_GATE` already had a real separating run in hand; the machine can answer |
| Store exact actions/traces/plans as permanent memory | killed | 43/43 stale rows; 31/31 held-out abstentions; negative transfer hits hard cases [2](https://arxiv.org/pdf/2604.27003) |
| A learned world model / transition predictor | killed | copy-run-read is exact and free; r27 deleted the model |
| A new neural proposer or NLU parser | killed | forbidden runtime model; also would put authored content into weights (knowledge house) |
| A new admission gate / learner / capability primitive | killed | `breadth.Analysis`, `gate.decide`, `runs.traces_for`, `local_guide.lookup` already cover it |
| Learn all environments equally | killed | iteration 2: one environment at depth 3 beats all three at full depth by 81×; the third fitted machine bought 0 statements |
| Guess when no contrast exists | killed | acting on the intersection measured 0 false accepts on 73 GIT runs |
| A hand-built `holder_changed` predicate | killed | it would be a supplied 36th form, not a computed grammar; `A_SITE_IS_NOT_A_PRODUCTION` already priced that path |
| Full canonical-trace isomorphism table | killed | 0 false accepts/rejects but 43 OVERWRITE and 69 third-name abstentions; exact cells are too fine to carry the relation |
| Model-proposed predicate invention | killed | frontier systems use MIL/Bayesian/LLM proposers; forbidden at runtime and would hide the calculation |
| Claim §6 done from these receipts | killed | OSWorld/SWE-bench Pro/Terminal-Bench were not run; honesty law |

**"Am I sure this is the smartest approach?"** I tried to kill it five ways: (a) a shallow fit produced a weak residual whose collapsed relation false-accepted 6 held-out runs — one judgment is *not* universally sufficient; (b) a mis-specified criterion M4 was falsified by the first ladder run and is preserved as a V0 receipt; (c) a third environment with a different goal refused the carried relation and falsified my expectation that the grammar could not state it; (d) iteration 4's literal-identity relation false-rejected 4 named witnesses; (e) a full canonical-trace isomorphism table had 0 errors but 43/69 abstentions, and a hand-built 36th form was rejected as a supplied vocabulary. All five kills are in receipts or the killed-design field. What survives is the loop above, with one new file per round and zero changes to byte-pinned runtime kernels.

**Player by player (best idea per role, assembled, no whole team bought):** version-space bitmask from `breadth_buys_what_repetition_cannot_v1`; exact successor from `instant_learning_in_a_new_environment_v1` / `THE_BRANCH_IS_THE_MODEL`; projection/quotient computation from `the_goal_is_a_quotient_of_the_trace_v1`; deictic object-relative reference from the NeurIPS 2018 result, computed here as holder-shape indices; active question from `the_goal_is_a_discriminator_v1`; completeness gate from `intake/residual_question_gate_v1`; external deletable store from `intake/purpose_gate_v1`; K1 tier from `local_guide_v1`; admission discipline from `perfect_algorithm_v1`.

---

## 4. The build (all on `arena/6f8ac9ce-brain`)

| File | What it is |
|---|---|
| `canonical/tools/the_environment_answers_the_question_v1.py` | the composed loop: fit → scan two new real CLI machines (`COPY_TWO` via `cp`, `TEE_COPY` via `tee`, plus `git`) → separate → one judgment → collapse → external store → replay → delete-to-unlearn → raw-trace control → local-guide tier |
| `canonical/tools/the_minimum_experience_v1.py` | depth ladder pricing the experience a portable goal needs; active balanced questioning with `ceil(log2(class))` budget |
| `canonical/tools/the_relation_refuses_the_unstatable_v1.py` | a `MOVE` machine (real `mv/cp/rm/ls`) testing what happens when the carried relation cannot be recomputed |
| `canonical/tools/the_loop_repeats_on_a_second_goal_v1.py` | re-fit on the holder-history goal and run the same loop on `EXTRA_FILE` / `OVERWRITE` machines |
| `canonical/tools/the_holder_is_not_the_identity_v1.py` | compute deictic holder-shape terms, fit two minimal statements, separate them on a real `DELAY` environment, save `first_final_different ∧ max_holders<=1`, replay across different identity names, and refuse different goal content |
| `canonical/tools/the_content_is_not_a_literal_v1.py` | compute a `content:first_relocation_source` pointer from each machine's own executor call log, fit three literal-free holder-shape statements, collapse them with two real delayed-run judgments, save `first_final_different ∧ max_holders<=1` over the pointer, replay across machines with different identity **and** content literals, and fail closed when the pointer cannot be recomputed |
| 6 test files + 7 receipts (incl. the superseded V0) + `CARRIED_RELATION_V1.json` + `COMPUTED_HOLDER_RELATION_V1.json` + `COMPUTED_CONTENT_POINTER_RELATION_V1.json` | regression guards and measurements |

Zero changes to `AGENTS.md`, the guard, the referee, laws, byte-pinned kernels, or `truth.achieved`. 0 model calls, 0 stored parameters, 0 network calls at run time; every "run" in every receipt is a real subprocess against real files, archives, SQLite databases or git repositories.

Reproduction:

```
python3 canonical/tools/the_environment_answers_the_question_v1.py \
  --receipt canonical/verification/THE_ENVIRONMENT_ANSWERS_THE_QUESTION_20261123_V1.json \
  --store   canonical/astra_runtime/state/CARRIED_RELATION_V1.json          # 155.6 s
python3 canonical/tools/the_minimum_experience_v1.py \
  --receipt canonical/verification/THE_MINIMUM_EXPERIENCE_20261123_V1.json   # 51 s
python3 canonical/tools/the_relation_refuses_the_unstatable_v1.py \
  --receipt canonical/verification/THE_RELATION_REFUSES_THE_UNSTATABLE_20261123_V1.json  # 0.7 s
python3 canonical/tools/the_loop_repeats_on_a_second_goal_v1.py \
  --receipt canonical/verification/THE_LOOP_REPEATS_ON_A_SECOND_GOAL_20261123_V1.json   # 2.6 s
python3 canonical/tools/the_holder_is_not_the_identity_v1.py \
  --receipt canonical/verification/THE_HOLDER_IS_NOT_THE_IDENTITY_20261123_V1.json      # 4.5 s
python3 canonical/tools/the_content_is_not_a_literal_v1.py \
  --receipt canonical/verification/THE_CONTENT_IS_NOT_A_LITERAL_20261123_V1.json       # 11.3 s
PYTHONPATH=/tmp/pylibs python3 -m pytest -q \
  canonical/tests/test_the_environment_answers_the_question_v1.py \
  canonical/tests/test_the_minimum_experience_v1.py \
  canonical/tests/test_the_relation_refuses_the_unstatable_v1.py \
  canonical/tests/test_the_loop_repeats_on_a_second_goal_v1.py \
  canonical/tests/test_the_holder_is_not_the_identity_v1.py \
  canonical/tests/test_the_content_is_not_a_literal_v1.py
```

---

## 5. Hard, honest tests through the §5 loop

### Iteration 1 — the residual is paid by an environment, not by words
Pre-registered H1–H7 in the tool **before** the receipt. Fit: 555 executed runs, 244 terms, 29,890 hypotheses, 622 behaviours, residual **2**. New environment `COPY_TWO`: 84 sequences → 48 distinct traces → **10 separating runs**; one judgment on the shortest (1 action, verdict false) collapsed the class to `monotone[…] and final:count[…]==1`. Held-out `TEE_COPY` (different implementation, different initial identities): **0 false accepts, 0 false rejects, 0 abstentions** on 31 runs; the discarded `created_once` was wrong on 6. `GIT` with no separating run → `NO_QUESTION`, 0 false accepts on 73 runs (intersection action). Store replayed with 0 re-fit; deleting it restored `REFUSED__NO_CARRIED_RELATION`. Raw-trace memory abstained **31/31**; local guide `OPEN`, never decisive. **7/7 MET**, 155.62 s.

### Iteration 2 — what experience is actually worth
Pre-registered M1–M5. Eight depth rungs, full 555-run fit cited (not re-run). Shallow rungs: residual class 3 → 2, collapsed relations **false-accepted 6 held-out runs each**. The first strong rung `{TARBALL:1, FILESYSTEM:3, SQLITE:1}` — **75 runs / 163 sequences / 1.84 s** — produced the same exact held-out prediction as **555 runs / 2,484 sequences / 148.99 s**: 15.2× fewer sequences, 81× faster, 7.4× fewer runs. Nested supersets added no predictive correctness. Every rung stayed inside its `ceil(log2(class))` judgment budget. **First run: M4 FALSE** (criterion used ladder order, not nesting) — preserved as `_V0_SUPERSEDED_M4_MISDESIGNED.json`; corrected criterion declared before the second run; **5/5 MET** on the corrected receipt, with `criteria_declared_after_a_first_run_for_M4: true` recorded.

### Iteration 3 — the hardest failure I could construct
A real `MOVE` machine where a move and a copy-then-delete end in **identical final states** but are oppositely judged (measured: 1 action vs 3 actions, `identical_final_state: true`). The carried relation **refused** (`REFUSED__VOCABULARY_NOT_RECOMPUTED`, 25 abstentions) — correct, no guess. **But N3 was FALSIFIED:** the existing run grammar *can* state this goal (2 minimal statements), because `run_terms` already produces `present_then_absent[ident]` and `precedence[…]` terms. N2's precondition ("unstatable") was therefore **VOID**, and its intersection measured 0 false accepts / 0 false rejects on all 25 runs. A measurement defect in the first version of N2 (a zero written without evaluation) was fixed and the whole tool re-run. **Receipt: `all_criteria_met: false`** — 3/5 MET, 1 falsified, 1 void. It is pinned as a failed round by its tests.

### Iteration 4 — the loop repeats on a second goal, and the grammar is what breaks
Iteration 3 left a residual of **2** for `moved_judge` on 25 real MOVE runs:
`monotone[probe_seed_content] and present_then_absent[seed]` vs
`no_decrease and present_then_absent[seed]`. I re-fit there (no new learner), carried those texts
into `EXTRA_FILE` (an atom removes an unrelated file, so cardinality falls while probe content does
not), recomputed every term from that machine's own runs, and found **8 separating runs**; one
judgment on a 2-action run collapsed the class to the `monotone` statement (the discarded statement
was wrong on 9 held-out runs). Raw traces abstained on **43** held-out runs; the relation on 0; the
iteration-1 relation still refused (`REFUSED__VOCABULARY_NOT_RECOMPUTED`) — no cross-goal smuggling.

**P3 FAILED: 4 false rejects on 68 held-out `OVERWRITE` runs.** The witnesses are named in the
receipt, not summarised: all 4 are real moves (`mv seed copy`) after which the `OVERWRITE` atom
re-creates the identity `seed` with **different** content. `present_then_absent[seed]` becomes false
while the holder of the probe content genuinely changed from `seed` to `copy`. The grammar has no
term for `the holder of THIS content changed` — a relation over (content, identity) that survives
re-creation of an identity. That is the same "a demand is a relation, not a value; its producer may
be in another frame" law the project measured on real fixes, now arriving from a second goal with a
counted witness. **4/5 MET, `all_criteria_met: false`.** I did **not** add a hand-built 36th term
to make it pass: `A_SITE_IS_NOT_A_PRODUCTION_20261124_V1.md` already priced that incremental path
at ~1 row per form per 35 real fixes.

### Iteration 5 — the holder is not the identity
Pre-registered R1–R7. A computed relation grammar replaced identity literals with **deictic holder-shape invariants**: for one content, replace identity names by first-appearance indices among its holders, then enumerate Boolean invariants of that shape sequence. On 83 real MOVE + EXTRA_FILE runs the version space had exactly **2 minimal statements**:
`initial_final_different ∧ max_holders<=1` and `first_final_different ∧ max_holders<=1`. A real `DELAY` environment made the goal content appear after step 0 and then move; **4 separating runs** existed and one judgment on a 2-action run selected `first_final_different ∧ max_holders<=1` — 1 judgment on a run, 0 questions about statements.

The external store `COMPUTED_HOLDER_RELATION_V1.json` contains no identity literal. Replay recomputed 64 terms from each target machine's own runs: **68/68 OVERWRITE** and **127/127 third-name** runs with **0 false accepts, 0 false rejects, 0 abstentions**; all four prior false-reject witnesses were predicted true. A third machine with different identity names (`origin/archive/side/spare`) transferred; a machine with a different goal content literal refused (`REFUSED__GOAL_CONTENT_OR_TERMS_NOT_RECOMPUTED`); deleting a copy of the store refused and restoring it predicted; raw exact runs abstained 43 times while the relation abstained 0.

Killed designs are measured, not asserted: a full canonical-trace isomorphism table had 0 errors but **43 OVERWRITE / 69 third-name abstentions**; a hand-built `holder_changed` term would have been a supplied 36th form; model-proposed predicate invention is forbidden. **7/7 MET**, 4.46 s, 0 model calls/parameters/network. Content-literal portability remains the next bottleneck and is reported as a refusal, not a success.

### Iteration 6 — the content is not a literal

Pre-registered C1–C7 **before** the receipt. Iteration 5's store still contained the goal content literal `probe_seed_content`; a machine whose goal content was `alpha_content` refused. Iteration 6 replaces the literal with a **computed deictic content pointer**: `content:first_relocation_source`, recomputed from each machine's own executor call log / first relocation source, never from a stored string. The relation texts are therefore literal-free in **both** identity and content.

Design path was falsified in public, not tuned away: prototype 1 used an initial/pre-command fallback and left 39 pointerless runs; prototype 2 removed them but produced **zero separating delayed runs** and was killed. The first production run raised `RuntimeError: POINTER_RESIDUAL_IS_NOT_TWO_EXACT_MINIMAL_STATEMENTS` because `MOVE_ALPHA`+`DELAY_BETA` yielded one exact combo; adding no-change atoms still yielded one. The shipped design uses `MOVE_ALPHA`+`EXTRA_BETA`, no-change atoms, delayed `DELAY_GAMMA`, **three** exact minimal statements, `ceil(log2(3))=2` judgment budget, and **two real 2-step run judgments** on run indices 0 and 5 (true then false) collapsing class 3→2→1. C2 was corrected to three statements / two judgments before the successful run; it was **not** reverted to the earlier two/one design.

Measured receipt `canonical/verification/THE_CONTENT_IS_NOT_A_LITERAL_20261123_V1.json`: **C1–C7 all true**, `all_criteria_met=True`, 11.27 s, 0 model calls / 0 stored parameters / 0 network calls at run time. Fit = 516 executed runs, truth-mask popcount 204, 16 literal-free computed terms, 3 exact minimal statements. Six fit machines have 258 runs / 0 pointer failures; `NO_RELOCATION_SOURCE` has 39/39 pointer failures and refuses. `DELAY_GAMMA` has 258 usable and 9 separating runs. Survivor:

`holder_shape:first_final_different[content:first_relocation_source] and holder_shape:max_holders<=1[content:first_relocation_source]`

Store `canonical/astra_runtime/state/COMPUTED_CONTENT_POINTER_RELATION_V1.json` has schema `BRAIN_COMPUTED_CONTENT_POINTER_RELATION_V1`, `content_pointer.text=content:first_relocation_source`, `identity_literals=[]`, `content_literals=[]`, `evidence.judgments_on_runs=2`, `evidence.judgment_budget_ceil_log2_class=2`; the receipt pins its `store.sha256` prefix as `bed99689fc6825d0`. Receipt `identity_literal_leaks` and `content_literal_leaks` are empty.

Held-out replay on `OVERWRITE_DELTA` (258 runs, different content literal `delta_content`) and `THIRD_EPSILON` (258 runs, different identity names and `epsilon_content`) both give `PREDICTED` with **0 false accepts, 0 false rejects, 0 abstentions**. Pointerless machine refuses `REFUSED__CONTENT_POINTER_NOT_RECOMPUTED` on 39/39; deleted store refuses `REFUSED__NO_RELATION`; copy/restored store predicts; raw exact experience abstains 258 while the relation abstains 0; the old literal store refuses with 258 abstentions; a naive initial-content pointer makes 6 errors; the prior full canonical table is preserved as killed with 43 overwrite / 69 third-name abstentions. A static AST audit of 12 local modules found `marked imports: []` for `urllib/requests/httpx/socket/http/openai/anthropic/transformers/torch/tensorflow/boto3`.

The first combined six-file pytest run was `3 failed, 20 passed` because two new test helpers used nested `frames` tuples; both were fixed to flat frame tuples without weakening any falsifier, then rerun green. **This is a producer-run sandbox result only; no independent identity re-ran it.** It repairs the named content-literal bottleneck from iteration 5 but does **not** repair §6.

### Regression and honesty
- New tests: **23 passed** (6 + 3 + 2 + 3 + 4 + 5).
- Final six-file instrument run after the flat-frame fix: **23 passed in 2.49 s** (first attempt was `3 failed, 20 passed`; the three failures were nested-frame shape bugs in new test helpers, fixed without weakening falsifiers).
- Final targeted regression across the whole mechanism chain, including iteration 6: **194 passed in 186.03 s across 19 selected files** — `perfect_algorithm` (23), `breadth`, `goal_is_a_discriminator`, `goal_is_a_quotient_of_the_trace`, `goal_is_a_relation_over_the_run`, `vocabulary_is_the_artifact`, `local_guide`, `environment_learning`, `jit_knowledge`, `repertoire_is_a_query`, the six instrument test files and the three `intake/` suites. The earlier `DeprecationWarning: invalid escape sequence '\s'` in `canonical/runtime/raw_goal_trace_acceptance_v1.py:1171` did not surface in this run's captured summary; earlier 177-pass, 185-pass and 189-pass runs are superseded. A test-side write to `IGNORANCE_LEDGER_V1.json` recurred during the 19-file run and was again reverted with `git checkout --`, so the patch contains only this turn's files.
- **Verified / unverified / failed split:** verified = the seven receipts' numbers above, all by this producer in this sandbox; unverified = *no independent identity re-ran anything*, no capability registered, no benchmark score, and content-pointer portability is proven only inside this producer sandbox; failed = M4's first phrasing (preserved as V0), the shallow-fit false accepts, iteration 3's falsified N3 + void N2, iteration 4's P3 (4 false rejects with a named cause), iteration 6's killed prototype 2 (0 separating delayed runs), the first production run's `POINTER_RESIDUAL_IS_NOT_TWO_EXACT_MINIMAL_STATEMENTS`, and the first nested-frame pytest failures. Iterations 5 and 6 repaired their two named literal bottlenecks but did not repair the deeper §6 gap. None are hidden.

### §6 — NOT MET (explicit, not softened)
Done requires our own weights + instant-knowledge store + zero model calls to pass the hardest open computer-use and SWE tests in unseen environments. **No OSWorld 2.1, SWE-bench Pro / Pro V2 / HARD-51, Terminal-Bench 2.1 or current Terminal-Bench 4.1 task was run.** Concrete blockers measured in this sandbox: 2 CPUs, no guest VM/display, no docker/Harbor task images, no gated Hugging Face OSWorld assets, no benchmark-host access from the runtime; the repo's only local OSWorld 2.1 smoke workflow launches a Qwen server (forbidden by `NO_MODEL_PRODUCER_COGNITION`); SWE-bench Pro V2 needs 642 Harbor tasks with locked graders; Terminal-Bench needs containerized rollouts. Reading every remaining primary-source chunk to `hasMore=false` confirmed rather than removed these blockers: OSWorld 2.1 pins gated HF task classes/assets, self-hosted websites/GitLab, Python >=3.12, pinned Docker/AWS images and a maintainer-run verified leaderboard; SWE-bench Pro's own repo prescribes Docker images, `gather_patches.py` and `swe_bench_pro_eval.py` with locked graders; Terminal-Bench's current 4.1-era table and archived 2.1 page remain separate generations. Iteration 6's `all_criteria_met=True` is a producer-run causal falsifier on real CLI machines, **not** a benchmark score, independent verification, capability registration, or terminal completion. Simulating any of the hard suites would be a lie, so I did not. The CLI machines here are real programs, but they are **not** an ultimate-hard test. Per the honesty law: this is progress, not completion.

---

## 6. Expansion rule, applied

| Expansion | Smartest zero-constraint solution | Status |
|---|---|---|
| **GUIs / browsers** | the loop is reader-agnostic: state = `(ident, value)` pairs, atoms = real commands. A DOM/accessibility-tree reader would plug into `runs.traces_for` with no new mechanism; `predicate_world_abstraction_v1.py` already projects HTML forms into CNF predicates. But no guest VM exists here and the only local OSWorld smoke uses a forbidden model. | **Unproven.** Rigorous reason for not shipping: without a real guest, a "GUI test" would be a fixture, and §6 forbids synthetic proxies. Constraint unchanged. |
| **Natural-language input** | not parsed by a model. The owner's *judgments on runs* (booleans) plus typed authorized answers (`intake/authorized_answer_intake_v1.py`) compile into executable checks; residual questions are asked only on real contrasts (`residual_question_gate_v1`). This turn deleted the last NL-dependent step — choosing between sentences. | **Partly solved.** General free-form instruction → checkable purpose remains **unproven**; no NLU model is permitted, so it must be typed or judged. |
| **Cross-session learning** | external JSON of relation *texts*; deletion is the whole unlearning operation (H5/R5/C5); predicates **and the goal content pointer** recomputed from the current machine at use (§2 refinement). Iteration 6 stores `content:first_relocation_source` plus deictic holder-shape invariants, with `identity_literals=[]` and `content_literals=[]`. | **Solved for identity + content literal renames inside this producer sandbox:** iteration 3 showed a relation fitted for one goal/machine refuses on another; iteration 5 transferred across identity names but refused a changed content literal; iteration 6 predicts 258/258 on two held-out machines with both kinds of literal changed and refuses pointerless/old-literal stores. "Learn once, keep forever" is still false as an independent or §6 claim: no independent identity re-ran it, and the carried term family remains the fitted holder-shape grammar. |
| **Auto-discovered counterfactuals / victims** | constructed by executing real atoms (this turn found 10 separating runs in 84 sequences and used the cheapest). Prior round `CONSTRUCTED_QUESTIONS_ARE_NOT_AIMABLE` found four computable *orderings* worse than chance when no named hypothesis exists; here a named pair makes the contrast aimable. | **Solved for a named residual class; the general aiming problem stays open.** |
| **New expansion: "learn everything from the web"** | completeness-gated K1 tier for vocabulary only; never for purpose; offline by default. Measured OPEN on the decisive question this turn. | **Falsified as a complete strategy**, with numbers. |

---

## 7. Next bottleneck (loop continues; no approval pause)

1. **Independent verification and grammar transport (the bottleneck iteration 6 leaves).** Iteration 6 computed the goal content pointer `content:first_relocation_source` from each machine's own executor call log, removed both identity and content literals from the store, and met C1–C7 on two held-out machines with both kinds of literal changed. But every number is still `NONE__PRODUCER_RUN_SANDBOX`. The next build must be re-run by an independent zero-model identity from a fresh process, and must change the **goal / relation grammar itself** (not merely the literals) while terms are re-derived from the new machine; otherwise the carried artefact is still one fitted holder-shape vocabulary. No model, no NLU parser, no world fact in weights.
2. **Vocabulary transport / re-fit cost.** A carried relation is refused when its term texts do not recompute from the new machine (25/25 abstentions in iteration 3), even though re-fitting there costs 25 runs and 0.7 s. Iterations 5 and 6 made identity and content literals travel while terms were recomputed (68/68, 127/127, then 258/258 and 258/258). Now price re-deriving a *different* term family on a second goal, keep deletion-to-unlearn fail-closed, and preserve the measured refusals rather than hiding them.
3. **Authored repair content.** 1/134 real fixes, 8/30 multi-region compositions. A `RELATION_OVER_TWO_SITES` production with the project's own suite as the only judge, pre-registered as in `THE_HYPOTHESIS_GRAMMAR_IS_THE_BOTTLENECK_20261122_V1.md`, on commits not used by any prior sweep.
4. **§6 corpora.** OSWorld 2.1, SWE-bench Pro V2 / HARD-51 and the current Terminal-Bench 4.1 under a zero-model path, with a real guest/harness and pinned graders. Until that exists, `truth.achieved` stays `false` and no merge is made.

**Workflow / gates:** everything above is on `arena/6f8ac9ce-brain` as a clean local commit. Exactly one action intent is present: `canonical/action_intents/THE_ENVIRONMENT_ANSWERS_THE_QUESTION_20261123_V1.json`, now on route `COMPUTED_CONTENT_POINTER_RELATION_V1`, and its `gate_results` field records the final rerun. The project gates were run after the final commit against base `68bf0400…` and the commit head: `agent_orientation_check_v1.py verify` → `ok: true, errors: []`; `enforce_load_bearing_primary_pr.py` → `LOAD_BEARING_ADMISSION_PASS` (13 open obligations, constructive gap `OSWORLD_2_1_PARTIAL_GE_81_8`, `scope_complete=False`); `enforce_goal_hierarchy.py` → `DRIFT_GUARD_PASS` (exactly one action intent, `sensitive_files=0` outside intents); the drift workflow's continuous-OBS unit tests → `Ran 14 tests … OK` (7 + 7) and `current_state_obs_reducer.py` → `pass: true`. These are **local, producer-run gate results, not independent verification**. No PR, no push and no merge, because the feature is not complete (§6 unmet) and the workflow says merge once, when complete. No files were deleted, renamed or moved; the repository root and `.git` are untouched.

**Final honest sentence:** the owner's idea is right in direction and wrong in one word — the perfect algorithm should not *know everything* about a new environment, and should not *ask the user*; it should carry the smallest set of relations it cannot yet decide, and **ask the machine for the one run that decides them**. That is now built, measured, priced, falsified in several rounds with named causes, repaired twice by computed deictic holder-shape and computed content-pointer relations, and still far from the hardest benchmarks.
