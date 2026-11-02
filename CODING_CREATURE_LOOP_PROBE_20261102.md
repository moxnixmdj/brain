# Coding creature loop: routing follow-up and initial probe

Date: 2026-11-02. Research measurement, not an independent verification or a
capability, ownership, terminal, sentience, or universal-learning claim.

## Current outcome and handoff

**The front-door learn → restart → reuse loop has not been demonstrated.** The narrow routing change sends the tested repair requests to the editing capability instead of a non-editing auditor, but the existing adapter refuses them before execution: `BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT:python.software.repair.apply.verified.v1`. The registry describes the repair evidence as `SANDBOX_MEASUREMENT_ONLY__NO_TWO_SPRITE_FALSIFICATION_CLAIMED`. No independent verifier was obtained, no gate was bypassed, and no authority or certification is claimed.

With learning enabled, this exact refusal is now recorded as an open, non-authoritative ignorance gap without copying the raw goal or arguments. Teaching and warm runs in fresh processes record the same gap ID. The learning-disabled cold run does not write that gap store. Recording a gap does **not** acquire verification or automatically close the gap when conditions change. Storage failures are exposed as `RECORD_FAILED`. The existing normalized-token identity is a heuristic; legacy duplicate rows are not merged and concurrent ledger writes are not addressed.

There is a second obstacle: the existing frozen bound-action template does not bind a `retained_learning` input. The draft now refuses a mismatched setting rather than silently dropping it; the template itself is unchanged. Even a legitimate future admission would not, by itself, connect the front door to retained repair. In addition, repair runs target tests with host authority: examined public execution routes now refuse that adapter until confinement is admitted, without claiming direct APIs are protected. The separately configured direct repair route does exercise scoped retained learning, but it supplies inputs that the raw front door does not; it is not a fair front-door comparison or proof of general learning. The detailed path and state audit is in `RETAINED_REPAIR_FABRIC_PATH_AUDIT_20261102.md`.

Next steps require (1) a separate person to actually run independent verification, record the distinct verifier and run reference, and follow the existing admission process without inventing proof; (2) review the frozen action-template and context/contract binding through the legitimate process before enabling opt-in retention; and (3) rerun raw-goal teaching, fresh-process warm reuse, learning-disabled cold, negative and held-out controls, with independent outcome audits. The exact R1 authority binding also needs legitimate governance review before integration can be called admissible: both authority records pin fabric Git blob `d0b1cceffc8c2b39ce1157afa193fea83d76c8ab`, whereas the original HEAD fabric is `8dfbc4d757f0a12dfbba9efac7352bb5af128105` and this worktree fabric is `85d4639611fa84d7f617d74b77d07cbe0acb5e3d`. Do not hand-repin authority to conceal the drift.

### Local checks, not independent certification

- Focused unittest run across restart identity, legacy ledger, refusal recording, route guards and the fresh-process probe: **27 passed**. Negative controls include explicit audit naming, failed admission, no typed repair plan, refusal of non-editing proposals, learning disabled, privacy, and storage failure.
- In disposable copies, curriculum tests: 27 passed / 1 failed; live-route memory: 4 passed / 2 failed / 9 skipped; fabric: 24 passed / 1 failed. Each of these four failures was separately reproduced after restoring the three modified runtime files from the original HEAD in the copy. The fabric failure includes R1 authority blob drift; a pre-existing failure does not authorize this worktree's different blob.
- The unified model was regenerated using `python3 canonical/runtime/compile_brain_unified_model_v1.py`, not by hand. Its official verifier in a disposable copy reported **33/33**, explicitly `AUTHORITY NONE -- SANDBOX MEASUREMENT, NOT INDEPENDENT VERIFICATION`; the digest of that earlier snapshot was `87de8b90b68be727e9c783213a8abc219f1cf33a60de1477c7251fb3bd6671a4`. See `COMPUTER_CREATURE_LOOP_PROBE_20261102.md` for the later model digest after subsequent safety edits.
- Static repository integrity guard: 11 rules, 0 violations. `git diff --check` passes.
- The action intent is explicitly a **draft, not admitted**. Its recorded base is the current HEAD, but the orientation intent-check reports `ORIENTATION_PROGRESS_CLASS_INVALID`: no available class accurately describes this unfinished, unverified integration experiment without implying a verified gain or misclassifying it as a governance-only change. The full recursive OBS/action gate has not been satisfied or claimed to pass.

