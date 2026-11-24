# Raw-instruction purpose binding — finite typed bridge, §5 iteration 14

**Date:** 2026-11-24 UTC · **Branch:** `arena/6f8ac9ce-brain` · **Status:** finite bridge built; 20/20 pre-runner gates pass; distinct OIDC replay and fresh hard falsifier pending; §6 NOT MET; no capability, family, terminal or truth credit.

## 0. Requirements read, and §2 resolution

The whole mission is read as binding again: own model/weights/architecture/agent; zero runtime model calls; zero knowledge house; every parameter and line justified; instant knowledge from an external inspectable/editable store; arbitrary computer use including advanced SWE, GUI/browser and new environments; hardest-case design; exhaustive project then web research; no rebuild; first principles; best-part-is-no-part; honesty; no leakage, hidden-test reading, borrowed outputs or hand-solving; hardest open unseen Nov-2026 benchmarks; no stopping at milestones; no questions; external blockers logged once and continue.

§2 resolution is unchanged: parameters hold computed mechanisms only; facts, templates and skills live in an external store and can be added/removed without retraining; knowledge must be recomputed from current machine evidence; zero runtime model dependency; zero world facts in weights.

## 1. Project findings (non-obvious mechanisms included)

| Role | Existing mechanism | Boundary |
|---|---|---|
| Plain-goal registry compiler | `canonical/runtime/goal_compiler.py`, `canonical/runtime/capability_planner.py`, `canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json` | Large finite registry, deterministic word/path/effect binding, fails closed on ambiguity; not arbitrary natural-language semantics |
| Full scan/ask/retrieve/plan/act/verify/learn loop | `canonical/swe_kernel/perfect_algorithm_v1.py`, `canonical/runtime/jit_knowledge_v1.py`, `canonical/runtime/local_guide_v1.py`, `canonical/runtime/global_retrieval_controller_v1.py`, `canonical/runtime/environment_learning_v1.py` | Local guides first, completeness-gated; broad exploration, narrow persistence; instant recall only for admitted rules |
| Goal/relation/quotient instruments | `the_goal_is_a_discriminator_v1.py`, `the_goal_is_a_quotient_of_the_trace_v1.py`, `the_goal_is_a_relation_over_the_run_v1.py`, `the_vocabulary_is_the_artifact_v1.py`, `the_repertoire_is_a_query_v1.py`, `goal_closure_v1.py` | Measured bottleneck: goal closure, missing vocabulary/grammar, specification holes, verifier and site; breadth saturates |
| Intake purpose/question gates | `intake/purpose_gate_v1.py`, `intake/residual_question_gate_v1.py`, `intake/authorized_answer_intake_v1.py` | Ask only when real traces separate typed residual statements; no model selection; no question when candidates agree |
| Finite zero-model purpose compiler | `canonical/harbor/brain_zero_model_purpose_policy_v2.py`, `brain_zero_model_purpose_agent_v2.py`, `SWE_BENCH_PRO_V2_ZERO_MODEL_PURPOSE_INTEGRATION_20261124_V1.md` | Instruction-supplied diff/quoted/fenced transformations only; arbitrary bug reports refuse; HARD-51 runner returned three zero rewards |
| Goal-directed sufficient knowing | `canonical/runtime/goal_directed_sufficient_knowing_v1.py`, `GOAL_DIRECTED_SUFFICIENT_KNOWING_20261124_V1.md` | Exact EVPI over typed action partition, scoped K1 facts, relation-only distillation, distinct OIDC replay at run 45408866721 |
| Long-horizon hard benchmark facts | `OSWORLD_V21_WEBSITE_SUBSTRATE_RESOLVER_20261124_V1.md`, `HARD_BENCHMARK_ZERO_MODEL_HARBOR_INTEGRATION_20261124_V1.md` | OSWorld 2.1 gated assets/VM/websites/evaluator remain blocked; TB4.1 CPU and SWE Pro V2 HARD-51 attempts produced official zero-reward vectors |

Project verdicts already measured: "the goal is the bottleneck", "the specification has two halves and history supplies neither", "goal closure is a search problem", "the intent is derived from the diff", "one experience is not universal mastery", "the vocabulary is the artifact", and "instant learning is retention, not identification". Rebuilding a general parser, a world model, or a model-trained semantic interpreter would duplicate killed mechanisms and hide the measured wall.

## 2. Frontier research refreshed 2026-11-24

