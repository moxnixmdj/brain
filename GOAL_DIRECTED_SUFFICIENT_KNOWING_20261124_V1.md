# Goal-directed sufficient knowing — minimal plan, build, and honest boundary

**Date:** 2026-11-24 UTC · **Branch:** `arena/6f8ac9ce-brain` · **Status:** local zero-model contract instrument built, 16 tests passing, runner-owned OIDC finite replay recorded, final lightweight gates 20/20 passed; §6 NOT MET; no capability, family, terminal or truth credit.

## 0. Requirements read, and §2 contradiction resolved

I read the prompt as new, in full. Binding requirements: own weights/architecture/agent; zero runtime model calls; zero knowledge house; every parameter calculated; instant knowledge from the project's external store; research project first and web continuously; first principles; best-part-is-no-part; hardest-case design; build player by player; real understanding; honesty; integrity; hardest open tests; one branch; merge once when complete; never ask questions; never stop at a milestone; log fully user-dependent blockers once and continue; insanely fast; create new mechanisms from project history, web evidence and first principles.

**§2 resolution, verified against the live project:** parameters may hold computed mechanisms only. Knowledge and learned skills live in an external inspectable/editable store. The strict project refinement is stronger than the default: stored relation texts are not executable predicates or world-fact answers; they must be recomputed from the current machine's own evidence, and the agent refuses when a term cannot be recomputed. Test: add/remove/edit the store without retraining, no runtime model dependency, zero facts in weights.

## 1. What already exists in the project (non-obvious names included)

| Role | Existing mechanism | Measured boundary |
|---|---|---|
| Full scan/ask/retrieve/fetch/plan/act/verify/generalize/admit/save loop | `canonical/swe_kernel/perfect_algorithm_v1.py`, `canonical/runtime/environment_learning_v1.py`, `goal_compiler.py`, `capability_planner.py`, `BOUND_CAPABILITY_REGISTRY_V1.json` | 23 tests; local guide + JIT tiers; unknown goals fail closed |
| Instant knowledge | `canonical/runtime/jit_knowledge_v1.py`, `local_guide_v1.py`, `canonical/astra_runtime/state/JIT_KNOWLEDGE_SOURCE_VALUE_V1.json` | completeness-gated; ≥2 sources; local tier first; web fallback; open-world knowledge honestly OPEN |
| Global anti-blind-spot search | `canonical/runtime/global_retrieval_controller_v1.py` | multilingual, technical-anchor, history, queryless bounded enumeration, correlated-channel discount, open-world unknown firewall |
| Goal/vocabulary/relation instruments | `the_goal_is_a_discriminator_v1.py`, `the_goal_is_a_quotient_of_the_trace_v1.py`, `the_goal_is_a_relation_over_the_run_v1.py`, `the_vocabulary_is_the_artifact_v1.py`, `breadth_buys_what_repetition_cannot_v1.py` | 555 runs / 244 terms / 29,890 hypotheses / 622 behaviours; residual 2 minimal statements; breadth saturates |
| Action repertoire | `canonical/tools/the_repertoire_is_a_query_v1.py` | 437 programs, 4,621 options, 0 of 80 accepted options mutated state; no threshold separates serveable from unserveable needs |
| Learning gates and one-shot falsifications | `canonical/swe_kernel/lesson_admission_gate_v1.py`, `verified_skill_crystallizer_v1.py`, `intake/purpose_gate_v1.py`, `intake/residual_question_gate_v1.py`, `THE_BOTTLENECK_IS_THE_INDEX_NOT_THE_LEARNING_20261116_V1.md`, `LEARNING_ONCE_DOES_NOT_SOLVE_COMPUTER_USE_20261113_V1.md` | raw experience does not accumulate; one demonstration is not identification; the index, verifier, hypothesis grammar, goal and site are separate bottlenecks |
| Authority and transport | `THE_ENVIRONMENT_ANSWERS_THE_QUESTION_20261123_V1.md`, grammar transport receipts, OSWorld website-substrate receipts | distinct OIDC-attested exact-byte replay; website source/compose config verified; no website deployment, OSWorld task run, score or §6 |

