# A counterexample must revoke the live rule; safety evidence must actually execute

Date: 2026-11-13. Base: `388c5c7d9b4d1407ac842d785201c1fb6fb6b473`.
Authority: **NONE**. This is model-assisted development and producer-run sandbox testing.
It registers no capability, flips no family, updates no base-model weights, and claims no
independent certification. `truth.achieved` remains `false`.

The branch was fast-forwarded through the concurrent main revisions while this work was in
progress. In particular, main PR #6861 already fixed source-sensitive oracles and pointwise
regressions inside partially broken programs. Those fixes are kept, not reimplemented; this
patch adds revocation of the already-live rule, evidence-input validation/deduplication, and
execution accounting on top of them.

## Direct answer to the owner

**The direction is real. The universal conclusion is not.**

- Persistent skills, executable verification, narrow transfer, and weight consolidation are
  real mechanisms. They can make an agent improve faster than a stateless agent.
- “Show it once and it permanently learns anything on a computer” is not established here
  or by the current research checked below. One trajectory is a point estimate; it does not
  identify preconditions, exceptions, causal credit, or behavior on unseen inputs.
- Storage permanence is not correctness permanence. A stored rule can be wrong, stale,
  over-broad, or harmful when composed with another rule.
- The repository’s own held-out measurements are partial, not perfect. The existing record
  reports 37.52% coverage at 76.36% precision on one change class and an upper bound of
  34.15% coverage at 60.61% precision on another, with 65 unwanted changes. Those numbers
  are from `LEARNING_ONCE_DOES_NOT_SOLVE_COMPUTER_USE_20261113_V1.md`; this patch did not
  re-run that benchmark and does not claim to improve it.
- Nothing in this repository establishes sentience. Memory, planning, self-report, and
  weight updates are not evidence of subjective experience. A module named
  `sentient_cognitive_core` does not change that.

## First-principles diagnosis

A durable improvement needs six separable properties:

1. **Representation:** the artifact can express the useful transformation.
2. **Credit assignment:** the system knows which action/state change mattered.
3. **Specification:** “correct” means something checkable for this task.
4. **Admission:** the candidate helps unseen cases and does not break known-good cases.
5. **Use:** retrieval/application actually consults the artifact in the right context.
6. **Maintenance:** new evidence can narrow, revoke, or replace stale knowledge.

A single demonstration can supply (1) and a hint about (2). It cannot by itself supply
(3)–(6). Finite probes reduce uncertainty; they do not prove behavior over an open input
space. For arbitrary programs and arbitrary user intent, there is no finite demonstration
procedure that guarantees universal correctness. The practical goal is a growing set of
bounded, measured, reliable capabilities—not a literal “solves everything” switch.

## What exists under non-obvious names

| Artifact | What it actually provides | Boundary |
|---|---|---|
| `canonical/swe_kernel/verified_skill_crystallizer_v1.py` | SQLite-backed parameterized code-edit hypotheses, structural twins, scoped verification, invalidation | Not a general reasoner; many legacy admissions remain `UNGATED` |
| `canonical/swe_kernel/lesson_admission_gate_v1.py` | Executes a candidate rule on supplied unseen programs before persistence | Bounded by supplied specs/probes; not whole-task proof |
| `canonical/swe_kernel/semantic_generalization_engine_v1.py` | Typed count/list/breakdown/exists/compare programs plus small online linear ranking heads | The heads are not an LLM and cannot override a verified symbolic refusal |
| `canonical/swe_kernel/weight_update_admission_v1.py` | Shadow weight step admitted only on measured gain with no probe regression | Small linear heads; agreement with the typed parser, not open-ended engineering competence |
| `canonical/swe_kernel/taught_actions/edit_by_example_v1.py` | AST-level edit induction from examples | Finite operator basis; measured transfer is narrow |
| `canonical/runtime/confinement_v1.py` and repair oracles | Copied/confined execution machinery and project test checks | Availability and wiring vary by live route; not universal GUI control |

