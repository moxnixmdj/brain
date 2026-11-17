# The bottleneck: grounded feedback, not permanent replay

**17 November 2026. Status: research and decision, not a capability claim.** No external
model was invoked as a component, teacher, or solver. No benchmark was run in this research
pass, no known win was re-tested, and no new weights were created. Existing numbers below
are producer-reported measurements from the current tree, not independent verification.
Research is necessarily incomplete; the cited sources are evidence, not guarantees.

## Answer

The useful part of the proposition is real: an agent can preserve experience outside its
weights and reuse a verified rule in a new state, sometimes much more efficiently than
repeating the whole discovery process. It does **not** follow that one example uniquely
specifies the rule, the rule remains valid as the world changes, or skills compose safely.
It does not imply all coding, all computer use, perfect weights, or sentience.

**Best-supported shared bottleneck:** obtaining and using sufficiently discriminating,
state-grounded feedback for choosing, testing, and safely reusing a proposed behavior. Call
this the *observation–verdict loop*: observe the consequential state, propose a candidate,
choose a discriminating intervention, check the resulting effect, and retain a scoped
hypothesis only while its evidence and preconditions hold. This is a research priority,
not a proof that repairing one component would solve every task. Some tasks need a proposal
that the system cannot currently express, new sensors, permissions, specification, or
irreducible information from a user; an excellent verifier alone cannot invent them.

## First principles

1. A single successful trace generally has many consistent explanations. For example, a
   click may succeed because of a label, location, hidden state, or a coincidence. One
   cannot distinguish rules that make identical observations until a state is reached in
   which their predictions differ. Chosen observations can reduce this uncertainty; they
   cannot recover facts unavailable to every permitted observation.
2. Storage is not validation. A content-addressed record makes bytes retrievable and
   tamper-evident relative to its hash; it does not make the record true, current, relevant,
   authorized, or usable. The user-requested instant-knowledge source is valuable as an
   inspectable memory, not a substitute for grounded action and verification.
3. A successful test is evidence for its tested behavior, not proof of all behavior.
   Using the same cases to search and to certify the result risks overfitting. Even a
   physically separate verifier can be wrong, incomplete, inaccessible or gamed.
4. A step's success does not establish a sequence's success. Later actions may invalidate
   earlier effects, or environment changes may invalidate preconditions. A lasting memory
   needs scoped applicability, provenance, revalidation, revocation, and an effect check.
5. No-free-lunch intuition is not a proof that progress is impossible: prior structure and
   tools can make specific families tractable. But no finite test proves perfection on
   arbitrary tasks, and no one can honestly promise the globally optimal research path.

## What is already in this tree

- `canonical/runtime/contrast_selection_v1.py` and `world_probe_v1.py`: candidate
  discriminating observations and world probes. Reuse rather than building another selector.
- `canonical/runtime/acquired_operator_memory_v1.py`, `applicability_v1.py`, and
  `fact_entailment_v1.py`: stored examples, scoped applicability and fact checking.
- `canonical/swe_kernel/effect_contract_composition_v1.py` and
  `proved_composition_v1.py`: test compatibility and preservation across composed effects.
- `canonical/swe_kernel/zygote_worker_pool_v1.py` contains distinct execution paths.
  `ZygotePrewarmedPool.run_isolated` forks with shared filesystem, network, credentials and
  kernel, computes a deadline but does not enforce it before blocking on pipe reads and
  `waitpid`; it is **not** a reliable timeout or adversarial security boundary. The separate
  `screen_python_candidates_cow` delegates to a namespace/seccomp broker; that path has
  additional confinement and wall-time controls, but its suitability for adversarial use,
  its test-runner semantics, and final verification need an independent audit. Neither is
  a justification for running this branch's in-process synthesizer on untrusted code.
- `canonical/tools/judge_the_judge_v1.py` and
  `canonical/verification/JUDGE_THE_JUDGE_20261117_V1.json`: producer audit of the cheap
  QuixBugs judge. It reports 31 real-judge reference passes, 7 naive false rejections,
  2 repaired by generator materialization, and 5 still inadmissible under its audit. This
  calibration reads reference answers **for the separate audit only**; a solver must not
  receive them. Passing one correct reference and failing one defective program is necessary
  calibration evidence, not proof of verifier correctness for all candidates.
