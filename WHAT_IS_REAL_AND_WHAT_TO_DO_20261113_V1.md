# What is real, what is not, and the fastest honest path — 2026-11-13

**Branch:** `arena/954d9035-brain`. **Base:** `68374960837276a4d19f32caf39215cc99eb49ae`.
**Authority:** NONE. Producer-run sandbox measurement and code change. `truth.achieved` stays `false`.
No capability registered, no family flipped, no model weights updated, no independent verifier claimed.

## 0. Direct answer

The direction is real; the quantifiers are not.

- **Real:** persistent procedural memory, verified skill compilation, narrow transfer, test-time
  adaptation, and weight consolidation are active, measurable research directions.
- **Not real:** “show it once and it permanently learns anything on a computer,” “perfect
  generalization,” “the most advanced coding agent on the planet,” or “sentient creature.”
- **This repo specifically:** the older `INSTANT_LEARNING_PROOF.md`, `THE_SYSTEM_ALREADY_WORKS.md`,
  and `FINAL_SOLUTION_SUMMARY.md` overclaimed. The tree already contains retractions and
  measurements bounding them. This round removes one measured-wrong live executor and replaces
  it with a bounded, typed, read-only adapter.

A system can learn *procedures* without changing model weights. That is useful. It is not the
same as the model understanding why a procedure works, knowing when it must not fire, or
transferring across arbitrary environments.

## 1. First-principles decomposition

A computer-use/coding agent needs all of these, separately:

1. **Observation:** what is true of the current machine/repo/UI now?
2. **Action space:** what can actually be executed here, with what arguments and permissions?
3. **Policy/reasoning:** choose actions under uncertainty.
4. **Credit assignment:** which action caused success/failure?
5. **Oracle/verifier:** was the outcome correct, not merely completed?
6. **Memory/consolidation:** what durable artifact should change — prompt, skill, tool, policy,
   or weights?
7. **Evaluation:** did the change improve held-out tasks without regressing old ones?

One demonstration supplies a trajectory. A trajectory is a point, not a quantifier. It usually
underdetermines preconditions, invariants, edge cases, and failure boundaries. Storage makes the
point permanent; it does not make the point correct. Drift makes even a correct point stale.

The scarce resource is therefore not “more experiences” alone. It is **cheap, strong,
environment-specific verification plus safe admission of reusable artifacts**.

## 2. What the repository already measured

Relevant existing records:

- `THE_YES_WAS_NOT_MEASURED_20261112_V1.md`: one before/after pair becomes a reusable rule and
  survives a fresh process, but generalizes over surface, not meaning; a compile-only oracle can
  store a wrong lesson; `solve_or_learn` refuses unconfined computer execution on this machine.
- `WHERE_GENERALISATION_STOPS_AND_WHAT_MOVES_IT_20261112_V1.md`: on 132 ordered pairs from 12
  mechanical-migration PRs, one showing recovered 0.529 of developers’ changes with precision
  1.000; two showings recovered 0.891; widening the ladder produced 42 wrong changes; 0/42 real
  changed files could be checked on that machine because test modules/dependencies were missing.
- `THE_SYSTEM_ALREADY_WORKS_AUDITED_20261112_V1.md`: the shipped bundles exist, but several
  “instant/permanent/verified” claims were invented or one-trial deep.
- `NINE_BLIND_FACTS_NOW_DECIDED_20261112_V1.md`: binding/argument supply, not only verification,
  remains a dominant front-door blocker.

These are producer-run measurements, not independent certification. They are still better than
slogans because they name denominators and failure classes.

## 3. What this round changed

### 3.1 Removed a measured-wrong live executor

The controller’s old “semantic generalization” lane retrieved a lexically similar experience,
then used keyword presence in the current goal to choose an AST operation. Measured on the
shipped seed corpus and real repo files:

| Request | Old live answer | Problem |
|---|---:|---|
| `Count methods in canonical/runtime/solve_v1.py` | `Found 9 methods` | counted all functions, not methods |
| `Count functions and classes in canonical/runtime/solve_v1.py` | `Found 9 functions` | ignored classes |
| `Do not count functions in canonical/runtime/solve_v1.py` | `Found 9 functions` | negation became affirmative |
| `Count functions in <absolute path outside workspace>` | PASS | read outside caller root |
| `Count functions in absent.py` | PASS via parent scan | missing file answered from sibling/parent scope |

