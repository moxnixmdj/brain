# Own-model loop: EIG question wire, one-experience transfer, and honest §6 status — 2026-11-24

Status: **progress, not completion.** `truth.achieved = false`; §6 remains **NOT DONE**. This is a producer-run local experiment and regression record, not an independently verified frontier score, not an own-weights model qualification, and not a claim that arbitrary computer use has been solved.

## 0. All requirements read, and the date/branch interpretation

I reread the whole prompt as a new mission, including: own weights/architecture/agent, no runtime model calls, zero knowledge house, external instant-knowledge store, single-experience learning, arbitrary GUIs/browsers/SWE, natural language, cross-session persistence, counterfactual/victim cases, real understanding, exhaustive project-then-frontier research, first principles, "the best part is no part", ultimate-hard unseen tests, no hand-solving/leakage/borrowed outputs, one branch, merge only when complete, and the autonomous §5 loop until §6. I did not treat the repeated prompt as "continue"; I restated the binding requirements in the working commentary before acting. I asked no user questions. The system date **2026-11-24 UTC** is used; the prompt's `10/11/2026` is interpreted as November 2026. Work is entirely on active branch `arena/e7a4ed58-brain`; no branch change and no merge.

The only blocker invoked remains the previously logged physical/cost one: Docker, Podman, Harbor, Python 3.12, a disposable independent VM, OSWorld desktop, and required GPUs are absent in this sandbox. It is logged once here and in `FRONTIER_BENCHMARK_GATE_20261124_V1.md`; all other work continued to the next bottleneck.

## 1. §2 contradiction: adopted, verified, refined

**Default adopted:** forbidden are (a) parameters used as a lookup table of memorized world facts and (b) any runtime dependency on another model. Allowed are (a) an external, inspectable, editable, deletable store of knowledge/skills the system computes with and (b) learning that writes to that store from a single experience. The test is: knowledge outside weights; add/remove without retraining; weights hold only computed mechanisms.

**Verification this loop:** `canonical/astra_runtime/state/ONE_EXPERIENCE_CROSS_FAMILY_TRANSFER_V1.json` stores one computed procedure and source provenance digests. It stores no exact source binding and no target outcome. Removing the abstraction from a temporary copy makes `_load_abstract_rule` refuse; restoring the original makes it available again; a second Python process reproduces the same store digest. `written_to_weights: false`, `runtime_model_calls: 0`, `runtime_network_calls: 0`.

**Refinement, recorded rather than hidden:** an external store is necessary but not sufficient. A rule in a store is not knowledge until the goal oracle, current-environment preconditions, decoy separation, ambiguity refusal, and an independent verifier have acted on it. Unidentified readings are stored nowhere. Mechanism code still contains inductive bias; zero parameter writes is not zero architecture. The shipped system here is still **code plus external store**, not a trained own-weights model; `own_weights: false` is explicit in the receipt. Build-time web search and code editing are not runtime dependencies and are not counted as our capability.

## 2. Exhaustive project research and non-obvious names

The earlier exhaustive project pass counted 18,207 files and 440 top-level Markdown documents, including producer-run artifacts dated through `20261204`; I did not repeat that whole scan. Targeted re-inspection this loop confirmed the live bottleneck: `canonical/swe_kernel/perfect_algorithm_v1.py.right_question()` was still a novelty/closeness heuristic whose answer was logged, while `canonical/runtime/settlement_v1.py` already computed expected information gain over explicit hypotheses. `OWN_MODEL_RESEARCH_AND_NEXT_EXPERIMENT_20261124_V1.md` named the unrun preregistered source-experience→unseen-family transfer experiment as the earliest decisive experiment. `canonical/runtime/guide_precondition_v1.py` already resolved missing names from a guide's own statements with replay and decoy separation; `canonical/tools/the_guide_is_a_test_suite_v1.py` already harvested real stdlib transcripts and the interpreter's printed-output oracle.