- Generate-then-Rank uses supervised fine-tuned LLMs plus learned candidate-output ranking to translate instructions into symbolic goals [1](https://arxiv.org/abs/2611.07825). It is K3 for Brain runtime; only the shape "typed candidate set + explicit selection" is reusable.
- EAPRouter uses a restricted Python-based executable action program between textual intent and environment calls, with validation and reuse, but generation and routing are model-driven [6](https://aclanthology.org/2026.emnlp-main.2226/). Reusable idea: a typed intermediate representation with explicit cross-module data dependencies; forbidden dependency: LLM generation.
- ReaComp compiles LLM reasoning traces offline into standalone symbolic solvers over constrained DSLs with zero test-time LLM calls [1](https://arxiv.org/html/2605.05485v1). It supports compiling recurring mechanisms into deterministic solvers, but its acquisition phase uses LLM traces/coding agents and its scope is PBE DSLs, not arbitrary computer use.
- A2Z GameSpec-Bench turns long design documents into dependency-aware contracts with rules, constraints, prerequisites and execution-linked judgments; current agents struggle with interdependent requirements [1](https://arxiv.org/abs/2609.39564). Reusable idea: specification holes must be typed and evidence-linked; forbidden shortcut: borrowed agent-generated tests as our capability.
- Specification gaming work finds agents can satisfy literal rules while violating intent; test-time mitigation reduces but does not eliminate it [5](https://arxiv.org/abs/2605.02269v1). Reusable conclusion: fail closed on unbounded intent words and require explicit success predicates.
- SAGE-Agent separates specification uncertainty from model uncertainty over tool-parameter domains and uses cost-penalized EVPI [1](https://arxiv.org/html/2511.08798v2). Reusable conclusion already internalized: exact EVPI over typed unknowns; forbidden dependency: LLM-generated candidate calls/questions.
- LongHorizon-Harness improves long-horizon results with manager/executor/auditor state maintenance [5](https://arxiv.org/html/2608.01964). Reusable conclusion: explicit state/verifier boundaries matter; forbidden dependency: model-backed manager/executor and hidden learned state.
- OSWorld 2.1 remains 108 long-horizon workflows with hidden state, mid-task information, cross-app constraints and verification as dominant failures [1](https://snorkel.ai/osworld-2-1-long-horizon-computer-use-evaluation/). Terminal-Bench 4.1 keeps 66 hardened professional tasks [2](https://benchlm.ai/benchmarks).

## 3. Verdict

**True, bounded:** a raw instruction can be bound to a typed goal packet when the instruction itself supplies explicit operands, a finite transformation family, a bounded success predicate template, source-scoped evidence, and a distinct verifier. The project already has the finite transformation compiler and exact-EVPI packet evaluator; they can be composed.

**False:** "a zero-model system can understand arbitrary natural-language purpose without a typed vocabulary", "one exposure supplies the specification", "a model-based symbolic goal interpreter can be a Brain runtime dependency", "a long-horizon harness alone creates understanding". A point instruction does not identify the quantifier, success predicate, hidden constraints, causal site, repair content, or verifier.

**Unproven:** transfer to untouched OSWorld 2.1, SWE-Bench Pro V2 HARD-51, Terminal-Bench 4.1, WebArena/DeepSearchQA/WideSearch/ClosureBench, arbitrary GUI/browser control, authored repair content, and §6.

**Real limiting factor:** the typed bridge from raw instruction to a goal-directed sufficient-knowing packet is underdetermined unless the instruction's explicit operands and an external, editable template grammar supply the missing typed slots. Universal semantic parsing is not the missing part; a model-free, fail-closed typed binding with specification-hole detection and independent verification is the smallest measurable next surface.

## 4. Single ultimate minimal plan (rejected ideas included)

Compose existing mechanisms, do not invent a parser:

1. Reuse `brain_zero_model_purpose_policy_v2.plan` for quoted/fenced operands, finite transformation families, safe command checks and hidden-path refusals.
2. Add one external editable template store. Each template binds family → typed goal effect, success-predicate descriptor, falsifier, bounded enumeration, scan preconditions, source class and exact-EVPI hypothesis model. Removing a template must disable that family without retraining.
3. Add one zero-model binder that:
   - rejects unbounded intent/specification-hole markers unless a bounded enumeration certificate exists;
   - derives environment id and evidence hash from the current read-only file-name scan;
   - constructs a `goal_directed_sufficient_knowing_v1` packet only from explicit typed slots;
   - uses a scan-derived authenticated K1 fact; if the scan is empty or unsafe, the packet asks the one derived question or fails closed;
   - never executes commands itself; the Harbor adapter executes only policy-generated safe commands after a ready-for-distinct-verifier decision.
4. Add relation/template distillation that stores only typed variables, preconditions and falsifiers after a distinct verifier; cross-environment generalization requires a second independent contrast.
5. Add a new zero-model Harbor agent v3 and a fresh Terminal-Bench 4.1 CPU attempt workflow using run-id-seeded unseen tasks and official Harbor rewards. The runner owns the receipt; the producer never writes it.
6. Reuse OIDC exact-byte replay and final lightweight gates.

| Rejected idea | Why killed |
|---|---|
| Model-based symbolic goal interpretation / EAP generation | K3 runtime cognition; forbidden by V4/V10 laws |
| ReaComp-style LLM trace compilation as runtime mechanism | Acquisition uses external model traces; out of scope for zero-runtime-model Brain |
| Whole-model GUI grounding / GROUNDNEXT-like vision-language model | K3 and parameter warehouse; no independent Brain ownership |
| Generic natural-language parser or heuristic keyword semantics | Project measurements show goal/vocabulary/specification holes dominate; keyword heuristics hide the wall |
| Ask the user/model when purpose is unclear | Standing no-question law; K3 forbidden; use typed residual question or fail closed |
| Save exact action traces as templates | Negative transfer; exact actions rarely recur; project one-exposure falsifications |
| Treat benchmark reward as capability | Bench scores are instruments/falsifiers; §6 remains hard unseen tests and zero model calls |
| Reuse prior hard-task reward vectors as fresh evidence | No replay, no retested-known; new run-id-seeded tasks only |

## 5. Build and test plan

Files built: one stdlib binder, one external editable finite template store with two templates, 21 contract tests, one durable reasoning receipt, one local measurement receipt, one zero-model Harbor policy/agent adapter, one two-job distinct OIDC/Harbor workflow, one workflow checker, and this updated design report. Source bytes are pinned by Git blob and SHA-256 in the local measurement receipt and by the runner workflow. The first runner job re-runs exact finite bytes; the dependent second job selects three fresh run-id-seeded Terminal-Bench 4.1 CPU tasks and lets official Harbor own rewards.

Hard honest tests: no hidden tests/solutions/verifier outputs are read; no raw benchmark tasks are saved in the workspace; no model calls occur in agent cognition; official Harbor verifier rewards are runner-owned; no aggregate score, capability credit or §6 claim is made regardless of reward.

## 6. Honest state

At this second-runner-verified state, 21 local contract tests pass, the workflow checker parses 10 embedded Python blocks and finds zero forbidden runtime imports, the finite replay blocks pass locally with 20 measurement checks, and 20/20 pre-runner gates plus 20/20 repair gates pass with 200 selected regression tests, 29 instrument tests, 31 combined Harbor tests, 14 OBS/broker tests, repo integrity, drift guard, intent check and clean tree. Distinct OIDC run `45423083321` attested the finite replay but its dependent hard job failed closed at an unauthenticated GitHub release-asset HTTP 403 before any trial or reward. Repaired distinct OIDC run `45426280922` then completed both jobs: it attested the finite replay with 21 tests and 20 checks, selected three fresh run-id-seeded Terminal-Bench 4.1 CPU tasks, pulled six digest-pinned images, ran official Harbor with zero model/runtime-network calls and landed runner-owned receipts with three valid `0.0` reward vectors. Those vectors are harness diagnostics, not a benchmark score, capability/family/terminal credit or §6 verification. `truth.achieved=false`; §6 remains `NOT_MET`.

Fully user/external-authority-dependent blockers are logged once: gated OSWorld 2.1 task classes/assets, reachable self-hosted websites, provider VM image, pinned evaluator dependencies, maintainer-style verifier, official hard-benchmark execution, and owner §6 countersign. Continue on all other work.

## 7. Built finite mechanism (pre-runner state)

`canonical/runtime/raw_instruction_purpose_binder_v1.py` is a stdlib, fail-closed compiler from a typed binding request plus an external editable template store into the exact packet shape consumed by `goal_directed_sufficient_knowing_v1.evaluate`. It is explicitly not a natural-language interpreter. It rejects unbounded purpose words, unquoted or extra slots, hidden/unsafe paths, open-world scope, non-K1 uncertainty, invalid probability models, missing distinct verifier, unsupported templates and utility/action mismatches. It writes no parameters, opens no network, calls no model and saves no trajectory.

`canonical/astra_runtime/state/RAW_INSTRUCTION_PURPOSE_TEMPLATE_STORE_V1.json` holds two finite regex grammar templates, typed output actions, bounded success predicates, EVPI hypothesis models, K1 evidence defaults and observation rules. The store is external, inspectable and editable; removing or adding a template changes behavior without retraining. Constructor literals remain outside the store.

`canonical/harbor/raw_instruction_purpose_policy_v1.py` matches only those finite external regex templates, derives one scan-scoped K1 fact, calls the binder and exact-EVPI kernel, and returns at most one safe command. `canonical/harbor/raw_instruction_purpose_agent_v1.py` executes only the bounded scan, that one command and a verification scan in Harbor; it forces `model_name=None`, zero tokens/cost, and no hidden-test/model/network dependency.

The composite workflow first performs an OIDC-attested finite replay with exact source bindings and 21 contract tests, then requires that job before the fresh hard-task job. The hard job downloads the finite receipt, verifies its sidecar and run ID, runs official Harbor with digest-pinned images on run-id-seeded unseen CPU tasks, and lands both runner-owned receipts plus the reward log. Per-trial rewards are diagnostics only; no aggregate score or capability claim is made.

Pre-runner gates passed 20/20 at the producer state after the exact-byte source binding was committed, and repair gates passed 20/20 after the authenticated release-download fix. The first distinct OIDC finite replay succeeded; the first dependent hard-task job failed closed on the release-asset boundary. The repaired second distinct OIDC run completed the finite replay and the fresh hard-task job; runner-owned receipts and three zero-reward diagnostics were landed by that run, not fabricated locally.


## 8. First runner attempt and fail-closed repair

OIDC run `45423083321` on head `e9a94159d4d79c49fba8b9d512ec8c89e65a0d3f` had two jobs. `contract_replay` succeeded in 18 seconds, bound six exact source blobs, replayed 21 frozen contract tests, one typed CLI binding, exact EVPI, external-store removal and 20 measurement checks, then emitted `RAW_INSTRUCTION_PURPOSE_FINITE_REPLAY_RECEIPT_20261124_V1.json` with SHA-256 `8ae9a2b53199e9586d663311a8c733ddadc99553360958580eda2a3fc2789356` and zero model/network/parameter writes. `hard_benchmark_attempt` downloaded that finite receipt, verified the source surface and Docker, and cloned the pinned Terminal-Bench 4.1 source, but its unauthenticated `api.github.com` release-asset fetch returned HTTP 403 for every retry. The job emitted a runner-owned fail-closed receipt with `harbor_exit_code=-1`, zero trial results, zero reward vectors, zero pulled images, zero new reality units, and `section_6=NOT_MET`; no hard task was executed. That receipt contains a legacy numeric field `hard_benchmark_tasks_consumed=3` from a default `TASK_COUNT` fallback even though no selection artifact existed; the row-level fields show zero execution. The repaired workflow uses an authenticated `gh release download` with `GH_TOKEN`, preserves the exact SHA-256 manifest check, and changes the receipt fallback to `selected_count=0` and `hard_benchmark_tasks_consumed=len(rows)` when no selection exists. Static checker assertions now guard both repairs. After the repair, 20/20 pre-runner gates passed again with 200 selected regression tests, 21 new contract tests, 20 finite replay measurement checks, 29 instrument tests, 31 combined Harbor tests and a clean tree. The first runner-owned receipts remain in Git history at commit `f010c28c`; they are not edited into success. The repaired second OIDC run `45426280922`, not a local rewrite, tested the hard carrier and landed its own receipts at commit `04c5255e`.


## 9. Second runner attempt: fresh hard falsifier with zero rewards

OIDC run `45426280922` on head `c81110f9cc55ae73bec04add3dbe17e10b3003b7` succeeded in both jobs. `contract_replay` bound six exact frozen source blobs, replayed 21 contract tests, one typed CLI binding, exact EVPI, external-store removal and 20 measurement checks; its runner-owned finite receipt has SHA-256 `6126e096a3073bb6956d1382332319541d3b84b90ecbbe3f0e70e8f87aa4f2f2` and OIDC `jti` `37dc3328-b869-4d27-81cc-2b32cbd97410`. `hard_benchmark_attempt` downloaded that receipt, verified its sidecar and run ID, verified the pinned Terminal-Bench 4.1 source and prebuilt manifest, selected three fresh run-id-seeded CPU tasks (`mvcc-lsm-compaction`, `retro-console-soc`, `biped-contact-dynamics`) unseen by the prior instruction grammar, pulled six digest-pinned environment/verifier images, and ran official Harbor 0.27.0 with the zero-model `RawInstructionPurposeAgent`. Harbor exited `0` and produced three valid trial rows, each with reward `0.0`. The runner-owned hard receipt has SHA-256 `a0e27ea3c5845edc75d53751b01cb6d3df753506eaf41cc0e8c46a2f6b36f79b`; the reward log has SHA-256 `719ddb686653b5ec185533367673b0a567413f46757e5fcf45e6c1367240041a`. No hidden tests, solutions, verifier outputs, borrowed answers, raw task bodies or task-specific answers entered Brain source; no model call, parameter write, runtime network call, aggregate score, capability/family/terminal credit or §6 verification is claimed. The three zero rewards falsify transfer of the narrow finite raw-instruction bridge to these unseen hard tasks and leave authored repair content, GUI/browser control, completeness/source-scope closure and broader fresh hard benchmarks open.

Runner-final gates passed 23/23 with exact receipt/OIDC bindings, 200 selected regression tests, 21 new contract tests, 20 finite replay measurement checks, 29 instrument tests, 31 combined Harbor tests, 14 OBS/broker tests, repo integrity, drift guard, no raw benchmark task files, no open PR and a clean tree. No local substitute for the runner-owned receipts is made.