The old lexical `semantic_generalization_integration.py` is retired and refuses to run.
Optimistic “COMPLETELY SOLVED” documents are historical claims, not executable evidence.

## Two concrete defects found and fixed

### 1. Rejecting a new counterexample left the old harmful rule active

Measured on the real store before this patch:

```text
teach boundary rule with safe victims -> ACTIVE, admission=ADMIT
reteach same rule with harmful victim -> crystallized=False, ADMISSION_REJECT
stored rule                           -> still ACTIVE, admission=ADMIT
apply to inclusive-cap program        -> still rewrites correct code
```

That is not learning from a mistake. It is refusing to record a new mistake while keeping
the old one usable.

**Fix:** when admission produces executed `BROKEN` or `REGRESSED` evidence, the store now
invalidates the matching persisted identity (including scoped identities), preserves the
earlier admission as history, and appends an `admission_refutations` record in the same
SQLite transaction. The read-modify-write uses `BEGIN IMMEDIATE`, so concurrent refutations
serialize instead of losing an append. The rule remains auditable but cannot apply, even
through a permissive verifier. The invalidation travels through bundle export/import and is
visible to a fresh store instance. `REFINE`, `REFUSED`, missing evidence, and a fabricated
report with zero executed probes do not revoke anything.

### 2. Probe accounting could report safety without executing probes

At the original base, `Victim.probes` was consumed once by `len(tuple(...))`. If a caller
supplied a generator, the later baseline/candidate checks iterated an exhausted object. Zero
executed points could become `PRESERVED` with `counted_as_evidence=True`. Main PR #6861
already snapshots probes inside `_evaluate_victim`; the remaining holes were duplicate
labels/points, the same observation relabeled or reordered as archive, malformed inputs, and
counts inferred from `probe_count` rather than recorded executions.

**Fix:** validate and snapshot probe inputs once before any oracle/program runs; require
nonempty unique victim IDs, readable source, JSON-serializable distinct probe points, and no
duplicate source/spec/point-set observation across roles; record actual baseline and
candidate execution counts. The same source under a different spec remains distinct
evidence. `programs_executed` now counts actual program evaluations at probe points,
including a baseline that ran before a non-match.

These are reliability fixes to the admission machinery. They do not create new coding
coverage, do not make the autonomous callers supply victims, and do not prove the supplied
oracles correct.

## Current research checked through 2026-11-13

- **FGSE, submitted 2026-11-10:** treats each lesson as a hypothesis and tests transfer,
  falsification, and archived regression before commit. Author-reported harmful committed
  updates are still 3.6%, not zero. https://arxiv.org/abs/2611.14326
- **ReScopeBench, submitted 2026-11-03:** 352 tasks, 18 environments, 26 silent changes.
  Experience helps, but agents leave outdated content uncorrected and can fail even when
  the needed experience is recorded. This directly separates retention, revision, and use.
  https://arxiv.org/html/2611.05450
- **Continual-ARC, submitted 2026-11-10:** no harness-based method gained on unseen tasks
  in its experiments; weight-based DAgger did, but held-out performance was about half of
  seen-task performance. That supports weight learning as a real lever, not a perfect one.
  https://arxiv.org/html/2611.14505
- **ENGRAM, submitted 2026-11-06:** separates training admission from memory release and
  compares the updated model without retrieval against base-plus-retrieval on reserved
  probes. Consolidation is a measured release decision, not “train once and delete memory.”
  https://arxiv.org/abs/2611.09472
- **AgentCL:** separates plasticity, stability, and held-out generalization; memory can
  help dependent streams while degrading independent tasks. https://arxiv.org/html/2606.02461
- **SkillsBench:** curated skills helped, while self-generated skills had negligible or
  negative average benefit in the reported configurations. More self-authored memory is
  not automatically better. https://arxiv.org/html/2602.12670v1
