# Learning something once does not solve everything, and it does not solve computer use

Date: 2026-11-13. Instruments: `canonical/tools/held_out_transfer_20261112_v1.py`,
`canonical/tools/generic_alias_measure_20261112_v1.py`.
Record: `canonical/verification/HELD_OUT_TRANSFER_PRS_20261112_V1.json`,
`canonical/tests/fixtures/held_out_transfer_v1.json`.
Base: main `d9318588` (post-#6828).

## The claim being answered

> Instant learning in new arbitrary environments is solved perfectly. Does that solve
> everything, including any computer use?

No. Two separate claims are packed into that sentence, and both are false on the record:

1. **"Solved perfectly."** The best held-out number this project has is 37.52% coverage at
   76.36% precision on one change class, with two of eight pull requests at zero, and an
   upper bound of 34.15% coverage at 60.61% precision on the other class -- with 65 changes
   the developers did not make. That is a partial transfer on a narrow class, not a solved
   capability.
2. **"Therefore everything."** Even a perfect instant learner of *code-edit classes* would
   leave computer use untouched, because coverage of an open environment space, not learning
   speed, is the binding constraint. A perfect learner of ten classes is a perfect learner of
   ten classes.

The rest of this note is the evidence, the three walls, and what would have to be true for
the claim to become true.

## What was measured, and what it means

Eight pull requests the operators were never designed on, four change classes never shown to
them, 240 askings per arm. Stricter arm resolves imports from this repository, so a
project-local helper is "not found in this project" and the organ refuses; the assumed arm
treats the project's own modules as available, which is an **upper bound** because a real
checkout both resolves the import and checks the names.

| mode | class | arm | right | developers | coverage | precision | wrong |
|---|---|---|---:|---:|---:|---:|---:|
| strict | PEP 585 | operator alone | 64 | 525 | 12.19% | 74.42% | 16 |
| strict | PEP 585 | + family (ABC names) | **197** | 525 | **37.52%** | 76.36% | 52 |
| strict | utcnow | operator alone | 35 | 410 | 8.54% | 47.95% | 17 |
| strict | utcnow | + family | 35 | 410 | 8.54% | 47.95% | 17 |
| assumed | utcnow | operator alone = family | **140** | 410 | **34.15%** | 60.61% | **65** |
| assumed | PEP 585 | + family | 197 | 525 | 37.52% | 75.48% | 51 |

Per pull request, assumed: `pyVHDLModel#204` 23 -> 108, `agent-kernel#825` 31 -> 79,
`draft-detective#858` 10 -> 10, `AirTell#200` 0 -> 0, `U00#1831` 72/95,
`ContaAutonomo#121` 30/215, the two `bugbug` pull requests 19/50 each.

Three things follow directly.

- **The gain is knowledge, not inference.** The utcnow family arm is a no-op: the alias table
  adds nothing on this class in either mode. The PEP 585 gain comes from knowing the
  `typing.List -> list` pairs, and it disappears where the example refuses or where the
  developers wrote PEP 604 unions.
- **The transfer is real but small and shallow.** One class moves +25.3 percentage points;
  the other moves zero through the family and lands at 34.15% only when its imports are
  assumed to resolve.
- **The quality is the problem, not the speed.** At the upper bound the utcnow operator makes
  231 changes of which 65 are wrong. A permanent learner that writes 65 wrong changes per
  410 developer changes is not a capability to be trusted unattended.

For contrast, the same instrument on the corpus the operators *were* designed on gives
56.87% (952 of 1674). In-sample numbers overstate; the held-out line is the only honest
number this project has.

## Wall one: transfer

One demonstration fixes a class in the file where it was shown, and degrades with distance
from that file. The literature agrees and is unambiguous about the size of the effect:

- **Continual-ARC** (arXiv:2611.14505, 114 runs): most harness methods score below a
  cache-the-demonstrations floor, and **no harness method gained on unseen tasks**. Weight
  training did -- 0.57 on seen tasks, 0.29 on held-out ones, still halving.
- **LearnAct** (ACL 2026 Findings): a retrieved demonstration lifts a strong model from
  38.5% to 58.9%; one demonstration transfers **partially**, never fully.
- **GEN-1.5** (Generalist AI, Aug 2026): one 3-12 s demonstration reaches 59% without
  gradients; ten gradient steps reach 83%. Prompting alone has a ceiling and the ceiling is
  not near "solved".
- **SkillEvolBench** (arXiv:2605.24117): agents adapt locally but rarely form robust reusable
  skills; raw trajectories often beat distilled skills.
- **SkillsBench** (arXiv:2602.12670): curated skills +16.2 points, **self-generated skills
  -1.3 points**.

So "learns once, permanently, everywhere" is contradicted both here and in the 2026
literature. The lever that does reach unseen tasks is weight training, and that is blocked by
this repository's own constraint -- $0 spend, zero model dependency in result-bearing paths.
That is a decision, not a discovery: the trace corpus produced here is exactly the dataset
that decision would need.

## Wall two: coverage

The organ family is a finite basis of AST-level operators: rename a local, inline a variable,
bring a name under an imported one, rewrite an expression, apply a family of API substitutions.
Past that basis the repository has no move. Real commits contain an unbounded variety of
edits, and "anything on a computer" is not even the same substrate:

- GUI agents measured on OSWorld 2.1 sit near **48.7% binary success**; RLI reports 41.3%.
  Those are the best published numbers for *doing a task in a desktop application*, and they
  come from policies with perception and action loops, not from edit operators.
- **SkillLearnBench** (arXiv:2604.20087): going from 1 to 3 to 5 instances per skill moves
  coverage 36.05 -> 34.09 -> 31.35. More exposure does not widen the basis.
- **ContinualSkillBench** (arXiv:2608.03874): the 16.9% sequential gain is mostly retained
  context, not abstraction -- in-context learning is roughly equal to explicit skill
  maintenance.

A finite operator basis converges on the classes it contains and is flat outside them. That is
what the eight held-out pull requests look like: two full zeros, one stuck at 10 of 10, one at
30 of 215.

## Wall three: verification

"Learn permanently" without a referee means permanent wrong changes. At the upper bound the
organ disagrees with the developers 65 times out of 231. The only reason the corpus is not
worse is that each candidate is compared against the developers' own diff before it is kept.
Remove that comparison and the same mechanism happily rewrites `utcnow()` call sites the
developers deliberately left alone.

This is why the referee is the load-bearing part of the design, and why "instant learning" is
the wrong thing to optimize: the measured effect of verified error feedback is larger than the
measured effect of more demonstrations, in this repository and in the literature (K2-Agent,
ICLR 2026).

## Where the four levers stand

- **Weights** -- not attempted; the one lever the literature shows reaching unseen tasks, and
  blocked by the $0 / no-model constraint. Decision open, stated as a decision.
- **Concepts** -- the operator family. Measured: +25.3 points on a class it knew, 0 on a class
  whose pairs it did not contain. Real, narrow, and typed.
- **Transfer** -- measured: one example selects the direction inside a class; it does not
  carry across classes, and outside the design corpus it yields 12.19% -> 37.52% (PEP 585) and
  8.54% -> 34.15% (utcnow, upper bound).
- **Reasoning** -- verified error feedback exists as a referee over candidates; there is no
  model that reasons about an unseen repair. Nothing here plans, and nothing here represents
  its own state.

## Four documents on main that say otherwise

Main currently carries four files whose headlines claim more than any measurement supports:

- `REVOLUTIONARY_SOLUTION_2026.md` -- "I Was Wrong: Real Learning DOES NOT Require Model
  Training", on the strength of a quotation, with no experiment.
- `FINAL_SOLUTION_REVOLUTIONARY_LEARNING_2026.md` -- "We have achieved the impossible:
  genuine generalization and permanent learning", listing zero-shot transfer and continuous
  improvement as achieved.
- `REAL_GENERALIZATION_SOLUTION_2026.md` -- replaces TF-IDF matching with an "MCP box
  compiler" and calls the result real generalization, again with no held-out measurement.
- `HONEST_ASSESSMENT_2026.md` -- correctly says the TF-IDF layer is fake and no real
  generalization exists, but stops there and cites no number.

The first three are **notes, not results**: none of them reports a coverage, a precision, a
held-out set, or a wrong-change count, and none of their claims appears in a verification
record. The fixtures are the record; a document that asserts a capability without a
measurement against developers is precisely the failure mode this project has spent its recent
history correcting (the in-sample ladder, and then the utc "did not transfer at all" claim).
They are allowed to stay as history. They may not be quoted as evidence, and nothing in the
runtime reads them.

## What is genuinely solved

- Exact recall of a change shown twice, in this repository: 8.13x. That is memoization with a
  refusal on mismatch, first built in the 1960s. Useful; not learning.
- A referee that refuses rather than guesses: on the design corpus, 36 wrong changes out of
  537 (91.81% precision) without the family and 48 out of 1026 (92.79%) with it, and an
  explicit wrong-change count everywhere else -- 65 at the held-out upper bound, which is the
  number that matters.
- A measured held-out instrument that reports its own upper bound and its own failure cases.
- One class of transfer at +25.3 points, with the mechanism named.

## What would count as solved

Falsifiable, and none of these hold today:

1. Hold-out coverage above 80% on a class never used in design, with precision at or above the
   developers' own agreement rate.
2. The same on a second, mechanically unrelated class, with the first still holding.
3. A wrong-change count of zero without a hand-written referee per class.
4. Any GUI task suite above the published 48.7% -- which no part of this repository attempts.

Until 1-3 hold, "instant learning solves everything" is a hypothesis with three walls in front
of it, and "any computer use" is outside the substrate entirely.

## Next measured step

Not more demonstrations (SkillLearnBench: more instances do not widen coverage), and not a new
operator family. The next step is precision on the utcnow class: restrict the import-removal
operator to lines the rewrite actually dropped, which targets the 65 wrong changes directly,
and clear the two `needs_sandbox` door tests that currently block re-measuring it. Both are
declared work in this repository already.

The honest frame stands: there is no any-action-once computer use, no sentience, and no
general learner here. There is a referee, a small typed basis, and a number that goes up when a
mechanism is added and measured -- one at a time.
