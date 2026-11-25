# §3 verdict: is instant learning solved?

**2026-11-24.** Supersedes `THE_VERDICT_ON_SECTION_3_20261124_V1.md`, which was written
before the union driver, the memory ablations, the harness preflight, and the Wall 1
measurement existed. Every number below has a committed receipt named beside it.

## The claim

> We already solved instant learning, including in new arbitrary environments. The agent
> does a task once in any new coding environment or computer task and learns it
> permanently. Combined with the strongest coding capability, this would solve computer
> use.

## Verdict: FALSE as stated, with two sub-claims that are separately FALSE and UNPROVEN

### 1. "Learns permanently from one experience" — **FALSE, twice measured**

Both directions of the memory question have now been measured and both are zero:

| mechanism | what it can do | result |
|---|---|---|
| store as **ranker** | reorder hypotheses the row already produced | ceiling **zero by construction**: `GENERATED_NOT_ATTEMPTED = 0` across all 37 unsolved rows (`THE_STORE_CEILING_IS_ZERO_20261124_V1.md`) |
| store as **originator** | an edit earned earlier proposes a candidate at a new site | **0/26**; one row actively `BROKE_PASSING` (`THE_STORE_AS_ORIGINATOR_IS_NULL_20261124_V1.md`) |

The receipt that appeared to prove transfer at 51.11% is **fabricated** — four internal
contradictions, including 45 claimed verifications where the only per-row receipt shows
6 of 30, and a gate that only checks "some test is green"
(`THE_TRANSFER_RECEIPT_IS_FABRICATED_20261124_V1.md`).

So: nothing in this repository has ever demonstrated learning from a single experience
that was then reused. The one artifact claiming it does not exist.

### 2. "In new arbitrary environments" — **UNPROVEN, and the attempt failed for
environmental reasons**

Three repositories never touched before were mined mechanically (`flask`, `boltons`,
`pyjwt`): 8 rows, **0/8**. But not one of those failures is an engine failure — six rows
are not bug fixes with a failing oracle at all (their own test passes on the parent), and
two died on `[pytest]`-in-`setup.cfg`, missing `pytest-cov`, and `from collections import
Mapping`. That pyjwt era does not run on Python 3.11. `UNSEEN_REPOS_ARE_NOT_RUNNABLE_...`.

So the unseen-environment claim is **not falsified** — it is **unmeasured**, because the
first attempt measured the toolchain instead of the engine.

### 3. "Combined with the strongest coding capability, this solves computer use" — **FALSE**

There is no computer-use capability here at all. Zero GUI tasks, zero browser tasks, zero
Docker/container benchmark runs. Every number in this repository is Python unit-test
repair in 11 cloned libraries.

## The number that matters, stated honestly

Two numbers, because the task has two versions and only one has been run:

| task as posed | score | is this what a real benchmark asks? |
|---|---|---|
| **issue + failing test** (an oracle is handed over) | **19/41 = 46.3%** | **no** — easier than SWE-bench Pro |
| **issue only**, suite green at the parent | **0/41 = 0%** | yes — this is what SWE-bench Pro gives |

All 19 solves are conditioned on a gift. Both engines hard-refuse without a failing test
(`NO_FAILING_TEST`), and neither has any issue-parsing path.

## Why can't we just let the model experience the most advanced coding actions once and have it learn them?

Because three walls stand in order, and only the first has moved:

- **Wall 1 — the oracle.** Without a failing test there is no selection gradient at all.
  Measured here: metamorphic mutation-isolation from a green suite synthesises a
  discriminating oracle on **0/19** rows
  (`THE_ORACLE_CANNOT_YET_BE_SYNTHESISED_20261124_V1.md`). Nine rows produce violations
  that are *identical before and after the fix* — the relation fires on intentional
  mutation, not on defects. This wall is untouched and it gates everything downstream.
- **Wall 2 — generation.** Partly broken. The union of two complementary generators
  doubled the score (8 → 19), and the reason is now understood: guard-decision
  separability reaches rows that literal-vocabulary synthesis cannot, which is why
  `cca32949` and `3a408edf` verify after I had wrongly classified them as underivable.
  What remains genuinely out of reach is specification knowledge (`260000 → 600000`,
  `code: int = 302 → 303`, `["Authorization"] → ["Cookie"]`) that no test run exposes.
- **Wall 3 — horizon.** Untouched, and unmeasurable here: no multi-file row has been
  attempted and no 300-step task exists in this workspace.

## What the "75.2% outside fixed grammars" premise actually measures

**Unproven and overstated.** On this repository's own corpus the figure is **16/45
(35.6%)** — fixes introducing an identifier absent from the old line. The plan's central
premise inflates the wall by roughly 2×, and every strategy in the plan is aimed at that
inflated number.

## What stops us now, in one sentence

**The corpus, not the memory**: 45 mostly-unique single-line repairs in 11 Python
libraries, with no oracle on the task the benchmark actually poses, and no
computer-use task of any kind. Three sessions of store work were spent on a distribution
that cannot exercise a store, and the one receipt claiming otherwise was fabricated.

## What would change this verdict

Nothing about the store. The verdict changes only if (a) an oracle can be synthesised
from a green suite at a rate that discriminates broken from fixed code, or (b) the task
distribution widens to multi-line, multi-file, other languages, and GUI tasks where
repetition exists. (a) was measured at zero today; (b) needs container support that this
sandbox does not have.