- **SEAL:** persistent self-edits are real, but sequential updates exhibit catastrophic
  forgetting. https://arxiv.org/html/2506.10943v1
- **OSWorld-V2 and SWE-bench Pro V2:** pinned, executable long-horizon benchmarks exist
  for computer use and repository engineering. They are the right kind of external audit,
  not proof that this repo passes them. https://github.com/xlang-ai/OSWorld-V2,
  https://github.com/scaleapi/SWE-bench_Pro-os

## Smartest next order

1. **Wire real victim corpora into autonomous learn callers.** The gate is still optional;
   callers without victims write `UNGATED`. Start with one narrow repair class and real
   project tests, including boundary and already-correct programs.
2. **Measure paired transfer, not counters.** Same held-out tasks, memory off vs memory on;
   report repairs, regressions, precision, abstentions, latency, and cost. Keep a reserved
   set that never proposes candidates.
3. **Make maintenance continuous.** Replay known counterexamples after rule/scope changes;
   quarantine on drift; test composition, not only isolated rules.
4. **Then investigate weight consolidation.** Use verified, deduplicated, contrastive
   traces; replay old tasks; compare no-retrieval candidate against base-plus-memory.
   This repo’s ownership law forbids an external general-purpose model in credited producer
   paths, so a general-model fine-tuning route is a governance decision, not a hidden switch.
5. **Expand computer use only inside a real stateful sandbox.** Observation, feasible
   actions, rollback, permissions, and task-specific success predicates come before GUI
   breadth. “Anything on a computer” is not the same substrate as AST edit transfer.

## Ideas rejected before implementation

- Training on every successful trace: weak credit assignment and forgetting.
- Adding more action names or “causal model” counters: no measured behavior change.
- Treating similarity, confidence, or a compile-only pass as correctness.
- Treating a non-firing rule as safety evidence.
- Letting a rejected counterexample leave an older active copy untouched.
- Counting duplicated or unexecuted probes as independent evidence.
- Claiming sentience from persistence, self-model text, or planning.

## Test ledger

Commands run in this sandbox with Python 3.11.2, pytest 8.4.2, tree-sitter 0.21.3,
tree-sitter-languages 1.10.2, Pillow 13.0.0, and z3-solver 5.4.1.0. No test harness was
patched and no assertion was weakened.

```text
# new regression file at pre-merge main base 8cb35f6502, before this patch's runtime wiring
32 failed, 2 passed in 1.12s

# final focused admission/store/engine regression set on the merged tree (16 files)
302 passed, 1 warning in 31.37s

# all 43 tracked test files that reference VerifiedSkillStore/crystallize_code_fix (at 8cb35f6502)
551 passed, 11 failed, 7 errors, 9 warnings in 249.94s

# the same failing/erroring files re-run with the two runtime files restored to 8cb35f6502
11 failed, 126 passed, 5 warnings in 100.97s

# the 7-error QuixBugs file alone, with this patch restored
61 passed in 30.76s
```

The 11 broad-suite failures reproduce on the 8cb35f6502 base runtime files: unconfined-route
expectations, multi-round crystallization count, navigation/front-door confinement,
insertion/coupled repair, latency/confinement-dependent organism tests, and a calibration
expectation. The 7 QuixBugs errors were a concurrent `_MEM_SKILLS` dictionary-mutation race
during the broad run; that file passed alone and also passed in that base rerun. Neither class
is hidden or attributed to this patch. They remain real backlog/environment work.

`compileall`, `git diff --check`, and the integrity guard self-test passed. Generated test
mutations to tracked runtime-state JSON were restored; they are not part of the patch.

## Bottom line

You are right that verified experience can compound. You are wrong that one exposure,
permanent storage, and more action names amount to perfect general intelligence or
sentience. The fastest honest path is to make every durable update earn its scope, revoke
it when contradicted, measure transfer and regressions separately, and only then consolidate
what survives into weights.