- `canonical/verification/ONE_CASE_CHOSEN_NOT_ASSUMED_20261117_V1.json`: on the 23 tasks
  the producer measured, first-case screening admitted 19 candidates of which 4 passed the
  corpus pytest; the chosen-case arm admitted 21 of which 13 passed; the all-case arm admitted
  16 of which 16 passed. These are corpus-test passes, not independently established
  semantic correctness. Later judge audit qualified the earlier space-coverage interpretation.
- `SITE_GENERAL_EXPRESSION_SYNTHESIS_20261117_V1.md` and its receipt describe the current
  branch experiment. Its grammar was designed after inspecting four answer keys, and its
  search and final corpus pytest used the same published examples. Four test passes are
  **in-sample** evidence, not a blind capability or generalization measurement. The tool
  executes Python in-process, uses signals rather than process isolation, and materializes
  generators unboundedly; it is not a safe sandbox. No new hard-open result is claimed here.
- `canonical/runtime/derived_text_candidate_v1.py` derives some answers not literally present
  in a page. The related MiniWoB measurement is bounded, not evidence of universal page
  understanding. `canonical/swe_kernel/weight_update_admission_v1.py` already supplies an
  admission gate for any future weight experiment; no update is justified by storage alone.

## Corrections on three specific claims

- **One experience:** a repeat of exactly the same fact vector adds no separating fact;
  this does not rule out new interventions or priors. The tree's
  `INSUFFICIENCY_CERTIFICATE_20261113_V1.json` is a certificate about **conjunctions of
  observed positive facts on its finite evidence**, not a proof that every hypothesis class
  or every kind of repeated experiment is incapable of learning. Its real-repair witness
  contains two successes and two failures; its separate filename-sensor case illustrates
  an actual missing distinction. The certificate's own probe has the precise theorem.
- **~2.2% replay:** some tree reports present this as a measured SWE-bench Verified
  result, but `THE_VERIFIED_INDEX_IS_THE_BOTTLENECK_20261116_V2.md` identifies it as an
  owner-supplied premise. This review did not find an underlying reproducible experiment
  establishing the figure. Do not use it as a measured capability or universal replay
  ceiling. The qualitative distinction between replay and synthesis does not depend on it.
- **Missing object-suite observables:** `repair_where_the_suite_is_the_observable_v1.py`
  already tries the corpus's test file as an observable for the nine non-JSON tasks; its
  receipt reports zero repairs, six with no screen survivor and three with collection
  errors at the final corpus test. Collection errors do not establish incorrect patches.
  The screen uses a pytest stand-in and the same public tests for selection, so neither a
  screen survivor nor a public-test pass would independently prove generalization. The
  earlier `NO_EXAMPLES` result describes the example-based arm, not the whole project.

## External research checked, through 17 November 2026

