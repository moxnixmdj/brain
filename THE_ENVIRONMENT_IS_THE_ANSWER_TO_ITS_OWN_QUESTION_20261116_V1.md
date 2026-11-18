# The environment is the answer to its own question

*Round 8. 2026-11-16. Branch `arena/006395f8-brain`, base `f79f9566`.*

## The question you are asking, stated as a testable claim

> Give the model the smartest actions, let it experience each **once**, and it learns them permanently. Do
> that in any new environment, and anything on a computer is solved — the most advanced coding included.

That is a claim about **evidence**, not about intelligence, and it decomposes into four propositions. Only
the fourth was still open when this round started.

| proposition | verdict | evidence |
|---|---|---|
| One exposure identifies an action | **FALSE** as usually stated | round 6: 0 survivors of a single exposure; one witness leaves 6.9% held-out accuracy |
| A learned action stays learned across a release | **FALSE** | round 6: 31% of observable actions moved on a major bump |
| …and moves *silently* | **FALSE as measured** | round 6: 13 of 13 moves caught, 0 blind |
| **An environment can be made to exhibit an action at all** | **this round: 73.7% of the previously impossible set** | 28 of 38 actions that no scalar witness could ever reach are exercised *by the environment's own tests*, and 22 of those 28 (78.6%) move at the next release |

So your sentence is right in its mechanism and wrong in its assumption. The mechanism — exposure, then
permanence — is sound where the exposure is real. The assumption — that the exposure exists — is what all
eight rounds have been circling. **The bottleneck was never learning. It was evidence.**

## What was built

`scenario_observation_v1.py`. No model, no prompt, no fixture library, no new grammar. It runs the
**environment's own test suite** under a recording tracer and writes down, for every call into the package:

- which callable, and **its own arity** (read from the live code object);
- `RETURNED|<normalised digest>` — exact for literals and JSON-able structures to depth 2, **type-only for
  objects**, because an object's `repr` carries addresses and timings and would make every revision look like
  a move;
- or `RAISED|<exception name>`.

Hex addresses and tmp paths are erased; the old suite is executed **twice** at the same revision, and
disagreement is refused as `NONDETERMINISTIC_AT_OLD` rather than counted.

Two 2026 lines of work converge on this exact object and both then reach for a model. The specification-mining
literature calls it the carrying object: *"construction and call arguments, selected pre-state and post-state
values, and whether the call returns normally or throws"* (arXiv 2608.13240, Aug 2026) — and infers JML
contracts from it with an LLM, 11 of 22 tasks. `wrapture` (Sep 2026) ships the same record shape as a library.
**The record is the innovation. The model in front of it is the part we delete.**

## The measurement, on round 6's denominator

82 real actions, 11 real modules, three real release bumps. 38 of them could never be exercised by scalar
witnesses — the dangerous class from round 6.

| | round 7 (lookup) | **round 8 (execution)** |
|---|---|---|
| previously unexercisable actions reached | **1 (2.4%)** | **28 (73.7%)** |
| of those, moved by the release bump | 0 | **22 (78.6%)** |
| cost | $0 | $0 |
| model calls | 0 | 0 |

Distribution of what happened to all 82 actions: **19 signature changes,
5 value changes, 8 stable, 1 exercise-mix change (a test change, not a move), 47
never reached, 2 gone at the new release**; among the 38 previously-unexercisable actions alone the split is
**17 signature, 5 value, 5 stable**.

That is a **28×** unlock over round 7 on the same denominator and the same repositories — and, for the first
time in this series, a class that was previously **invisible and immovable** became both visible **and** moved.

## Why this is not a metric artifact — three checks

1. **tomli 2.0 threaded a nesting level through its entire parser.** Observed: 19 of 21 `tomli._parser` actions
   changed signature, e.g. `skip_chars` `RETURNED|None|arity=2` at 1.0.0 → `RETURNED|10000|arity=3` at 2.0.2,
   over 1214 real observations. The arity is the function's own `co_argcount`; no digest can invent it.
