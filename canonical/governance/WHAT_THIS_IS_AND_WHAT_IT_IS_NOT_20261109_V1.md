# What this is, and what it is not

Twenty-two rounds of measurement, one page. Every claim below carries the number that
produced it. Nothing here is an estimate.

## What is real

| capability | status | the number |
|---|---|---|
| one demonstration installs one CLI operation | works | 23/33 verbs reproducible (r41) |
| the operation is permanent | works | survives restart, replayed every round since r42 |
| it runs in a new directory on a new file | works | verified r44, re-verified r51 |
| it refuses when nothing was taught | works | returns None/ASK, never guesses (r46, r55) |
| it refuses to compile a self-tested skill | works | `FAIL_CLOSED__HELDOUT_IDENTICAL_TO_TRAINING_INSTANCE` |
| it refuses two steps recorded as a pipeline | works | `FAIL_CLOSED__MULTI_STEP_CLI_EXEC_IS_NOT_A_PIPELINE` (r54) |
| every answer carries a replayable source | works | 23/23 audited (r48) |
| the answer type follows the goal | works | 28/30 on blind held-out phrasings (r47) |
| the carrier cannot be shell-injected | works | argv exec, no shell=True (r53) |

## What is not real

| claim | measured |
|---|---|
| "it composes what it learned" | two learned verbs in one sentence -> None (r51) |
| "it finds the object itself" | "the largest .log file" -> None (r51) |
| "it understands a paraphrase" | 4/8; and 7/8 asks tie for a *perfect* word selector (r50, r55) |
| "it learns more by being taught more" | 4 near-duplicate skills break selection; adding them is destructive (r52) |
| "it does anything on a computer" | no display, no browser, no pointer, no GUI toolkit in this runtime (r51) |
| "it solves coding" | no model. 0 trained parameters. It cannot read a codebase |
| "it is on a path to sentience" | no evidence, no mechanism, no test that could settle it |

## The one sentence

**Permanence is real and is the only mechanism here at full strength. Selection, discovery,
composition and computer use are either absent or have a measured ceiling, and the ceiling is
usually set by the input rather than by the code.**

## Why the record is long

Because the interesting failures were all silent. A two-step skill answered 0 where the truth
was 3 and reported `pass: true` (r54). Four near-duplicate skills made an operation unreachable
(r52). A spaced filename bound nothing (r53). Each of those passed every check that existed at
the time it was found. The record is the only artefact here that improves when something is
wrong.
