# If the word were given, is only its slot unknown?

**Round 24. Receipt: `canonical/verification/THE_WORD_IS_GIVEN_AND_ONLY_THE_SLOT_IS_UNKNOWN_20261119_V1.json`. Tool: `canonical/tools/the_word_is_given_and_only_the_slot_is_unknown_v1.py`. 14 tests. 73 real refused suites executed. Zero model calls, zero parameters.**

## What this round was for

Round 23 ended by naming a mechanism: *manufacture speaking checks from the repository's own assertions.* Before building it, its two preconditions had to be measured, because if either fails the synthesizer is wasted work:

- **(A) is the word supplied?** — a speaking check is one whose own text contains the word the fix must introduce.
- **(B) is the slot local?** — given the word, is *where it goes* confined to the function the machine refused in?

Both were measured on the same 87 real fixes, executing the real upstream suites in their refused state.

## The numbers

| | |
|---|---|
| refused states executed | **73 / 87** (12 could not run; recorded, never scored) |
| **the machine points into the *source* at all** | **13 / 73 = 18%** |
| fixes with a new word | 57 |
| **all of the fix's new words present in the check or the refusal** | **5 / 57 = 8.8%** |
| some of them present | 30 / 57 = 53% |
| change lands in the refusing function | 10 / 13 sited = 77% |
| **ceiling of the mechanism: word supplied AND slot local** | **2 / 73 = 2.7%** |

## What that kills, and why it matters

**The speaking-check + slot-search mechanism is dead, and it died before a line of it was written — which is the point.** Its ceiling is 2.7%. Two independent walls:

1. **The machine usually does not point at the site.** For an `assert` failure on a returned value, the frames stop in the *test*: the code that produced the wrong value has already returned, so nothing in the traceback names it. 82% of real failures are of this kind. The "localisation" that this project and the field both lean on is not something the machine provides for value failures — it is an *inference*.
2. **The word is almost never fully supplied.** Even granting a check that speaks and a refusal that names, *all* of a fix's new words are present only 8.8% of the time.

So the previous round's closing line was too optimistic, and the correction is the real result: a refusal that names a word is not the same as a specification that contains the fix.

## The deeper correction: repair is abduction, not identification

Operators are *identification*: the world produces the observable (bytes, exit codes, trees), one execution pins the hypothesis, and the value of that is now three receipted layers deep. Edits are **abduction**: from a behavioural mismatch at the boundary (`assert f(1) == 3`), hypothesise an internal cause. The mismatch is observed; the cause is not. That is why every measured route to a proposal has come back short:

| route to a proposal | measured outcome |
|---|---|
| one experience per action | 123/160 wrong (operators only) |
| a bigger vocabulary / seed corpora | 0 gained, 1 lost (round 21) |
| the file's own alphabet | 0 of 8 one-token fixes (round 22) |
| blind generate-and-verify | 4,581 executions per fix (round 22) |
| the refusal's own words | 32% named, 0/5 for literal fixes (round 23) |
| the check's own words + local slot | ceiling **2.7%** (this round) |

Six routes, six walls, and each wall is in the same place: **the observation that would identify an edit does not exist in the machine's output.**

## The single bottleneck, restated precisely

Not experience. Not vocabulary. Not checks that speak. **The observation that identifies a hypothesis — for edits, the *provenance of the wrong value*.**

An operator's effect is identified because the machine hands over the *whole* post-state. A wrong output is identified the same way: not by the assertion, which only says "wrong", and not by the traceback, which only exists if something raised, but by **the expression instance that produced that value and the operands it used**. That is machine-produced, needs no model, and no current system reads it — the field settles for stack traces and instrumented prints it asks a model to place.

This is not a new idea in this project; it is **the law this branch already proved twice**, applied one level down: *an effect is a provenance map from output bytes to input arguments* (round #7009). The analogous map here is from the rejected value to the expression and operands that produced it. `dir()` and `sys.settrace` can supply it; nothing has to be learned, and nothing has to be guessed.

## The smartest next build

**Value provenance: turn every assertion failure into a site and an operand list.** Trace the execution of the failing test, record for each value the expression instance that produced it, and when an assertion rejects a value, hand back *where it came from and what it was built from*. Then:

- the 82% of failures the machine does not localise become localised, by observation rather than inference;
- the missing word is often an operand that provenance already records;
- the repair is once again an **identification** problem, which is the only kind this project has ever solved exactly.

Predict the failure honestly: this can plausibly move the ceiling from 2.7% to somewhere in the tens of percent, not to 100%, because a wrong value can be produced by a correct expression from wrong operands — provenance does not tell you which link in the chain is wrong, only the chain. That is the next measurement, and it should be run before the next mechanism is built.

## What is real in the original claim, and what is not

- **Real, and revolutionary:** instant learning solves every capability whose observable the world produces. That is the operator layer, and it is exact, permanent, parameter-free.
- **Not real:** that it extends to edits. The claim needs an observation that identifies an edit; five rounds have now shown the machine does not produce one today, and this round shows the *check* cannot substitute for it.
- **The creature:** still not needed. A creature is what a loop looks like when the world, the refusal, and the provenance are all in place. Two of those three exist here; the third — value provenance — is a tracing call, not a mind.

## Limits

- Presence in the check or the refusal is necessary, not sufficient; the measurement errs toward optimism, which is the right direction for a ceiling.
- The refusing function is the innermost function containing the traceback line; a fix that legitimately lands in its caller counts as not local.
- 12 tasks could not be executed here and are recorded, never scored.
- The 2.7% ceiling is a ceiling for *this* mechanism, not for parameter-free repair in general; the next mechanism is named above precisely because this one is spent.
- No independent verification.
