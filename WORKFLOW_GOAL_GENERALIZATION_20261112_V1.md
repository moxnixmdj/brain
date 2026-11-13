# Workflow goal generalization — 2026-11-12

Status: sandbox measurement and merged-runtime repair record. Authority: NONE. No capability, benchmark, family, ownership, or terminal credit is claimed.

## What shipped

PR #6793 adds a narrow, verification-gated generalization path for compiled workflow memory:

- `canonical/swe_kernel/workflow_goal_generalization_v1.py`
- `canonical/swe_kernel/causal_trace_to_skill_compiler_v1.py`
- `canonical/tests/test_workflow_goal_generalization_v1.py`
- a live-door repair in `canonical/runtime/live_brain_route_admission_v1.py`

A held-out wording can be admitted as a content-addressed goal variant only when it preserves the abstract workflow, binds new typed parameter values, passes held-out execution and postcondition checks, and survives sabotage/ownership gates. Unsafe control surfaces, ambiguous same-kind role alignment, and tampered variants refuse. Export/import binds the variant into the artifact SHA; empty variants are omitted so legacy bundle shape is preserved.

## What main already shipped

This PR is not the first structural generalization mechanism in the tree. Main PR #6805 already shipped:

- a structural/synonym goal binder with reordered key=value support;
- typed holes and an ambiguity guard;
- `anti_unify_workflow_examples` least-general-generalization support;
- a multi-token retrieval index;
- bridge and crystallizer tests for those behaviors.

Round-11 work on main also measured that the router answered 11/11 paraphrases with memory OFF, and that 4/6 refused ordinary tasks had no capability in the registry. That makes capability coverage, not retrieval matching, the measured ceiling for those cases.

The distinct contribution here is verification-gated variant admission and the merged-runtime repair that keeps that path reachable beside main's structural binder.

## Merged-runtime repair

After merging #6805, the first local 3-suite run was 6 failed / 113 passed. Two regressions were localized:

1. The wider structural fallback bypassed the negation/control guard, so a request beginning “do not rename …” could execute.
2. Main's word-accounting refusal became an honest final refusal before verified taught-workflow recall could answer, so taught rename/inline doors failed closed and declined-case reasons were lost.

The repair composes the binders:

- exact taught regex binding, with main's key=value misbind guard;
- verified goal variants behind `surface_is_safe`;
- main's structural/synonym fallback behind a structural surface guard;
- multi-token retrieval over the skill/variant token union.

The live door now lets verified recall answer only the capability word-accounting refusal. The workflow still executes confined and must pass its own postcondition. Other honest contract refusals stand.

## Local measurements

- Pre-merge 14-suite baseline: 227 passed, 2 skipped, 8 subtests.
- Post-resolution 15-suite targeted regression before later main syncs: 237 passed, 2 skipped, 8 subtests.
- After syncing `origin/main` `b56d981c`: 229 passed, 8 failed, 2 skipped, 8 subtests.
- Clean `origin/main` archive reproduces the same 8 failures:
  - 2 tracked-bundle/teach failures from `edit_by_example_v1` using a relative import inside confined exec;
  - 6 bridge failures from a class-count answer arriving as `"Found 1 classes"` where the bridge expects an integer.
- Unified model verifier: 33/33 PASS, sandbox measurement, not independent verification.
- Repo-integrity static guard: PASS.

The branch adds no new failure in that 15-suite comparison. The required referee check is the merge gate; the long heartbeat check was still running during the final sync loop.

## Honest verdict

Exact recall and permanence are real but narrow. A stored workflow can be recalled and executed with new typed values when the wording variant has been admitted and verified. That is not open-ended procedure induction.

One demonstration cannot identify a procedure in an open space. The repo's own identifiability probes found 14.1 surviving interpretations after one demo and 0/10 settlement; three demos reached 5/10; one demo plus about two chosen queries reached 10/10. The next sound step is chosen-probe settlement and adversarial held-out transfer, not a larger retrieval similarity score.

Permanence amplifies checker blind spots. A verified-looking artifact can persist a wrong abstraction if the oracle is weak. The variant path therefore keeps sabotage, ownership, postcondition, and confined-execution gates in front of persistence.

Public frontier numbers do not change this verdict. SWE-bench Pro V2 public-full is near saturation for the strongest listed systems (Opus 5: 99.40±0.40 full, 98.00 HARD on the cleaned 642-task split), while OSWorld 2.0's best listed binary success is 31.4% (68.3% partial). Near-saturation on a public coding split is not open-ended software engineering or computer use solved.

Sentience is neither implied nor evidenced by this work. The shipped mechanism is a model-free runtime artifact: admitted variants, typed binding, confined execution, and verification. It does not establish subjective experience, global extrapolation, or autonomous goal completion.

## External anchors

- SWE-bench Pro V2 leaderboard: https://labs.scale.com/leaderboard/swe_bench_pro_public_v2
- OSWorld 2.0: https://osworld-v2.xlang.ai/
- Agent Workflow Memory: https://arxiv.org/abs/2409.07429
- SkillGen: https://arxiv.org/abs/2605.10999