Non-obvious project names inspected or re-located, so they are not rebuilt: `canonical/runtime/exact_information_gain.py`, `demonstration_version_space_v1.py`, `demonstration_version_space_v1.py`-adjacent `settlement_v1.py`, `root2_calibrated_settlement_scheduler_v1.py`, `contrast_selection_v1.py`, `applicability_v1.py`, `precondition_discovery_v1.py`, `instant_condition_store_v1.py`, `current_one_shot_projection_v1.py`, `one_shot_reality_closure_v2.py`, `one_shot_verified_closure_v1.py`, `one_shot_identifiability_probe_20261112.py`, `canonical/swe_kernel/instant_one_shot_learning_v1.py`, `canonical/swe_kernel/contrastive_oracle_bootstrap_v1.py`, `canonical/runtime/harbor_epistemic_agent_v1.py`, `canonical/runtime/harbor_experimental_vm_v1.py`, `canonical/runtime/harbor_container_solver_worker_v1.py`, `canonical/tools/swebench_verified_epistemic_adapter_v1.py`, `canonical/tests/test_miniwob_one_success_generalisation_v1.py`, `canonical/tests/test_a_refusal_must_learn_v1.py`, `canonical/tests/test_settled_is_computed_never_reached_v1.py`, and `canonical/tests/test_current_one_shot_*`. The project's own historical dead ends remain binding: exact recall, TF-IDF skill lookup, more demos, more primitives, more search budget, breadth as admission, and source-count "completeness" were already measured as insufficient.

## 3. Frontier research, used as input, not truth or runtime dependency