The old lane was not semantic understanding. It was TF-IDF/n-gram retrieval plus a keyword
counter, and it could fail open.

### 3.2 Added a bounded typed adapter

New module: `canonical/swe_kernel/python_ast_query_v1.py`.

Contract:

- explicit single-file, read-only count/list shapes only;
- operation and target bound from the **current** request, never from memory;
- targets: functions, methods, classes, if statements;
- methods use nearest enclosing lexical class scope;
- source resolved under caller workspace; symlink escape refused;
- negated/filtered/ambiguous/unsupported shapes refused;
- effectful requests are not intercepted;
- answer checked structurally against Python’s AST and labelled `independent_oracle: false`.

This is engineering transfer over file names and wording for a bounded syntax domain. It is not
weight learning, not conceptual understanding, and not arbitrary computer use.

### 3.3 Retired dangerous patchers and corrected labels

- `semantic_generalization_integration.py` and `fix_semantic_integration.py` now refuse to run;
  they previously spliced keyword-driven executors into the controller.
- `semantic_generalization_engine_v1.py` is labelled lexical retrieval, not “true generalization.”
- The three optimistic summary documents carry supersession/retraction banners.
- `test_semantic_generalization_real.py` now asserts correctness instead of printing a banner.

### 3.4 Tests

New/changed tests:

- `canonical/tests/test_python_ast_query_transfer_v1.py`: 21 tests.
- `test_semantic_generalization_real.py`: 1 test.

Targeted regression run:

```text
.venv/bin/python -m pytest -q \
  test_semantic_generalization_real.py \
  canonical/tests/test_python_ast_query_transfer_v1.py \
  canonical/tests/test_swe_intent_scope_regressions_v1.py \
  canonical/tests/test_one_demonstration_and_where_it_stops_v1.py \
  canonical/tests/test_the_check_is_the_difference_v1.py \
  canonical/tests/test_learn_path_verification_wiring_v1.py \
  canonical/tests/test_wake_sleep_recall_and_specialist_controller_v1.py
71 passed in 19.48s
```

Integrity guard:

```text
python3 execution_guard/repo_integrity_guard_v1.py --self-test
self-test: PASS

python3 execution_guard/repo_integrity_guard_v1.py --root . --base HEAD
rules=17 violations=0 -> PASS
```

Known unrelated failures observed while probing broader suites (not caused by this diff; those
modules do not import the changed controller lane):

- `canonical/tests/test_goal_front_compiler_v1.py::test_f1_best_candidate_that_cannot_bind_fails_closed_instead_of_falling_through`
- three tests in `canonical/tests/test_closed_loop_repair_must_generalise_v1.py`

They are recorded, not hidden or weakened.

## 4. What current research supports

Checked through 2026-11-13. Primary sources:

- **Zep Agent Skills, 2026-11-01:** verified traces compiled into versioned skills; teacher-derived
  skills improved weaker executors by 4.5–18.8 points, mostly on tasks the teacher solved; transfer
  to new tasks in the main benchmarks remains open. <https://arxiv.org/abs/2611.01386>
- **Anchor, 2026-11-07:** replay source decisions with/without candidate memory; test shift magnitude
  and source-role alignment before retention; held-out ALFWorld/WebShop gains up to 19.9%/17.2%.
  <https://arxiv.org/abs/2611.10382>
- **ENGRAM, 2026-11-06:** separates training admission from memory release; LoRA consolidation on
  valid traces; verify updated model without retrieval against base+retrieval before releasing
  external records. <https://arxiv.org/html/2611.09472>
- **WikiTrace, 2026-11-10:** memory can cause regression; link lessons to source trajectories and
  descend when evidence is needed; measures Gain and Regression separately.
  <https://arxiv.org/pdf/2611.14320>
- **SkillsBench, 2026:** curated skills raised average pass rate 33.9%→50.5%; self-generated skills
  underperformed no-skills in tested configurations. <https://arxiv.org/abs/2602.12670>
- **SkillLearnBench, 2026:** continual skill methods improve over no-skill but no method leads
  everywhere; external feedback matters; self-feedback alone can drift.
  <https://arxiv.org/html/2604.20087v1>
