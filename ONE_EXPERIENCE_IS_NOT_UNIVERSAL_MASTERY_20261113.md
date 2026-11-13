# One experience is not universal mastery — findings and a measured repair

Date: **13 November 2026 UTC**. Authority: **NONE**. This is an engineering assessment and
producer-run sandbox test record, not independent verification, capability promotion, or a
claim of sentience. No model weights, mission laws, registries, or terminal-truth files changed.

## 1. Direct answer

**The direction is useful; the universal conclusion is unsupported.** An agent can keep an
experience immediately and reuse it later. That is not evidence that it can infer every relevant
precondition, solve unfamiliar engineering problems, or operate every application correctly.

The strongest counterexample is informational, not computational. Suppose two programs both
return `True` at 99, but one is meant to implement “under 100” and the other “at most 100.” A
successful demonstration at 99 cannot distinguish those contracts. More clever storage or a
weight update cannot manufacture the missing bit. A contract, a boundary test, a contrasting
example, or another informative observation can supply it. One demonstration CAN suffice when
prior mechanisms plus the demonstration identify the task sufficiently; that qualification is
what “learn anything once” omits.

The right target is **fast, scoped acquisition with measured transfer and revocable retention**,
not unconditional permanent belief. Retain evidence durably; revise or disable conclusions when
counterevidence arrives. Version and permission changes can make yesterday's correct action wrong.

Neither memory, autonomous behavior, self-description, nor benchmark gains establishes subjective
experience. This work supplies no evidence that Brain is sentient. Operational competence and
sentience should not be treated as the same engineering deliverable.

## 2. What is already here, including the non-obvious names

| Mechanism inspected | What it actually provides | What it does not establish |
|---|---|---|
| `canonical/swe_kernel/verified_skill_crystallizer_v1.py` | Parameterized edit hypotheses, persistent SQLite storage, scoped verification and recall | General reasoning or arbitrary new edit synthesis |
| `canonical/swe_kernel/python_scoped_edit_rule_v1.py` | Structural Python edit machinery used by the crystallizer | Semantic correctness merely from matching |
| `canonical/swe_kernel/lesson_admission_gate_v1.py` | Execution-based candidate admission on supplied other programs | Safety outside those programs and probe inputs |
| `canonical/tools/rule_generalization_probe_v1.py` | Executable checks against an oracle tied to the original victim | Isolation, timeout enforcement, or a universal oracle |
| `canonical/tests/test_scoped_skill_verification_and_restart_v1.py` | Real copied-project test execution and fresh-interpreter storage/recall tests | A representative frontier software-engineering evaluation |
| `canonical/runtime/goal_compiler.py`, `capability_planner.py` | Declared deterministic goal compilation and precondition/effect planning | Arbitrary natural-language understanding or universal computer control |

So “only a wording lookup system” is too sweeping a description of this tree. Structural,
parameterized transfer is implemented. But “therefore solved all computer use” is much too strong.
The nine-suite run below executes the current tree; earlier narrative documents are not evidence
of additional capability merely because their titles say “complete” or “perfect.”

**The decisive deployment limitation remains:** supplying `admission_victims` is optional in
`VerifiedSkillStore.crystallize_code_fix`. Its no-victims path still persists an `UNGATED` rule.
The existing admission tests explicitly demonstrate this. This patch does not secretly change
that compatibility behavior or claim that all autonomous callers now use the gate.

## 3. Two admission defects found and fixed in this turn

### A. The candidate could change its own expected answers

Before this patch the gate called `oracle(source, point)` for the baseline and again with the
**edited** source. A source-sensitive oracle could silently reinterpret the contract, so a harmful
boundary change appeared `PRESERVED`. With an otherwise valid repair and preservation case in the
suite, the gate returned `ADMIT` and the real store persisted the rule.

Now expectations are computed once per probe from the original source, before either execution,
and reused by both arms. This matches the original-victim convention already used by
`rule_generalization_probe_v1`. It does not make an incorrect oracle correct.

### B. A program with an old bug could lose working behavior without rejection

Previously the gate distinguished only “already correct” and “defect present” at whole-program
level. A defective program that acquired another failure was merely `STILL_WRONG`. If other
programs supplied the required gain and preservation, the lesson was admitted anyway. The same
hole affected archived programs.

Now every previously passing probe is protected:

```
regression = baseline_agrees AND NOT candidate_agrees
```

An already-defective program that loses any such behavior yields `REGRESSED`, with probe IDs and
counts, and rejects admission. Archive regressions use `ARCHIVE_REGRESSION`. Fully correct
programs retain the existing `BROKEN` classification. Stored admission summaries retain regression
counts. A program that remains defective WITHOUT new failures does not veto a useful lesson.

