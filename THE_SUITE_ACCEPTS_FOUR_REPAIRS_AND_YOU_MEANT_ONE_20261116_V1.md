# The suite accepts four repairs. You meant one.

Round 13. Branch `arena/1300ffbf-brain`, from `ebb8f636`.

## The question, in your words

If we give the system the smartest possible actions, why can't it learn them once and keep them forever?

Rounds 9 to 12 answered the easy half. Acquisition is instant and free. Retention is free. The
representation costs nothing. What kept failing was never the learning. Round 12 ended with a census
that named the reason: over 191 real changed sites, a missing check is 10.5%, replaying a seen edit
covers 49.2%, and **40.3% needs code that does not exist yet**. Learning cannot supply code that does
not exist. So this round did not build another learner. It went after the other term.

## What this round actually did

The tree already owns a repair aimer. `aimed_edits_from_the_program_and_the_failure_v1` built
predicates out of what the program imports and judged them with the commit's own tests, and it was
measured on the unsolved set: **13 of 46** tasks recovered. Every round before this one threw away
everything except the first repair that passed. That is the bug in the method, not in the code: the
first passing repair is not *the* repair, it is *a* repair, and nobody checked how many others exist.

So the instrument is small and it only changes one thing. It enumerates every repair the machinery can
build — seats crossed with terms crossed with operators — keeps **all** of them that pass the commit's
own suite, and reports the size of the set. Then it reads the set for what it is: a version space.

## What came back

Seventeen real fix commits, each judged by its own tests.

* On **16 of 17** the machinery cannot build a repair at all. `REFUSED__NO_PARTITION`, by name. That is
  the coverage wall this project has measured for six rounds and it did not move.
* On the **one** it can — `pypa/packaging` `022ae6c6`, `metadata.py`, 344 tests — the suite accepts
  **four** different repairs at **four** different guards:

  * line 766, refusing on `'..' in path`, message *"parent directory indicators are not allowed"*
  * line 771, refusing on `'*' in path`, message *"paths must be resolved"*
  * line 775, refusing with `is_absolute()`, message *"paths must be relative"* — **what the human wrote**
  * line 782, refusing on the posix delimiter, message *"paths must use '/' delimiter"*

Four implementations. Four behaviours. One human. And all **4 of 4** pass the exact verifier — the same
344 tests that this project has used as the arbiter of every claim since round 9.

## What that means, stated without decoration

The verifier is exact about **behaviour** and completely silent about **intent**. So the sentence
"learn it once and keep it forever" has a precise status, and it is not the status I gave it in rounds
9 to 12:

* For **behaviour**, permanence is real and cheap. What the tests accept, the tree can keep, replay and
  re-verify at zero cost.
* For **intent**, permanence is not undefined because memory is weak. It is undefined because the
  specification never picked a member of the set. There is no fact of the matter to keep.

The bottleneck is not retention. It is **identity**: which of the four was meant. Every "learning
zero" in rounds 9 to 12 sits inside this. The agent was not failing to remember. It was succeeding at
remembering *something else*.

## The one constructive thing this round adds

If the suite cannot choose, the chooser has to be the person, and the person cannot be asked
"line 766 or line 775". They can be asked something else, and that something is computable from the
version space without a model, a network call or a single training example.

Each repair refuses at a different guard, so each repair **tells the user something different**. Take
the failing value the machinery already recovered — `C:LICENSE` — and read the raise out of each guard:

> For `license_files=["C:LICENSE"]`, what should the error say?
>
> 1. `'C:LICENSE' is invalid for 'pkg', parent directory indicators are not allowed`
> 2. `'C:LICENSE' is invalid for 'pkg', paths must be resolved`
> 3. `'C:LICENSE' is invalid for 'pkg', paths must be relative`
> 4. `'C:LICENSE' is invalid for 'pkg', paths must use '/' delimiter`

You can answer that. You do not need to read code, know a line number, or know what a guard is. And
one answer collapses four implementations to the one you meant. The instrument prints this question
mechanically — `question_from_repairs` groups the passing repairs by the message their guard emits and
emits one option per group. It fired on the one task where a version space exists, and it produced
exactly the four options above, with the human's choice inside them.

That is not a new organ and I will not pretend it is. It reuses the differential, the seats, the terms
and the judge, and the only new line of thinking is *keep the set*. It is the thing every previous
round deleted.

## The honest ceiling, and why 40.3% is still out

Multiply the two numbers and you get the fraction of real work this architecture can be *right* about
rather than merely *consistent* about:

    reach 1/17  x  identifiability 1/4   ->  a repair that is both buildable and intended

That is the arithmetic behind "how much of an agent's competence is permanent": the part that is
specified. Not the part that is stored.

And the feature bucket stays out, for a reason that no question fixes. The same commit `4b243af9`
wants `__replace__`: a sentinel default per field, field-wise copy, re-parse for validation, deepcopy of
the specifier, and a round-trip rejection when a field parses as more than itself — forty lines, from a
change request one sentence long. The tests say *"returns a copy with the field replaced, and validates
and normalizes"*. That sentence under-determines an unbounded design space. Asking you "how should
`replace` behave when a field is invalid?" narrows it; it does not write it. Someone — a model, a human,
or a synthesizer over a space that contains the answer — still has to author code. This tree refuses
models, and it has no space that contains `__replace__`. So the honest statement is: **the 40.3% is not
addressed by this round, and the measurement now explains why it cannot be addressed by any mechanism
that reads a trace.**

## Computer use, briefly

The structure is identical and the vocabulary is friendlier. A GUI trace under-determines intent the
same way: "it clicked Save" is consistent with *commit* and with *save a copy*. The version space is
real, the discriminating action is a behaviour the person can describe in their own words, and the
extra term that GUI adds is horizon — how far ahead the specification must reach before a question can
even be asked. Nothing here says GUI is easier. Round 12 already corrected that: OSWorld sits below
SWE-bench at the frontier. What this round adds is that the *ask* is the same mechanism on both sides.

## What would be dishonest to claim here

* That the four repairs are equivalent. They are four behaviours. Two of them reject a path the human's
  code accepts.
* That one task is a distribution. It is one in seventeen, and the reach number is the reason the
  version-space number is not the headline.
* That asking closes the feature bucket. It bounds it. The code still has to come from somewhere, and
  in this tree that somewhere does not exist yet.
* That the tree is now better at computer use. It is better at *knowing when it does not know*, which
  is the precondition, not the result.

## Reproduce

```
.venv/bin/python canonical/swe_kernel/passing_repairs_version_space_v1.py --limit 9 \
    --json canonical/verification/PASSING_REPAIRS_VERSION_SPACE_20261116_V1.json
.venv/bin/python canonical/swe_kernel/passing_repairs_version_space_v1.py --limit 24 \
    --json canonical/verification/PASSING_REPAIRS_VERSION_SPACE_WIDER_20261116_V1.json
.venv/bin/python -m pytest canonical/tests/test_passing_repairs_version_space_v1.py -q
```

Model calls 0. Network calls 0. Spend $0. Authority: sandbox measurement, not independent verification.

## The next term

Round 12 said the bottleneck was the specification and the shape of the change. Round 13 sharpened it:
the bottleneck is **identity** — which behaviour among the ones that pass. The next round's target is
therefore not a synthesizer for features and not another learner. It is the only thing that makes a
question worth asking: **a version space large enough to be honest, enumerated by a mechanism that
covers more than one commit in seventeen** — because on the other sixteen there is nothing to ask
about, and refusing to ask is the whole capability.