- **SEAL, 2025:** persistent weight updates via self-edits are real, but sequential edits exhibit
  catastrophic forgetting. <https://arxiv.org/html/2506.10943v1>
- **TT-SI, 2025/2026:** test-time self-improvement from uncertain samples can help, including
  single-instance adaptation, but is not a general solution. <https://arxiv.org/html/2510.07841v1>
- **OpenAgent, 2026:** SFT/RL agents degrade under open-world query/action/observation/domain shifts.
  <https://arxiv.org/html/2607.01084v1>
- **Benchmarks:** SWE-bench Pro V2 ships 642 validated Harbor tasks and fresh-sandbox regrading;
  OSWorld V2 targets long-horizon computer use with pinned releases.
  <https://github.com/scaleapi/SWE-bench_Pro-os>, <https://github.com/xlang-ai/OSWorld-V2>

The pattern across these sources is consistent: **verification, admission, scope, and regression
measurement are the levers**. “Store more successful traces” is not enough.

## 5. Smartest next steps, in order

1. **Oracle bootstrap before skill expansion.**
   Make project checks runnable in isolation: declared dependencies, test entry-point discovery,
   positive/negative controls, mutation checks. Report `CHECK_DEPENDENCY_MISSING`,
   `CHECK_NO_TEST_MODULE`, `CHECK_WEAK_ORACLE` separately. Do not admit a skill from a compile-only
   or self-graded success.

2. **Typed skill contracts, not wording lookup.**
   Each skill carries parameters, preconditions, effects, postconditions, verifier references,
   source evidence, version, and quarantine state. Retrieval ranks candidates; contracts and
   current-world probes decide applicability.

3. **Contrastive demonstrations and active questions.**
   One success plus a boundary/failure case is worth more than ten similar successes. Use
   version-space/anti-unification machinery already present, but gate widening with target checks.

4. **Paired transfer evaluation.**
   For every memory/skill change measure: no-memory vs memory, held-out tasks, Gain, Regression,
   precision, wrong-edit rate, cost, and verification strength. Pin benchmark releases. Start with
   the repo’s 12-task corpus, then SkillsBench/SkillLearnBench-style tasks, then SWE-bench Pro V2
   and OSWorld V2 for broader claims.

5. **Weight consolidation only after external memory proves useful.**
   Train LoRA/adapters on verified, deduplicated, contrastive traces with replay. Gate admission and
   memory release ENGRAM-style: candidate without retrieval must match/beat base+retrieval on
   reserved probes and old-task retention suites. Do not merge adapters blindly; measure forgetting.

6. **Confined computer-use lane.**
   VM/browser sandbox, state observation, action feasibility sensors, checkpoints/rollback,
   destructive-action approval, and task-specific success predicates. “Anything on a computer”
   requires effect admission and safety, not just memory.

7. **Sentience is not a capability milestone.**
   Nothing in this repository establishes subjective experience. Names such as `sentient_cognitive_core`
   do not create sentience. Treat it as a philosophical claim outside the engineering contract until
   there is evidence and a testable definition.

## 6. Ideas killed before implementation

- “Give it every advanced action once and it permanently learns everything.” Killed: one trajectory
  underdetermines scope; repo measurements show surface-only transfer and wrong lessons under weak oracles.
- “Widen the rule ladder.” Killed: measured 42 wrong changes and precision collapse.
- “Self-feedback is enough.” Killed: SkillLearnBench reports drift; external feedback is the lever.
- “Train on all successful traces immediately.” Killed: unverified/one-trial successes can poison
  weights; SEAL shows forgetting; ENGRAM separates admission from release.
- “Similarity score proves generalization.” Killed: this round’s live wrong answers had high lexical
  similarity and wrong semantics.
- “Sentience follows from memory + planning.” Killed: no evidence, no testable contract.

## 7. Bottom line

We did not solve general intelligence, arbitrary computer use, or sentience. We removed a concrete
fail-open path, replaced it with a bounded typed contract, pinned the behavior with tests, and
aligned the next work with the strongest current evidence: **oracle-first admission, scoped reusable
skills, paired transfer/regression evaluation, and only then verified weight consolidation.**