**Hardest-open benchmark landscape as of Nov 2026.** Terminal-Bench 4.0 has 66 hard terminal tasks and a 64.8% Claude Code + Opus 5.5 leader; Terminal-Bench 4.1 was introduced on Nov 9 with a 71.2% leader [1](https://www.morphllm.com/best-ai-coding-agents-2026). A separate November leaderboard reports Terminal-Bench 4.0 at 67.2% and SWE-bench Pro V2 at 99.4% / HARD-51 98.0%, i.e. nearly saturated, while SWE-bench Pro private commercial remains 51.5% [2](https://www.benchleader.com/benchmarks/coding). SWE-bench Pro is 1,865 tasks across 41 repositories with a 61.5%±3.1 public leader, but ~30% of its public tasks were flagged broken and its verifiers were measured accepting wrong / rejecting correct patches [3](https://www.morphllm.com/swe-bench-pro) [4](https://decodethefuture.org/en/ai-agent-benchmarks-2026/). A conflicting November aggregator claims 93% SWE-bench Pro [10](https://benchlm.ai/benchmarks/swe-bench-pro); this is an unresolved harness/split conflict, not a score we adopt. OSWorld 2.0 remains unsolved at 20.6% binary / 54.8% partial in one October survey [4](https://decodethefuture.org/en/ai-agent-benchmarks-2026/), while a later survey reports 44.33% binary / 77.67% partial under v2.1 scoping [5](https://fleeceai.app/blog/ai-agent-benchmarks-2026-explained). A November GitHub gap analysis ranks Terminal-Bench 4.0, Terminal-Bench-Science, HLE-Diamond, Agents' Last Exam, SWE-bench Pro V2, and OSWorld-V2 as the frontier additions and notes OSWorld-V2.1's heavy VM/assets requirements [6](https://github.com/Exgentic/eval-containers/issues/733). **Conclusion:** there is no single uncontested hardest benchmark; the defensible §6 gate is a battery with independent fresh verifiers, not a leaderboard snapshot. None was run here.

**Instant/continual learning.** External memory does not abolish the stability-plasticity problem; abstract procedural memories transfer more reliably than detailed trajectories, and negative transfer hits hard cases [2](https://arxiv.org/abs/2604.27003). MCCL argues memory should be judged by improved future actions, with forward-transfer and explicit negative-transfer rates, not retrieval accuracy [5](https://arxiv.org/pdf/2610.29357). PATH-Bench finds that experience utility depends on representation and task path, that transfer and retention dissociate, and that negative-dominant histories erode gains [3](https://arxiv.org/html/2608.01149v1). AgentCL finds held-out tasks necessary and memory can mildly interfere [7](https://arxiv.org/html/2606.02461v2). These are LLM-agent studies, not evidence about our no-model runtime.

**Active questioning / EIG.** EIG over explicit model hypotheses can support rule discovery, and EIG is entropy reduction over a hypothesis posterior [1](https://www.nature.com/articles/s41467-026-77209-5) [5](https://arxiv.org/pdf/2603.29003). But EIG can be counterproductive in open-ended program spaces: generator support, particle degeneracy, and proposal bottlenecks matter, and it can underperform simpler positive-test strategies on simple concepts [2](https://arxiv.org/html/2602.06818). Sequential visual active reasoning reports proposal-limited failures and high-EIG distractor traps [4](https://arxiv.org/html/2605.01345v1). BED-LLM uses an LLM to propose candidate questions and selects by EIG; that is an existence proof for the shape of the loop, not a permissible runtime dependency for us [7](https://en.papernotes.org/ICLR2026/llm_agent/bed-llm_intelligent_information_gathering_with_llms_and_bayesian_experimental_de/). Our design therefore refuses EIG on an open proposal space, keeps the space closed at two computed regimes, and executes the selected probe with a real oracle.

## 4. §3 verdict on instant learning, and the user's "perfect algorithm = model" idea

**True, bounded:** a durable, inspectable procedure can be derived from one verified experience and reused in a different, mechanically separated guide family when the environment supplies a refusal, an executable guide, and a printed-output oracle. This loop measured 4 independently verified target successes from one source experience, with 0 successes for empty/exact/shuffled/wrong/foreign memory controls.

**False as a universal claim:** one finite advanced coding action or experience cannot permanently identify an arbitrary unseen rule. Two environments can agree on every observed transition and require opposite next actions; without a hypothesis space, discriminating probe, sound verifier, action grounding, perception, hidden-state model, and provenance, "learn it once" is an unjustified quantifier jump. A single experience may contain many transitions but still lack contrasting failures and changed preconditions. Raw traces are also a measured source of negative transfer [2](https://arxiv.org/abs/2604.27003) [5](https://arxiv.org/pdf/2610.29357).

**Unproven / missing:** hardest-open Nov-2026 SWE and computer-use tests, arbitrary unseen GUI/browser environments, natural-language grounding, own trained weights, container-local `open_model().solve()` confinement, independent cloud verifier, GUI/DOM oracle, and end-to-end qualification. Real understanding is not demonstrated; this loop demonstrates a computed mechanism that uses an oracle.

**Evaluation of the idea:** the productive part is the loop `goal → environment refusal → right question → external guide → real probe → verification → generalized procedure`, not "the model already knows". The limiting factor is not a bigger fact warehouse; it is *which question can be asked, which hypotheses are representable, which probes are safe, and which oracle can reject a false success*. This is why we choose **goal-directed important learning** over learn-everything eventual generalization: learn-everything has no bounded admissibility criterion, stores unlabeled readings, and measured negative transfer concentrates on hard cases [3](https://arxiv.org/html/2608.01149v1) [7](https://arxiv.org/html/2606.02461v2).

**What defines what to know:** the **goal** here is reproducing the current guide's printed output; the **environment** is the interpreter's `NameError` plus the current guide's statements; the **need** is the refused name and candidate statements that bind it. Nothing about the target family is placed in weights. **What to save:** the computed procedure, source provenance digests, and outcome-class digests only. **What to generalize:** the procedure, not the source action. **What not to save:** exact source action replay, target bindings, guide answers, target outcomes, unidentified readings, weights. Ambiguous bindings and bindings not separated by a machine-made wrong input are refused.

## 5. One ultimate minimal plan, rejected ideas, and the kill attempt

The single plan is in `OWN_MODEL_PREREGISTERED_TRANSFER_20261124_V1.md`, frozen before the formal receipt (with a logged pre-run amendment). It reuses existing components instead of adding a learner: `settlement_v1.VersionSpace`/`settle` for EIG, `guide_precondition_v1` for candidate ranking/replay/decoy separation, `the_guide_is_a_test_suite_v1` for real transcripts, and `perfect_algorithm_v1.run` for the composed scan→question→plan→act→verify loop. Rejected first choices and reasons: another runtime model (hard constraint), exact trace replay (cannot transfer), larger skill library (coverage is not the measured bottleneck), pretraining facts into weights (forbidden warehouse), EIG over an open proposal space (measured generator-support failure [2](https://arxiv.org/html/2602.06818)), source-count completeness (counts do not prove relevance or agreement), benchmark-specific workflows (leakage), and more demos/primitives/search (project dead ends).

**Kill attempt:** the preregistration fixed target families, arms, thresholds, budgets, independent verifier, restart, contradictory/changed-precondition victims, and no-tuning rule before the formal receipt. EIG is allowed only on a closed ≤24-hypothesis space with positive-gain probes; zero gain, open space, missing oracle, and evidence outside the space are named refusals. Counterfactual arms must produce zero false successes. The implementation was smoke-tested to `/tmp` before the formal run; no formal arm results were recorded during that check. No threshold, arm, target family, or implementation was changed after the formal receipt.

## 6. What was built

| File | Minimal purpose |
|---|---|
| `canonical/runtime/active_question_v1.py` | EIG probe policy over a closed version space; executes and observes the chosen question; refuses open/blind spaces; no facts, weights, model, or network. |
| `canonical/swe_kernel/perfect_algorithm_v1.py` | Optional `question_space` / `probe_keys` / `probe_oracle` / `probe_budget` arguments wire EIG into `right_question` and `run`; the selected probe is executed and its observation updates the posterior. |
| `canonical/tools/one_experience_cross_family_transfer_v1.py` | Preregistered transfer instrument, real stdlib guide cases, five controls, learned abstraction, counterfactual victims, independent `doctest` process, external store, restart check, receipt. |
| `canonical/tests/test_active_question_and_one_experience_transfer_v1.py` | Mechanism regressions for EIG policy/ask, composed `right_question`, open/blind refusal, store editability, and no-exact-action boundary. |
| `canonical/astra_runtime/state/ONE_EXPERIENCE_CROSS_FAMILY_TRANSFER_V1.json` | External inspectable store: one procedure + provenance digests, no exact source binding or target outcome. |
| `canonical/verification/ONE_EXPERIENCE_CROSS_FAMILY_TRANSFER_20261124_V1.json` | Formal receipt with all arms, costs, refusals, EIG posteriors, independent verifier run refs, restart run ref, verdict, and §6 NOT DONE. |
| `OWN_MODEL_PREREGISTERED_TRANSFER_20261124_V1.md` | Frozen protocol and rejected ideas. |

## 7. Hard honest tests and measured results

The formal command `python3 -m canonical.tools.one_experience_cross_family_transfer_v1` completed in **6.6553 s**. It used 29 real interpreter-refusal cases across `stdlib:statistics`, `stdlib:enum`, and `stdlib:pickletools`; 24 had an identified `NameError` and 5 had no identified question and were reported as refusals, not dropped. One `difflib` source experience (`question = s`, 8 candidates, 8 probes, 1 reproducing, 0 unidentified) yielded the stored procedure and five source counterfactual observations.

| Arm | Cases | Extra interpreter probes | Independent verifier processes | Replayed matches | Independently verified | False successes |
|---|---:|---:|---:|---:|---:|---:|
| EMPTY | 29 | 0* | 0 | 0 | 0 | 0 |
| EXACT_SOURCE_TRACE | 29 | 29 | 0 | 0 | 0 | 0 |
| SHUFFLED_SOURCE | 29 | 29 | 0 | 0 | 0 | 0 |
| WRONG_SOURCE | 29 | 29 | 0 | 0 | 0 | 0 |
| FOREIGN_SOURCE | 29 | 29 | 0 | 0 | 0 | 0 |
| LEARNED_ABSTRACTION | 29 | 72 | 4 | 4 | 4 | 0 |
| CONTRADICTORY_GOAL | 4 victim cases | 14 | 4 | 0 | 0 | 0 |
| CHANGED_PRECONDITION | 4 victim cases | 0 | 4 | 0 | 0 | 0 |

\* The EMPTY arm reuses the real refusal already recorded while enumerating cases; the receipt states this rather than pretending it ran 29 new probes.

- Local transfer hypothesis: **PASS**, by the frozen criteria. 4 independently verified successes, best control 0, gap 4, 0 contradictory/changed-precondition false successes, 0 ambiguous/unidentified admissions, cost ratio **2.6207×** exact-cache probes (ceiling 8×), restart digest reproduced, external-store removal/refusal and restore both verified.
- EIG wire: **PASS locally**. 4/4 resolved cases selected a 1.0-bit positive-gain probe, executed it against the real interpreter, changed posterior from `{TRANSFER: 0.5, NON_TRANSFER: 0.5}` to `{TRANSFER: 0.999001, NON_TRANSFER: 0.000999}`, and `SETTLED` with winner `TRANSFER` in 1 query. The composed `perfect_algorithm_v1.run` wiring was exercised on the first resolved case: `PASS__PERFECT_ALGORITHM_RUN`, `PASS__GOAL_VERIFIED_OBSERVED`, EIG answered, 1.0-bit gain, posterior changed, rule not persisted (`NO_FRESH_INSTANCES_OFFERED__NOT_PERSISTED`). This proves the answer is used in the composed loop, not merely logged.
- Independent verifier: 12 fresh `python3 -I -c doctest.DocTestParser/DocTestRunner` processes, different from `_python_example_ok` and `compare`; 4 success run refs, 4 contradictory run refs, 4 changed-precondition run refs are recorded. No human supplied an answer; the guide's printed output remains the oracle.
- External-store boundary: removal of the abstraction from a temporary copy refuses; restore is available; no weight write; second process `run_ref ee4572081da7783b` reproduced digest.
- Regression suites: `57 passed in 15.21s` on the five immediately affected test files; `201 passed, 2 skipped, 1 warning in 62.66s` on all 15 affected modules discovered by import reference plus the prior witness suite. No known-good control guide suite was rerun. `python3 -m py_compile` succeeded for all three changed Python modules.

**What these tests are not:** they are real stdlib-guide failures, not a hidden frontier benchmark; the target families are mechanically separated, not arbitrary unseen GUI/browser environments; Python's own guide is an unusually strong instant-knowledge source with executable examples and printed answers. The receipt's `failed_or_unproven` list states this. A local pass is progress, not §6.

## 8. §6 status, next bottleneck, and loop continuation

§6 is **NOT DONE** and `truth.achieved` remains `false`. There is no hardest-open Nov-2026 SWE/computer-use score, no SWE-bench Pro / Terminal-Bench 4.0 / OSWorld 2.0 / FrontierSWE v2 run, no unseen arbitrary environment, no single-experience universal-learning qualification, no own-weights-only end-to-end qualification, no GUI/DOM oracle, and no independent cloud verifier with a different run reference. No completion claim is made.

The next single bottleneck is **container-local `open_model().solve()` confinement plus an independent fresh verifier and run reference**. The live adapter records an `EPISTEMIC` mode but `open_model().solve()` does not special-case it; Harbor is experimental; `confinement_admitted` must not be driven by an adapter flag or caller flag; verifier-mode shared environments are not independent; `solve()` can have side effects. After that seam is real, run the hardest-open Nov-2026 battery with the ranked additions and integrity caveats above, then a GUI/DOM oracle and OSWorld VM. The Docker/Podman/Harbor/Python-3.12/VM blocker stays logged once; work switches to the next-best bottleneck rather than ending the turn.

## 9. Reproduce

```bash
python3 -m pytest -q \
  canonical/tests/test_active_question_and_one_experience_transfer_v1.py \
  canonical/tests/test_perfect_algorithm_v1.py \
  canonical/tests/test_perfect_algorithm_probe_restore_v1.py \
  canonical/tests/test_the_guide_is_a_question_about_a_missing_name_v1.py \
  canonical/tests/test_the_check_is_the_object_the_action_produced_v1.py
python3 -m canonical.tools.one_experience_cross_family_transfer_v1
python3 -m canonical.tools.one_experience_cross_family_transfer_v1 \
  --verify-store canonical/astra_runtime/state/ONE_EXPERIENCE_CROSS_FAMILY_TRANSFER_V1.json
```

The first command prints `57 passed`; the formal instrument writes the receipt and store; the third command verifies restart in a separate process. All commands bind to local interpreters and temporary directories only; they make zero model calls and zero network calls.