The project already answered the owner's new idea in measured form: **authority > knowledge**. A larger fact warehouse does not supply purpose, verdict, generalization license, or unseen-environment capability. The perfect algorithm should not know everything; it should carry the smallest undecided relation class and ask the machine for the one run that decides it.

## 2. Frontier research findings

- SWE-Bench Pro V2 released 642 cleaned tasks and a 51-task Hard split; the full set is close to frontier saturation while Hard still separates systems, and the protocol hardened verifiers, scrubbed git history, disabled network access during the agent phase, and audited trajectories for reward hacking [1](https://arxiv.org/html/2610.24206). Terminal-Bench 4.1 keeps 66 professional computer-work tasks with verifiers hardened on 2026-11-09 [10](https://benchlm.ai/benchmarks/terminal-bench#terminal-bench-2-0).
- OSWorld 2.1 remains the heaviest current computer-use target: 108 long-horizon workflows, 31 self-hosted web environments, median ~1.6 hours of human work, and failure concentrated on constraint tracking, mid-task information, hidden state and verification rather than basic GUI control [9](https://snorkel.ai/osworld-2-1-long-horizon-computer-use-evaluation/) [10](https://llm-stats.com/benchmarks/osworld-2.1-strict).
- Continual-learning memory does not eliminate stability/plasticity; it moves the bottleneck to representation and retrieval. Abstract procedural memories transfer more safely than raw trajectories, and negative transfer hits hard cases hardest [1](https://arxiv.org/html/2604.27003v1) [3](https://arxiv.org/abs/2604.27003). Memory-centric continual learning argues memory must be judged by future action improvement, not passive recall [2](https://arxiv.org/html/2610.29357).
- Self-evolving coding agents distill trajectories into skills, but the survey's own hard requirement is filtering, abstraction, retrieval and validation so noisy logs and brittle repository-specific conventions do not hurt future performance [1](https://arxiv.org/pdf/2608.03392v1). CODESKILL learns a skill-bank management policy and reports gains while maintaining a compact skill bank [3](https://arxiv.org/abs/2605.25430). These are model/learning-dependent frontier specimens, not Brain runtime dependencies.
- Value of Information formalizes clarify-or-commit as expected utility gain minus interaction cost, with ambiguity, task risk and cognitive load [3](https://aclanthology.org/2026.acl-long.1987/). Active perception uses plan–observe–reflect with query-sufficiency halting; beyond three rounds gains saturate [5](https://arxiv.org/pdf/2512.05774). SAGE-Agent grounds the question in structured tool-parameter domains and uses EVPI to choose questions and stop; it reports 7–39% coverage gains with 1.5–2.7× fewer clarifications, but its runtime still uses an LLM [11](https://aclanthology.org/2026.findings-acl.2028.pdf). REVOIR likewise makes clarification decisions from expected improvement in task reward and reports success with fewer questions, again as inference-time reasoning on a model [12](https://arxiv.org/abs/2609.37588v1). These are mechanism evidence only, not Brain runtime components.
- Completeness is a hard open problem. SeekerGym measures information-gathering completeness and completeness uncertainty [1](https://arxiv.org/html/2604.17143). WideSearch finds primary failure is not finding individual items but collecting all atomic information; recall lags precision and top table-level success is only ~7% [7](https://proceedings.iclr.cc/paper_files/paper/2026/file/1119587863e78451f080da2a768c4935-Paper-Conference.pdf). DeepSearchQA shows under-retrieval of the long tail and over-retrieval without a stopping criterion [6](https://arxiv.org/html/2601.20975v1). LiveBrowseComp suppresses intrinsic-knowledge shortcuts with recent long-tail facts [4](https://arxiv.org/html/2605.28721). ClosureBench, submitted 2026-11-19, isolates OWA/CWA/LCWA: absence from an incomplete source is unknown, absence from a complete source may be false, and Ask/Act errors include excessive asking or losing false when local closure shrinks [13](https://arxiv.org/abs/2611.26335v1). This directly justifies the module's `bounded_enumeration` / `completeness_required` source contract.
- Neuro-symbolic concepts support data efficiency and compositional generalization by typed programs plus grounding [1](https://cacm.acm.org/research/building-intelligent-agents-with-neuro-symbolic-concepts/), but reviews note fixed DSL/vocabulary limits and that no single agent demonstrates all claimed properties [7](https://pith.science/paper/2505.06191). ACuRL adapts computer-use agents with zero human data but uses RL, parameter updates, GPT-5 task generation and CUAJudge evaluation [2](https://arxiv.org/html/2602.10356); under the owner law it is K2/specimen evidence only, never runtime cognition.

## 3. Verdict on the core hypothesis

**True:** the project has a real external-store instant-learning mechanism, a computed-relation grammar, zero-model exact-byte replay carriers, goal-as-relation instruments, and a verified way to add/remove/store edit knowledge without retraining.

**False as universal claims:** "one advanced coding experience plus instant learning solves arbitrary computer use"; "the agent should learn everything in every environment"; "perfect web research can be a runtime reasoner"; "eventual breadth automatically yields the right generalization". One trace underdetermines the goal, hypothesis grammar, site, verifier and authored repair content. Breadth saturates in project measurements. Raw trajectories cause negative transfer on hard cases in the 2026 literature. A web page is K1 evidence, not authority.

**Unproven:** transfer of the new sufficient-question quotient to untouched hard OSWorld 2.1, SWE-Bench Pro V2 HARD-51, Terminal-Bench 4.1, WebArena-Verified or DeepSearchQA/WideSearch instances; independent §6 verification; arbitrary natural-language purpose; authored repair content; GUI/browser control.

**Real bottlenecks, from first principles:** (1) goal/purpose binding and success predicate; (2) finite typed vocabulary/grammar for decision-relevant relations; (3) independent verifier and exact environment evidence; (4) authored repair/synthesis for novel changes; (5) open-world completeness and stopping; (6) fresh unseen hard environments with owner/gated authority.

**Direct answer to "why can't we just let the model experience the most advanced coding actions once and learn permanently?":** one experience supplies at most one bit about one scoped relation. It does not identify which variables were causal, which site in the program space the action applies to, what counterfactual would falsify the lesson, what the goal's success predicate is, or which unseen environment will preserve the relation. Without a distinct verifier and a cross-environment contrast, permanence would be memorized overfitting, not capability. The blocker is not memory capacity; it is identification, scope, verification and synthesis under unseen hard cases.

## 4. Minimal sufficient plan (rejected ideas included)

Let `A` be the finite action partition under the current goal, `U` the unknowns that can change which action is admissible, `H` a scoped hypothesis distribution for an unknown, and `Q` a query. The agent computes the quotient `A / U` and derives `Q` from the undecided action IDs rather than trusting a supplied sentence. With a normalized hypothesis model it computes exact `EVPI(Q) = sum_h p(h) max_a u(a,h) - max_a sum_h p(h) u(a,h) - cost(Q)`; without probabilities it computes only a labeled worst-case decision-contrast bound. It deletes every query with non-positive value, open-ended completeness, a model dependency, a ready-made answer, a missing falsifier or a missing distinct verifier. It asks only the smallest admissible K1 query, recomputes relation terms from the current machine, and writes only a typed relation with variables, preconditions, falsifier, evidence hash and distinct verifier. Universal generalization requires a second independent contrast in a different environment. Nothing executes an environment action without a distinct verifier.

| Rejected idea | Why it is killed |
|---|---|
| Scan everything | Unbounded observation cost; atoms that cannot change action choice have zero VOI; project breadth measurement saturates |
| Learn everything / eventually learn all environments | Open world has no finite completeness certificate; WideSearch/DeepSearchQA show completeness and stopping are hard failures |
| Web as runtime perfect researcher | Runtime model/service would be K3; gated assets, stale pages, hidden state and source authority remain; web is K1 only |
| Save exact action trajectories | 2026 memory paper and project `LEARNING_DOES_NOT_ACCUMULATE` show negative transfer; exact actions rarely recur |
| Natural-language universal purpose parser by another model | Forbidden runtime model call; purpose must be bound to a typed goal effect and success predicate |
| Parameter updates from one experience | Violates zero-knowledge house; one trace cannot justify a weight delta; external store is inspectable/editible |
| Self-written independent pass | `AGENTS.md` rule 4; verification means someone else ran it |

## 5. Build

New zero-model module: `canonical/runtime/goal_directed_sufficient_knowing_v1.py`. It uses stdlib only, has no model/network/runtime imports, never executes actions, and exposes `evaluate(packet)` and `distill(experience, contrast)`.

New external empty store: `canonical/astra_runtime/state/GOAL_DIRECTED_SUFFICIENT_KNOWLEDGE_STORE_V1.json`. It holds no facts, relations, parameters or weights; it is inspectable and editable without retraining.

New contract tests: `canonical/tests/test_goal_directed_sufficient_knowing_v1.py`. They cover no-model static audit, empty external store, minimal query selection, irrelevant scan deletion, zero-VOI rejection, open-world completeness fail-closed, model/ready-made-answer rejection, scoped K1 fact binding, goal-change scope, distinct-verifier requirement, relation-only distillation, cross-environment contrast license, and rejection of exact trajectories/self-verification.

This is a deletion-first composition of already-owned mechanisms (goal quotient, JIT K1 boundary, global retrieval completeness firewall, relation grammar, distinct verifier) plus one compact new policy surface. No new runtime model, no parameter training, no external runtime dependency, no benchmark-specific solver, and no hidden/gated bodies.

## 5A. Runner-owned finite replay

- OIDC run: `45408866721`, attempt 1, job `138496906549`, conclusion `success` in 21s.
- Trigger head: `4a488af98d3daafb316f5c19ae3a53b2f0af1eb0`; runner receipt commit: `67a343f6`.
- Receipt: `canonical/verification/GOAL_DIRECTED_SUFFICIENT_KNOWING_RUNNER_RECEIPT_20261124_V1.json`.
- SHA-256 / sidecar: `a7cacaab194841ba744787686b8d7dd38eb3c14093c0523a3c2a22ff254402d3`.
- Receipt Git blob: `f25c2a54e7083d4cb62aee190d484ff09c80bd5a`; sidecar blob: `640bea643273dac23d40a17f060fccc6aca9d8ea`.
- OIDC `jti`: `1a8b7197-7788-4765-9c5e-043e913e0b06`; verifier identity is the distinct workflow ref plus run ID.
- Verified: 3 exact blobs, 16 tests, 16 measurement checks, one derived minimal query, exact EVPI, zero model calls, zero runtime network calls, zero parameter writes, zero environment actions, zero hard-benchmark tasks.
- Not verified: every item in the `not_verified` list of the receipt, including untouched hard benchmarks, arbitrary purpose, authored repair content, GUI/browser control, shipped-agent integration and §6.

The runner is a build-time verifier only. OIDC provenance never becomes a Brain runtime dependency and never changes terminal truth.

## 6. Honest tests and blockers

Sixteen local contract tests pass, including exact EVPI normalization, derived-question generation, store add/remove without parameter writes, open-world and model-source refusals, scoped relation-only distillation and cross-environment contrast licensing. A distinct GitHub Actions OIDC runner re-ran the exact pinned module/test/store bytes from `/tmp` under isolated Python, checked 16 measurement conditions, bound 3 exact blobs, verified zero model/network/parameter writes, and recorded a runner-owned receipt. These are finite regression/replay measurements only, not §6 hard-benchmark tests. The §6 test set remains unseen hard instances of OSWorld 2.1, SWE-Bench Pro V2 HARD-51, Terminal-Bench 4.1, WebArena-Verified/DeepSearchQA/WideSearch-class completeness problems and fresh arbitrary computer environments, run only by our own system with zero model calls and a distinct maintainer-style verifier.

**Fully user/external-authority-dependent blockers, logged once:** owner/gated access to OSWorld 2.1 task classes and complete assets, reachable self-hosted websites, provider VM image, pinned evaluator dependencies, maintainer-style verifier, and official hard-benchmark execution/§6 countersign. I am continuing on all other work and do not ask for them here.

No OSWorld task, reward vector, aggregate score, §6 verification, capability/family/terminal credit, PR, merge or terminal truth change is claimed. Final lightweight gates after the runner receipt passed 20/20 on the metadata state, including exact runner-receipt/OIDC binding, 22 legacy gates, 16 contract tests, 29 instrument tests, 31 combined zero-model Harbor tests, OBS/broker/reducer, no raw benchmark tasks and a clean tree. `truth.achieved=false`; §6 remains `NOT_MET`.
