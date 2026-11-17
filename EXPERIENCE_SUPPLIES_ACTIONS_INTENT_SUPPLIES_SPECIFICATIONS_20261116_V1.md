# Experience supplies actions; only intent supplies specifications

You asked again, in the same words, and the words carry the answer's shape: *instant learning is solved, so
give the model the most advanced actions, let it experience each once, learn it permanently — and everything
on a computer, including advanced software engineering, is solved, permanently. Am I right?*

**Right that one demonstration is enough to add an action permanently. Wrong that this is the thing standing
between us and everything.** Three rounds have now built the three mechanisms that could have closed the gap,
and all three were refused by measurement — not by argument, and not by a missing feature.

## The claim, and the term it dies on

```
P(solved | work) = SPECIFIED(work) × [ MEMORISABLE + AIMED_EDITS ] × VERIFICATION
```

Experience enlarges `MEMORISABLE` (4.814% of real fixes) and improves the ordering of `AIMED_EDITS`. It
touches `SPECIFIED` — the share of work that arrives with a checkable statement of what is wanted — **not at
all**. And `SPECIFIED` is the term that decides whether anything can be learned, verified or composed in the
first place.

## This round: the third route, and the strongest one

The tree already owns a specification machine that needs no test, no intent and no model:
`specification_from_structure_v1.py` reads laws off a module's own names, arities, annotations, inverse pairs
and standard-library references (`normalize` ⇒ fixed point, `dedupe` ⇒ set preserved, `isabs` ⇒ differential
against `posixpath.isabs`), confirms them by **executing the module as it stands**, and refuses anything
vacuous or already refuted. Its published measurement is on this repository's own code: 407 laws confirmed,
8 mutants killed, blind-spot rate 0.652.

What nobody had measured is the question this project lives on:

> Take a **real commit**. Confirm the laws of the module *after* the change. Then put the module *before* the
> change in front of that judge. Does any confirmed law reject it?

That is not a metaphor: the organ already takes variants, and the parent is just another variant.

### The result on 40 real commits

| | |
|---|---|
| real commits, both states materialised | 40 |
| shipped their own tests | 21 |
| shipped none | 19 |
| judged by the organ's own laws | 40 |
| **laws confirmed** | **188** |
| **commits rejected by any law** | **0** |
| of the unguarded 19: rejected | **0** (57 laws confirmed) |
| confirmed law kinds | **TOTALITY 174 · IDEMPOTENCE 14** |
| excluded, not refused (the organ's child failed) | 3, named |

**Zero kills out of 188 confirmed laws.** And the instrument is proven able to kill: a parent whose `normalize`
is not a fixed point is rejected by `IDEMPOTENCE`, a parent whose `dedupe` returns `[]` is rejected by
`SET_PRESERVED`, and a parent that raises instead of returning is classified separately as bare totality and
counted as zero. All three are pinned as tests, so the zeros cannot be a broken instrument.

### What the zeros mean — the part that is actually new

1. **Structure can barely *state* a law about real library code.** 174 of the 188 confirmed laws are bare
   totality ("it returned where it returned"); only 14 are anything stronger. `parse_requirement`,
   `loads`, `platform_tags` do not imply fixed points or round-trips to their structure.
2. **Where a law can be stated, real changes do not violate it — they extend the specification.** A new error
   message, a widened accepted set, a new branch: none of these is a violated property. They are *new claims
   about what should happen*, and a claim that has not been made cannot be derived from the artifact that has
   not made it yet.

## Three routes, three zeros, one cause

| route by which the artifact might have supplied a specification | built | result |
|---|---|---|
| vocabulary + witness inversion (invert the demanded value at the localised site) | ✔ | 18 witnesses, **0 invertible** — the demanded content did not exist in the artifact |
| behaviour + behavioural probing (differential pins, the artifact's own literals and doctests) | ✔ | 13 drivable unguarded commits, **0 stable pins**; doctests discriminate **0** times because they move with the code |
| structure + generic laws (this round) | ✔ | 40 commits, **188 laws confirmed, 0 kills** |

That is not three failures of three features. It is one fact measured three ways: **the specification for new
work does not exist anywhere inside the artifact**, because the work exists precisely to create it.

## What is real and what is not

**Real.** One execution plus a sufficiency verdict settles an action whose survivors agree. Instant learning of
a new environment is a genuine cost law — 29 trials, payback at 25.78 requests. The edit space read off the
program in front of it solves 8 of 8 published QuixBugs bugs with zero model calls. Verification is exact and
cheap, and it is why coding compounds while creative work does not. Nothing here needs a model, a parameter
holding knowledge, or an external service — that premise survived this round untouched.

**Not real.** That experience is the limiting term. That reach follows from repetition (75.2% of real fixes are
named by no other task's fixes; 18.7% coverage with every other task as experience). That a perfect oracle
makes an unexpressible edit namable (18 of 18 refusals). That checkability can be manufactured from the
artifact (0 of 13 by behaviour, 0 of 40 by structure). That an agent can grade its own homework (9.6% of 1,000
audited AI-written tests were useful verification checks).

**Declined.** Sentience. It is unmeasurable, and it is the most expensive idea in this project because it makes
you spend on *being more* when the ceiling is on *being able to check more*. We are building a capability
engine, not a creature. The word buys nothing a measurement can use.

## Is this revolutionary versus how agents learn today?

Partly, and the honest part is narrower than the ambition. Frontier agents improve by putting knowledge into
parameters and by generating volumes of self-graded experience — and the field's own 2026 numbers say the same
thing this tree measured: 27% of changed Python lines are executed by any existing test, 64.8% of Python PRs
have no changed line executed at all, and test-time self-improvement is "gated by the same bottleneck: the
verifier". The revolutionary part of what we have is not the learner. It is that actions are learned from one
demonstration **without gradients**, that the edit space is read off the artifact rather than imagined, and
that verification is exact and model-free. The part that is *not* revolutionary, and cannot be, is the
specification.

## The single bottleneck, and the smartest next move

**The bottleneck is the specification of new behaviour, and it arrives only from outside the artifact: from a
stated intent, a demonstration, or the witness a failure supplies.**

So the next round does not build another learner, another grammar, another probe alphabet or another law
derivation. It builds the **intent compiler**: from the user's own sentence plus the environment's own
observables, construct the discriminating pair (input, expected outcome), and hand it to the exact verifier and
the aimed-edit space that already solve 8 of 8 when such a pair exists. That is the only lever whose ceiling is
still open, and it is the only one this project has not already measured and refused.

Reproduce everything above with:

```
.venv/bin/python -m pytest canonical/tests/test_structural_check_of_real_changes_v1.py -q
.venv/bin/python canonical/swe_kernel/structural_check_of_real_changes_v1.py --corpus --limit 40 \
    --json canonical/verification/STRUCTURAL_CHECK_OF_REAL_CHANGES_20261116_V1.json
```