2. **packaging 24.0 added validation to `canonicalize_name`/`canonicalize_version`.** Observed: both changed
   arity 1 → 2 and gained `InvalidName`/`InvalidVersion` outcomes.
3. **packaging 24.0 began rejecting versions inside filenames.** Observed: `parse_wheel_filename` and
   `parse_sdist_filename` gained `RAISED|InvalidVersion` and **lost nothing** — a pure tightening, exactly what
   the release notes describe.

## What is still refused, by name

| refusal | count | meaning |
|---|---|---|
| `REFUSED__NOT_REACHED_BY_OWN_SUITE` | **47 of 82** | the environment's tests never call it |
| `REFUSED__GONE_AT_NEW` | 2 | removed in the later release |
| `NONDETERMINISTIC_AT_OLD` | 0 | two runs of one revision never disagreed here |
| incomplete suite | 6 of 11 modules | packaging 21.0's own tests need dependencies this sandbox lacks; the observations are still real executions, but partial — `packaging.markers` reaches 0 of 6 for that reason, not because it is unreachable |

`pypa/pyproject-hooks 0.0.1` still does not materialise (known since round 6) and is excluded, not counted.

## The honest answer to "so is everything solved?"

No — and this round says precisely why, in numbers rather than in rhetoric.

**52.6% of actions are never called by their own environment.** Not because they are hard to learn, but
because **no one ever wrote the scenario that reaches them**. A training loop on such an environment would
have produced exactly zero signal for them — the same zero, for the same reason, forever. That is the real
shape of the wall: it is not a learning wall, it is a **driving** wall.

And the second half of your claim — *"the model learns it permanently"* — is answered by round 6 with a number
this round makes sharper: **78.6% of newly-visible actions move at the next release.** Permanence is not free;
it is bought by a check that must be re-run. What survives is not the action, it is the **check that verifies
it**, which is exactly the tree's `permanence_amplifies_check` law arriving from the other direction.

## What is real, what is not, and the smartest next thing

**Real**
- An environment that can execute an action once can be made to prove it, twice-stably, for $0, with no model.
- 73.7% of the previously impossible class is reachable that way; the remaining 26.3% are named, not hidden.
- Moves are caught with both sides of the evidence recorded, so the claim is falsifiable by anyone who reruns it.

**Not real**
- "Experience it once and it is permanent" — 78.6% of what you learn this way has a shelf life measured in
  releases, and saying otherwise would be the exact self-congratulation you warned about.
- "Anything on a computer, solved" — computer use has the same structure and the same wall: an action is
  learnable only where the environment will *exhibit* it, and a GUI will only exhibit what a scenario drives.

**The single bottleneck, now:** `REFUSED__NOT_REACHED_BY_OWN_SUITE` — 47 of 82 actions. Closing it is not a
learning problem, it is a **search for a driving scenario**: compose a call path from public entry points until
the target is reached, and accept only when **execution** confirms the reach. That is the first round where
search is genuinely required, and it must be searched against execution, never against text — because text is
what round 7 proved worthless here at 2.4%.

## Where the series stands

| round | organ | result |
|---|---|---|
| 1 | experience → actions | cost law; `p_correct` 0.2978 |
| 2 | differential pins | 13 drivable, 0 pins |
| 3 | structure → laws | 188 laws, 0 kills |
| 4 | instruction → contract by occurrence | site missing |
| 5 | site by intervention | 1 of 40 usable |
| 6 | permanence on real releases | 31% move, all loud; **39% never learnable** |
| 7 | arguments from the environment's proofs | **1 of 41 (2.4%)**; lookup is capped |
| 8 | **observation by the environment's own execution** | **28 of 38 (73.7%) reached; 22 move, both sides recorded** |

Round 7 proved that the environment's text cannot construct its own arguments. Round 8 proves that the
environment's **execution** does not need to: it already has them, every time its own tests run.

*Reproduce:* `.venv/bin/python canonical/swe_kernel/scenario_observation_v1.py --json
canonical/verification/SCENARIO_OBSERVATION_20261116_V1.json` (~100 s, no model, $0).