The tests also cover an important trap: an edit repairs -100 but breaks +100 in a mixed-boundary
program. Both versions have exactly **one** failing probe. Aggregate failure counts cannot detect
that loss; the new pointwise comparison does.

**Measured storage effect:** the three harmful store-path cases (moving specification, partial
regression, archived partial regression) previously each returned `crystallized=True`; now each
returns `False`, and reading the temporary database confirms zero stored rules.

## 4. Corrections to the proposed four requirements and phased plan

- **Weight updates are an option, not the definition of learning.** Non-parametric memory,
  induced programs, updated scope/routing policies, and search can change future behavior without
  base-model weight changes. Weight training alone does not guarantee transfer or correctness.
- **Concept counts are not a learning metric.** Ten versus forty stored “causal models” could be
  duplicated or wrong hypotheses. Measure executable success, harm, retention and cost instead.
- **A successful trajectory is not a causal explanation.** It usually leaves confounds and
  counterfactuals unresolved. Explicit preconditions and targeted interventions supply stronger
  evidence than narrative reflection alone.
- **Do not postpone edits and tests until after “advanced coding analysis.”** The essential unit
  is a closed loop: localize -> propose a bounded patch -> execute checks -> inspect failures ->
  retain or reject. Test generation is already part of coding, not a later adjacent domain.
- **Architecture and optimization need task-specific evidence.** An architecture is not verified
  by compilation; optimization needs representative workloads and correctness constraints.
- **Universal GUI control is a separate integration problem.** State observation, grounding,
  permissions, asynchronous interfaces, recovery and safe side effects do not follow from AST
  repair. Prefer APIs/CLI where they faithfully accomplish the goal, with GUI fallback when needed.
- **“Prevent literally every mistake before acting” is not an achievable procedure.** Unknown
  facts require experiments. Use cheap reversible experiments and risk-proportionate checks rather
  than endless reflection or unconditional action. This does not revise the owner's objective.

## 5. Current research consulted — versioned, not leaderboard folklore

These are published authors' reports, not results reproduced here. Model-assisted research does
not automatically meet Brain's zero-runtime-model-dependency ownership rules.