## Follow-up: reuse the typed plan before execution

The RAW_GOAL entry now checks a narrow case before dispatch: an explicit
fix/repair imperative compiled as a single non-editing, effect-inconsistent
capability. It asks the existing typed SWE planner for a decisive source-editing
proposal and checks it against the original admissible registry and the existing
route admission. Ambiguous or refused proposals fail closed. It does not
silently replace an explicitly named capability, and it does not change DAGs,
controller plans, or questions. The existing bound-verification and execution
checks remain in force.

On the same seeded project, all three fresh-process raw attempts now select
`python.software.repair.apply.verified.v1` rather than the auditor. All three
fail before execution with
`BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT`, leave source and tests
unchanged, and fail the separate audit. No permanent reuse is authorized. The
alternate plural repair sentence behaves the same way. The old runtime, replayed
in a disposable copy with the same instrument, selected the auditor and returned
an execution-level pass on both sentences, leaving the defect untouched.

A separate real audit request still selects the auditor and produces its report.
The run-tests, question, and unrelated controls did not select repair and left
source unchanged. A previously repaired, independently audited fixture remains
unchanged, though the current bound gate still refuses its repair request. A
fault-injection control removes the typed proposal: the wrong auditor is refused
and no report is written. Unit controls also refuse a rejected, non-editing, or
out-of-registry proposal, and an explicitly named auditor rather than silently
substituting a repair. These controls are finite; they do not prove all sentence
forms or other front doors safe.

The direct explicitly configured retained-repair path still repaired all three
cases and passed the separate authored audits; the warm worker had a retained hit
and no search, while the cold worker searched. It remains a different input and
admission path, not evidence that RAW_GOAL can learn, restart, and reuse a fix.
The existing qualification report explicitly disclaims independent certification;
no independent receipt or recognized verification flag was found for the bound
repair entry. The gate and registry were not changed. Legitimate independent
verification remains the next blocker before testing end-to-end reuse.

Validation: 6 new focused unittest cases passed (five route guards and the
fresh-process instrument); 38 focused existing/new pytest cases passed with one
known failing question test deselected; 28 retained-repair qualification and one
failure-continuity test passed in a copy. The question test fails on the base too:
its expectation that the typed planner returns no family conflicts with the
current diagnose family. Two selected old route-admission tests also fail on both
the base and modified runtime (a tutorial compilation gap and a repair sentence
selecting the cross-file choreographer). A larger combined test run timed out at
420 seconds; a smaller route-admission run timed out at 90 seconds after reporting
those failures. No full-suite pass is claimed. Earlier baseline observations
below are historical, not the outcome after this routing change.


## Question

Does an ordinary coding goal reach the existing retained-repair mechanism,
learn from the first repair, and use that learning on a later related problem?

Reproduce with:

```sh
python3 coding_goal_reuse_probe_20261102.py
python3 -m unittest -v test_coding_goal_reuse_probe_20261102
```

The probe runs current checkout code from a disposable copy. Only the explicitly
labelled `typed_plan_unavailable` control monkeypatches the planner to simulate a
missing proposal. The copy is necessary because the live route writes default
state outside the separately configured R3 state path. It avoids modifying the
caller's stores; it is **not an OS security sandbox** and executes real repository
code and authored tests. Run only trusted checkouts. Each goal and direct
application runs in a fresh interpreter.

## Initial baseline, before the routing change