- [SkillLearnBench](https://arxiv.org/html/2604.20087v1) reports one-shot and iterative
  skill learning vary substantially across tasks and models; self-feedback alone can drift.
  Its agents use LLMs, which are **not** adopted as our agent or credited to this project.
- [Falsification-Gated Self-Evolution](https://arxiv.org/html/2611.14326v1) tests scoped
  memory updates for transfer, counterexamples, and regressions before persistence. Its
  reported method uses LLM components; only its testable protocol is considered here.
- [Causal Episodic Memory](https://aclanthology.org/2026.realm-1.70/) reports bounded
  improvements from verified earlier SQL repairs, with weaker evidence on one dataset.
  This is not a demonstration of universal instant learning.
- [SWE-Bench Pro Verified](https://arxiv.org/html/2609.08149v3) describes answer leakage,
  hidden-test access, and flawed specifications as separate sources of invalid evaluation;
  its safeguards have limitations and do not eliminate all possible leakage.
- [Patch correctness evidence framework](https://arxiv.org/abs/2611.10837) distinguishes
  search exposure, scope, oracle dependence, execution integrity, and adjudication. A
  benchmark pass alone is not a complete correctness judgment.
- [OSWorld 2.0](https://arxiv.org/abs/2606.29537v2) reports 108 long-horizon workflows
  and substantial remaining task failure under its stated evaluation. It is context for
  the difficulty of the goal, not an evaluation of our system.
- [EvoAgentBench](https://arxiv.org/html/2607.05202v1) separates related experience from
  instance-disjoint tasks and reports inconsistent automatic transfer and negative transfer.
  Its LLM-based setup is research context, not an approved solver for this project.
- [SWE-CoWork](https://arxiv.org/abs/2611.20218v1) reports that supplying full requirements
  improves partial completion without raising whole-task success in its paired comparison.
  Thus better observation alone does not guarantee implementation. Its public
  [harness](https://github.com/TokenWave-AI/swe-cowork-bench) describes container images,
  an eight-hour budget per task, and LLM-simulated colleagues; compatibility with the user's
  policy and a local independent evaluation is not established.
- [METR's maintainer study](https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/)
  reports that roughly half of sampled test-passing patches from agents studied would not
  be merged, subject to its sample and review assumptions; agents did not get to iterate.
- [Identifying indicators of consciousness](https://cris.tau.ac.il/en/publications/identifying-indicators-of-consciousness-in-ai-systems/)
  discusses theory-derived indicators under scientific uncertainty. Competence, learning,
  self-report, and memory do not establish subjective experience. Sentience is not measured
  by the experiments in this branch.

## Next feature: prerequisites and kill criteria

**Do not merge the existing synthesis experiment as a universal or independently verified
repair.** The next feature should reuse the tree's screening and admission organs to construct
an isolated, scoped, evidence-separated repair/retention loop, but only if an actual hard-open
benchmark can exercise it honestly. Before writing more search machinery:

1. Freeze a hard, genuinely open task population with no prior successful runs; hash the solver,
   budgets, task data and test files, and document prior exposure. Keep issue-facing evidence
   separate from hidden adjudication and prevent access to answer keys, target patches, git
   history and internet answers. This needs enforceable environment isolation, not a copied
   directory or a claim of isolation.
2. Run **only this project's own agent** at fixed budget on the chosen real tasks. Establish the
   actual baseline, including tasks it cannot attempt, infrastructure failures, timeouts, skipped
   cases and unsafe actions. Do not use another model to choose repairs or judge outcomes.
3. Reuse an isolated worker where its documented guarantees are sufficient; bound time,
   memory and output and isolate side effects. Capture exact failures as failures or unknown,
   never silent skips. If trustworthy isolation cannot be provided, stop rather than claim
   a completed feature.
4. Expose only task-authorized evidence during search. Obtain final verdict from held-out tests
   or independently adjudicated real requirements inaccessible to synthesis. Record whether
   feedback is genuinely independent and audit the verifier; quarantine ambiguous tasks rather
   than count them as passes or failures.
5. On the **same new open population**, compare the frozen baseline and proposed loop with
   equal resources, separately counting new held-out passes, regressions, time, compute and
   memory. Previously solved tasks must not be re-run for this capability measurement; historical
   regression evidence is not a fresh regression test. Where zero regressions cannot be freshly
   established under that constraint, say so explicitly.
6. Keep a candidate memory or weight change only when target transfer, counterexamples, and
   applicable safety checks support it. Otherwise refuse. Hashing proves identity, not truth;
   independently sourced specifications or user confirmation may still be required.

**Stop/kill:** no accessible real hard-open test with a credible independent verdict; inability
of our system to execute it without external-model help; unbounded or unsafe candidate execution;
no measurable held-out improvement at equal cost; leakage; or unverifiable success. Report the
blocker, not an invented capability. All new learned parameters, if ever justified, must be
computed from the project's own evidence and separately gated; conventional pretraining and
using external models as the system are not assumed or required here.

**Practical status on this host:** a user/network/mount namespace can be created and the
existing namespace launcher prerequisites are present, but that is only a preliminary host
check, not a security audit or an independent adjudicator. Docker, Podman and `/dev/kvm`
were not found; the available sandbox and allowed outbound hosts do not by themselves provide
the SWE-CoWork container setup or privately held evaluation. The four QuixBugs object-suite
cases and public tests have now also been inspected here, so they are not blind evaluation
material for a design made in this session. No capability experiment was run in this pass.

The branch's existing PR is open. At the time of this review, the signed repository integrity
referee passed, but three other workflow checks failed; the job failure steps were visible, while
the detailed logs could not be retrieved from this environment. No merge was attempted.
