# The check the loop throws away — and the number that was wrong

**2026-11-25 · no benchmark run · zero model calls · zero dollars**

## What I set out to build

Last round I ended on this: the loss on SWE-bench splits in two, and the cheap half is that a
candidate makes the target test pass and breaks a neighbour — a break visible in a local re-run of
the tests the edit touches, a check that "costs seconds and was never taken", costing 16 tasks.
Round 15 was to build that loop and measure it.

## What I found before writing a line of it

**The loop already exists, and it already takes that check.**

The harness that produced the 2026-11-13 receipt does not run a candidate on the whole test
modules until it has passed every test that the task says must start passing. That gate is in the
code, one line: `if row["start_passing"] < len(first): return row`. It fires *before* the expensive
run, every time, for free.

I recomputed the whole story from that receipt's own rows:

| | count |
|---|---|
| candidates that passed at least one of the task's new tests | **258** |
| …that reached the whole-module run | **13** |
| …that resolved the task | **10** |
| **…that passed *all* the new tests and were stopped anyway** | **0** |
| …that passed *some* new tests and were stopped | 245, across 16 tasks |

Those 245 are not a loss. A candidate that fails one test the task says must start passing cannot
resolve the task. Stopping it saves a run and gives up nothing.

So **my own number from last round was wrong by a factor of five.** I had read "16 tasks never
reached the whole-module run" off "16 tasks have a candidate that passes some new test". The
breakage cost — candidates that pass the new tests and break an old one — is **3 tasks out of
128**, and the receipt has named all three all along.

I retracted that in the receipt and locked it with a test that fails if any candidate that earned
the whole-module run was ever withheld. It is not a correction in prose.

## What I measured instead

If neither selection (+2 tasks) nor the neighbour check (3 tasks) is the loss, then the loss is
that the generator has nothing to propose: 102 of 231 tasks got no candidate at all. I pulled the
benchmark's own statements, the Django trees at each task's base commit, and the merged pull
requests behind all 231 tasks, and asked where a candidate's *content* comes from.

**The generator's only content channel is the code lines in the issue text.** 93 of 93 no-candidate
tasks write no code line in their issue. Not one task with no code line got a candidate; not one
task with a code line failed to. That is a channel that is empty, not a search that is weak.

**Is the missing content anywhere at hand?** Measured against the fix itself:

- the **issue text** names every new name the fix needs for 6 of 102 tasks (18% of atoms overall);
- the **file** being changed already holds everything needed for 6 of 102;
- the **whole project** at the base commit holds it for **17 of 26** sampled changed files.

The material is in the project. What is missing is *which arrangement of it*.

**Two oracles that cost nothing, both measured and both rejected:**

- The issue's own reproduction (`>>>` lines): present in **19 of 231** issues, **3 of the 102**
  stuck ones. Too few to carry a round.
- A trace of the failing test: I ran each task's own tests under a line tracer. The file being
  changed is **never executed at all** for 13 of 26 tasks, and the changed line itself is in the
  trace for **1 of 26**. The reason is structural: a missing feature is absent code, and absent
  code cannot execute.

## The bottleneck, restated honestly

Not coverage of the store — the project holds the material. Not selection among candidates — that
is worth +2. It is that **the machine has no signal that prefers one arrangement of already-held
material over another** without running the hidden tests. Every zero-model signal I tested fails
on exactly that.

The next round should try to find a public signal that ranks arrangements — the failing test's own
output, the conventions of the neighbouring code, the shape census already in the tree — and if
none exists, say so plainly and pay for a test run per candidate, which these tests make
affordable at under a second each.

## What this round is

A withdrawal and a redirect, not a capability gain. No task was resolved here; nothing was run
against the benchmark. What changed is that a false number is gone, replaced by a measured one,
and the next round's question is different because of it.

- Receipt: `canonical/verification/THE_CHECK_THE_LOOP_THROWS_AWAY_20261125_V1.json`
- Tests: `canonical/tests/test_the_check_the_loop_throws_away_v1.py` (14 tests)
- Intent: `canonical/action_intents/THE_CHECK_THE_LOOP_THROWS_AWAY_20261125_V1.json`

Authority NONE — a measurement, not a verification receipt.