| Source and version/date | Relevant observation | Consequence, not overclaim |
|---|---|---|
| FGSE, submitted 10 Nov 2026 | Temporarily tests lessons on transfer, falsification and archive probes before committing; still reports 3.6% harmful committed updates | Test lesson admission; do not call a gate perfect. [1](https://arxiv.org/abs/2611.14326) |
| Continual harness evolution, submitted 2 Nov 2026 | In one studied configuration, further evolution reduces earlier SWE performance from 94% to 32% | Frozen base weights do not prevent harness-level forgetting; replay earlier tasks. [1](https://arxiv.org/abs/2611.03219) |
| SkillsBench **v4**, 14 Jun 2026 | Matched curated-skill evaluation: 87 tasks, 18 configurations, average 33.9% -> 50.5% (+16.6 pp) | Skills can help substantially, not universally. Do not quote the older +16.2 pp inventory as the latest result. [1](https://arxiv.org/abs/2602.12670) |
| SWE-ContextBench v2 | Context reuse can help; autonomous selection can yield limited or negative gains | Compare relevant retrieval with no-memory and irrelevant-memory controls. [6](https://arxiv.org/html/2602.08316v2) |
| ReTTT, submitted 8 Oct 2026 | Episode-local LoRA adaptation with revised lessons; reported gains up to 12.14 pp across evaluated settings | An example of parametric adaptation, not permanent universal acquisition. [4](https://arxiv.org/abs/2610.23942) |
| ReasoningBank, ICLR 2026 and released code | Reuses strategy memories from successes and failures; official implementation depends on LLM inference | Relevant algorithmic comparison, not a drop-in Brain-owned cognition provider. [2](https://proceedings.iclr.cc/paper_files/paper/2026/file/980ea04d23d1f6908964eba2a74afe45-Paper-Conference.pdf) [1](https://github.com/google-research/reasoning-bank) |
| OSWorld 2.0 paper, Jun 2026 | Long-horizon evaluation separates binary completion, partial completion and safety diagnostics; its reported best setting has 20.6% binary versus 54.8% partial accuracy | Do not confuse partial progress or an older short-task score with reliable end-to-end computer use; these are paper-setting results, NOT a current leaderboard claim. [1](https://arxiv.org/html/2606.29537v1) |

Search also surfaced secondary summaries with conflicting inventories and scores. Primary source
versions above were preferred. More search is worthwhile when it changes an implementation choice;
volume alone does not improve truth or establish optimality.

## 6. Fastest defensible next steps

This is a prioritized engineering recommendation, not a proof of global optimality.

1. **Close the admission bypass deliberately.** Inventory autonomous callers; require real,
   independently specified transfer and preservation cases for active reusable lessons. If
   evidence is unavailable, quarantine the hypothesis rather than mark it safe. Handle migration
   explicitly: old `UNGATED`/`ADMIT` rows are not retroactively revalidated by this patch.
2. **Choose one useful bounded end-to-end task:** test-guided Python bug repair. Reuse the current
   scoped project-test oracle, copied-tree execution, edit machinery, and persistent store.
   Avoid inventing five large “expert action” wrappers before one loop is measured.
3. **Separate acquisition, refinement and final evaluation.** Admission cases are development
   evidence once used for selection. Freeze a later repository/task-family holdout before tuning;
   record any overlap and do not call renamed demonstrations independently unseen tasks.
4. **Run paired controls under equal resources:** no memory, exact replay, parameterized lessons,
   and irrelevant-memory control. Test changed identifiers, paths, inputs, contracts and task
   structure separately; restart between retention checks. The no-memory route must still get
   the same underlying solver, not an intentionally crippled fallback.
5. **Measure outcomes rather than objects stored:** held-out task success, new failures, scope
   refusal/coverage, backward retention, elapsed time, calls and bytes. Report denominators and
   uncertainty. Stop growing a mechanism if it adds complexity without out-of-sample benefit.
6. **Only then broaden the mechanism basis and environment support.** Use the observed failures
   to choose between missing operators, scope inference, perception, planning and verification.
   No paper or toy test here shows a globally fastest route to every computer task.

Important residual risks: finite probes miss behaviors; caller-selected evidence can be biased;
source-text distinctness is weaker than semantic/task independence; arbitrary Python still runs
in-process without resource/security isolation; mutable/adversarial oracles and program side
effects are outside this gate's trust model. Production execution needs a separate isolation
boundary. None of those limitations is solved by this patch.

## 7. Reproducible validation ledger

Before the runtime change, the first eight new regression cases plus the existing gate suite:
**8 failed, 19 passed**. This included three actual harmful database writes, not just missing-field
assertions. Two additional equal-count regression cases were added after implementing the fix.

After the change:

```sh
.venv/bin/python -m pytest -q \
  canonical/tests/test_lesson_admission_regression_v1.py \
  canonical/tests/test_lesson_admission_gate_v1.py \
  canonical/tests/test_rule_generalization_probe_v1.py \
  canonical/tests/test_skill_recheck_v1.py \
  canonical/tests/test_scoped_skill_verification_and_restart_v1.py \
  canonical/tests/test_skill_self_witness_v1.py \
  canonical/tests/test_skill_scope_ledger_v1.py \
  canonical/tests/test_skill_scope_acquisition_v1.py \
  canonical/tests/test_a_learned_skill_is_durable_and_general_v1.py
# 158 passed in 8.17s

python3 execution_guard/repo_integrity_guard_v1.py \
  --base d98c52f3f508efcae22990f31152210a8fd38ca6
# 17 rules, 0 violations -> PASS
python3 execution_guard/agent_orientation_check_v1.py verify
# ok: true, errors: []
git diff --check
# clean
```

Environment: created a local ignored `.venv` and installed pytest 9.2.0; no test installs
packages, patches standard-library behavior, or reads historical source versions. No full-suite
run is claimed.

### CI follow-up: generated artifact, not a weakened check

The first PR check run failed `recompilation_is_byte_identical` (32/33 artifact checks), because
this report changes the root markdown knowledge index. The signed repository referee passed.
Updated the current working branch with `origin/main` at `2b4d4281fd582f45fb37c194b7464d0cdc189369`
and regenerated the existing tracked index through its normal compiler; no verifier was changed.

```sh
python3 canonical/runtime/compile_brain_unified_model_v1.py
python3 canonical/runtime/verify_brain_unified_model_v1.py
# 33/33 PASS after rebuild
.venv/bin/python -m unittest -q \
  canonical.tests.test_brain_unified_model_v1 \
  canonical.tests.test_goal_compiler \
  canonical.tests.test_goal_compiler_world_binding_v1
# Ran 137 tests in 52.399s, OK
```

Recompile again after this report is finalized, since its bytes are indexed too. The generated
JSON is an existing required projection, not new learned weights or additional capability.
Suite backlog outside the named pytest and unittest files remains unmeasured in this turn.

**Bottom line:** storing an experience once is achievable. Safe transfer is a hypothesis that
requires additional evidence. Today's concrete gain is two fewer ways for an unsafe hypothesis
to become a persistent rule, not a declaration that general intelligence has been solved.
