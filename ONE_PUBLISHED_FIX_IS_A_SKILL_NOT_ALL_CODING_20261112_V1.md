# One published fix is a skill, not all coding

2026-11-12 · authority NONE · zero model calls in the measured path

## The question, answered by execution

Can the existing learner be shown a real coding fix once, keep what it was shown, and use it on
other code? Yes, it can derive operators and reproduce this repair. Does that make it able to repair
all other bugs, let alone perform arbitrary computer use? This measurement does not support that.
The distinction is the lesson's applicability, not whether the bytes can be retained.

No new learner was written. `canonical/tools/one_published_fix_counterfactual_v1.py` reuses:

- `canonical/runtime/edit_kind_learning_v1.py` (`Lessons.learn` / `proposals`);
- `canonical/tools/quixbugs_one_fix_transfer_measure_v1.py` (published-fix extraction and project layout);
- `ProjectTestOracle` (the upstream tests in copied projects, fresh test subprocesses, nonzero-test
  acceptance). No pytest stand-in or substituted test oracle is used.

## Selection and protocol

Upstream: [jkoppel/QuixBugs](https://github.com/jkoppel/QuixBugs), revision
`4257f44b0ff1181dedaedee6a447e133219fcebf`. The runner refuses a different revision or dirty checkout.
It selects the first alphabetically of the 40 programs as the single teacher, and all remaining
39 as targets. This rule, the ten-candidate maximum, eight-second test timeout, and empty/forward/
reverse arms were written into the runner before its measured run. They are not externally
preregistered. No other teacher was tried after this result.

The teacher is `bitcount`: `n ^= n - 1` becomes `n &= n - 1`. Only this published before/after pair
enters the learner. The reverse arm receives the same pair backwards. The empty arm receives none.
Target reference programs calibrate the test oracle and allow a strict AST comparison after an
accepted candidate; they never enter candidate generation. Memory is frozen during evaluation.

Each arm's complete generation runs twice in separate Python processes, loading the same saved
lesson bundle and re-deriving operators. This tests repeatable reconstruction from saved examples,
not a runtime memory format or an unbounded permanence claim.

## Measured result

| Arm | Lessons / operators | Same-bug accepted repair | Other bugs repaired | Target candidates tested |
|---|---:|---:|---:|---:|
| Empty | 0 / 0 | no | 0 / 39 | 0 |
| Forward | 1 / 6 | yes, rank 1 | 0 / 39 | 0 |
| Reverse | 1 / 6 | no | 0 / 39 | 0 |

The forward repair matches the published fix's AST and passes **9 upstream tests** twice. Generation
matches after fresh-process reconstruction for all three arms.

**Zero target candidates** is the important localization: this particular learned edit pattern has no
applicable sites in these other programs. The failure is before test-guided selection, not a test
budget exhausted on bad repairs. Increasing the ten-candidate limit would not help this result.
It says nothing about whether another lesson or the full repair solver could solve those bugs.

All 39 target reference repairs pass their selected upstream tests; none was excluded. Of the target
buggy baselines, `sqrt` times out with zero counted tests, and `find_first_in_sorted` yields an oracle
`TypeError` with no counted result; the other 37 have counted failing tests. The teacher's buggy
baseline also times out (return code 124, zero counted tests). These two target baselines are not
claimed as counted assertion failures. They remain in the 39-program candidate-coverage diagnostic
because their references pass; no candidate was generated for them (or any other target). The oracle
error is retained, not repaired or silently converted into a test failure.

Record: `canonical/verification/ONE_PUBLISHED_FIX_COUNTERFACTUAL_20261112_V1.json`. It includes
per-target calibrations, arm outcomes and candidate counts, bounded-project file digests, source
hashes, controls, and limits. Eight new unit tests exercise forward/reverse direction, unrelated
syntax, fresh-process reconstruction, confirmation refusal, strict-match separation, and accounting.
The new tests plus existing edit-kind and claim-adjudicator tests: **83 passed** locally.

## We already had a larger experiment

Searching before rebuilding found
`canonical/verification/HUMANEVALFIX_EXPERIENCE_STREAM_20261112_V1.json`. Its archived first order
reports, on 100 previously studied bugs:

| Arm | Passes the tests | Right as far as additionally checked |
|---|---:|---:|
| Cold solver | 53 | 36 |
| Learner retaining its own repairs + solver | 64 | 45 |
| Reverse-direction lessons + solver | 62 | 42 |
| Published fixes shown after each bug + solver | 65 | 45 |

These are **archived results, not rerun in this round**. The archived fixed-threshold adjudicator
reports `NO_COMPOUNDING`, not perfect instant learning. It notes unequal extra search work, recorded
rather than live cold-solver outcomes, a post-hoc retention rule, sampled correctness checks, and no
independent reproduction. The reverse control retains structural information; its gains cannot be
called proof that memory contributed nothing. Its similar performance does show why raw gains over
a cold solver should not all be attributed to learning the right repair direction.

The new one-fix run does not replace this larger result or compare with the full cold solver. Its
empty arm is deliberately only the candidate learner without lessons. All arms have the same
maximum candidate budget but need not spend it. No claim of equal wall-clock costs or competitive
benchmark performance is made.

## First principles and recent research

One successful experience constrains a behavior. To use it safely elsewhere requires that:
(1) the retained rule expresses the relevant behavior; (2) the new task is in its domain;
(3) its dependencies/preconditions hold; (4) composition does not invalidate it; and (5) an adequate
acceptance test checks the outcome. Neither persistent storage nor one successful demonstration
implies those conditions universally. A prior can make one example sufficient for a bounded rule;
it does not make every rule identifiable from every one-example showing.

Recent sources consulted on the session date (November 12, 2026):

- [Continual-ARC code/protocol](https://github.com/unifyai/continual-arc) separates fresh instances of
  seen tasks from unseen tasks and freezes the learner for evaluation. That separation is useful
  here: repeating the teacher is not transfer to the other 39 programs.
- [KEEL, October 25](https://arxiv.org/abs/2610.34043) uses verifier evidence to support, contradict,
  replace and retire skill claims. This supports retaining scope and contrary evidence with a
  skill, not treating every successful trajectory as permanently valid knowledge.
- [K²-Agent, ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/file/b078eaadc927d7f7ae67371c1363195b-Paper-Conference.pdf)
  describes single-demonstration bootstrapping together with iterative feedback and trained
  execution. 'One demonstration' does not mean no prior training, no subsequent feedback, or
  universal success. Its pretrained-model producer route is not adopted under Brain's ownership law.

These sources were read, not experimentally reproduced here. No claim that this approach is novel,
revolutionary, state of the art, or competitive with current agents follows from this run.

## What to do, and what not to do

Do not keep showing arbitrary unrelated tasks and expect exposure alone to solve applicability.
Do not expand the generator to manufacture candidates merely to improve this selected benchmark.
Do not hide negative results by changing the teacher or widening a gate.

For useful learning now, teach an actual task-relevant operation with an acceptance test, then test
new instances **inside its claimed applicability class**, plus contrasting cases where it must not
act. Compare against the full cold solver and an equal-work control before claiming efficiency.
Independently reproduce any gain before promotion. The existing larger experiment already shows
that a broad exposure campaign is not a substitute for this causal test.

The concrete result here is one supported repair and an explicitly located transfer boundary. It
is not an advanced-software-engineering agent or a general computer-use solution. No registry,
learner state, family verdict, tolerance, or terminal truth was changed. No sentience experiment was
performed; storing and reusing a rule is not evidence of subjective experience.