The underlying source is a pinned `boltons` module, with an authored off-by-one
fault and visible tests. The subsequent defect is a different literal in the
same function, not an independent upstream issue or a different library. A
separate authored audit fails before every run and is run after each attempt.
The audit is a useful independent check of outcomes, not independent personnel
verification or a proof of correctness.

| Route | Outcome | Separate audit after | Learning/reuse |
|---|---|---|---|
| Raw-goal first attempt | selected `python.tests.audit.unittest`; source unchanged | failed | execution-level `pass: true`, but semantic acceptance false; no permanent reuse authorized |
| Raw-goal cold attempt | selected the audit capability; source unchanged | failed | learning disabled in the request |
| Raw-goal warm attempt | selected the audit capability; source unchanged | failed | did not reuse a repair; no permanent reuse authorized |
| Direct repair, first | searched and repaired | passed | crystallized a skill |
| Direct repair, cold | searched and repaired | passed | retained learning disabled, one search |
| Direct repair, warm | repaired | passed | retained hit, zero searches, in a new process |

All visible tests remained unchanged. The direct cold and warm runs had the same
capable fallback solver. In this run the direct teaching, cold, and warm worker
wall times were about 1.55 s, 1.28 s and 0.60 s respectively, **excluding audit**;
the warm figure excludes the teaching cost. This single run does not establish
an amortized speedup. Raw and direct routes have different inputs and admission
policies, so their timings are not comparable.

The raw result's `pass` means its execution path passed, **not** that the user's
repair goal was accomplished: its status explicitly says raw acceptance receipts
are still required and `semantic_acceptance_complete` is false. Treating that
boolean alone as success would be wrong. The result does not authorize permanent
reuse. These are separate facts from the observed wrong choice of audit capability.

The raw attempts share the same R3 state path and copied default runtime stores;
the cold request disables R3 learning, but the experiment does not claim every
other memory mechanism is disabled. The direct route receives explicitly supplied
target, scope, dependency context, tests and database. The raw route receives a
plain goal and report location. Thus these arms locate a boundary; they are not a
controlled head-to-head proving that the front door would reuse the direct skill.

## First blocker and safe next action

The first observed break is **before learning can be tested from the goal**:
this plain repair request routes to an audit rather than a repair and leaves the
bug in place. A separate exploratory small calculator goal reached the repair
capability but was refused by `BOUND_CAPABILITY_INDEPENDENT_VERIFICATION_NOT_EVIDENT`;
the registry's verification says `SANDBOX_MEASUREMENT_ONLY` and explicitly does
not claim a two-carrier replay. That exploratory result is not part of the
reproducer above. Neither result is a reason to bypass or fabricate admission
or relax the semantic checks.

Next, investigate whether the guarded repair-routing and independently verified
admission paths can be reused through the actual fabric entry; obtain legitimate
independent evidence where required. Add a regression on an actual repair goal
that distinguishes running an audit from repairing, plus already-correct and
unrelated-task controls. Only after the route is legitimately available should
we connect or expose retained repair with carefully derived scope and state, and
repeat the fresh-process cold/warm test on genuinely different projects.

## Other verification this session

- `test_retained_repair_production_qualification_v1.py` and
  `test_creature_failure_continuity_v1.py`: 29 passed. Pytest was installed in a
  disposable external directory for this run.
- Ignorance ledger, associative memory and transfer-learning tests: 53 passed.
- The pre-existing `test_a_repair_sentence_that_names_no_test_still_repairs_the_source_v1`
  suite: 9 passed, 2 errored due to `GOAL_INPUT_BINDING_REQUIRED:synthesize_regression_test`.
  Those errors were observed before any tracked runtime edit; they were not fixed.
- The new probe test: 1 passed. No full-suite run was performed.

No runtime implementation was changed during that initial measurement. The
follow-up routing change and its limits are recorded at the top of this report;
neither step solves or claims to solve the complete creature loop.
