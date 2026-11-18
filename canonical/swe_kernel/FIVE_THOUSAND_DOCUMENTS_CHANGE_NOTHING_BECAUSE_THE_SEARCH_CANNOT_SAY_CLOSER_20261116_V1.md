# Five thousand documents change nothing, because the search cannot say "closer"

Round 19 measured the last cheap hypothesis standing between us and a new mechanism: that the wall was never
*reachability* but **seed supply**. Every engine so far was fed the five or six literal arguments recoverable from
the one test file a fix touches — for `tomli`, strings like `"v"` and `"."`. A parser cannot be entered through five
characters. Meanwhile the repositories ship their own inputs: 5,949 of them across the audited fixes.

The hypothesis was worth measuring, because the field says seeds dominate. OSS-Fuzz's guidance is "start with
existing test inputs: unit test inputs, integration test data, or real-world examples — verify coverage — keep it
minimal", and its 1.12-million-session study found developer-provided seed corpora retain long-term effectiveness.
FuzzWise (December 2025) measures a better initial corpus finding eight errors where a random one finds one at equal
coverage. If that were our wall, the fix was an afternoon of harvesting.

It was not our wall. This round harvests the repositories' own documents, distils them by measured coverage, and
hands them to both existing engines **unchanged**. The number does not move, and one part is lost.

## What was measured

Eight parts across the audited fixes are accepted by the suite without being pinned (the same 8 rounds 17 and 18
spent their mechanisms on). Two engines, unchanged: round 17's mutation search and round 18's operand channel.
Only the seed set differs.

| seed set | seeds per part | executions | parts pinned | gained |
| --- | --- | --- | --- | --- |
| the tests' own literals (rounds 17–18) | 5–6 | 120 | **2** | — |
| the repository's own documents, same budget | 46 | 120 | 1 | 0 |
| the repository's own documents, budget scaled to the seeds | 46 | 600 | **1** | **0** |

5949 documents harvested, 82 kept by coverage-greedy distillation, 777 lines of the parsers entered — 2.6× the
lines the literal seeds ever touched. Zero parts gained. One part **lost**: `tomli 31c85a18`'s first part is pinned
by 6 seeds and *not* pinned by 46 seeds at five times the budget.

That last number is the finding. Adding seeds made the search **worse**, because the engines retain candidates by
line novelty across a budget that must be shared by every seed. A corpus five times richer spreads the same clock
five times thinner, and the ladder one seed was climbing is never climbed.

Two defects in this round's own instrument had to be fixed before the zero was believed, and both had produced a
plausible false report first:

- the candidate ranking was `prefer − length`, which put one-line test fragments ahead of the project's real
  documents and cut the documents off at the cap. The kept samples were `"v=['"` and `"a={"`. Reversing it to
  *validity first* raised coverage from 545 to 777 lines and still changed no verdict.
- distillation replaced the literal seeds. Coverage-greedy selection drops the small seed that reaches one error
  branch, so the corpus must be a **union** with the proven seeds, never a replacement. With replacement, the
  pinned count fell from 2 to 1.

The fire proof is built so that only the seed can explain a win, and it works: a guard in `parse` that can only be
reached by passing a check in a *different* function, whose token exists verbatim in the repository's data file and
nowhere else. Mutation from the test's literal cannot spell it; the artifact's own document does, and the part pins.
The honesty proof is the mirror: a token that appears nowhere in the repository is not invented — the corpus is
reported as having entered the file (coverage > 0) and still not reached the part.

## Why the zero is a bound and not a bug

The four rounds now form a closed table, and it is not a table of four failures. It is a table of what an
input-space mechanism can buy:

| round | mechanism | new channel | parts pinned of 8 |
| --- | --- | --- | --- |
| 16 | the tests themselves as the probe | which behaviours the suite separates | 0 |
| 17 | mutation of the tests' literal arguments | input shape | 2 |
| 18 | the program's own executed comparisons | the value a condition wants | 0 more |
| 19 | the repository's own 5,949 documents | input validity | 0 more, one lost |

Per part, the binding constraint is now nameable, and only one of the four is about inputs at all:

- `itsdangerous 7f4dcf83` — **no call exists**. The test contains no literal call to search from: the changed part
  is a `staticmethod(...)` assignment the suite never exercises. Seed supply cannot fix an absent call site.
- `packaging d5fedc90` — **the wanted value is constructed, not substituted**. The changed line is
  `state.keys() >= set(self.__slots__)`: the program hands us the set of slot names, and passing the gate requires
  *manufacturing a mapping keyed by them*. Round 18 can read the operand and re-deliver the seed at a different
  type; it cannot build `{slot: value}` from a set the program just showed it.
- `tomli 67ec7d10` — **the target is a chain of guards**. The three changed branches sit behind a sequence of
  earlier conditions; each is inverted by a different edit to a *malformed* document at a specific offset. One
  substitution per gate, with no record of which gate is next, is a walk without a gradient.
- `tomli 31c85a18` — **dilution**. The win exists at 6 seeds and evaporates at 46.

## The single bottleneck

Not seeds. Not reachability machinery. Not the format organ round 18's essay nominated.

**There is no per-gate objective. The search cannot say "this candidate is one gate closer", so it cannot prefer a
candidate, cannot keep a ladder, and cannot survive a larger corpus.**

That single absence explains every number in the table. Mutation stays alive by line novelty, which is a proxy for
nothing: a candidate that reaches line 700 by an uninformative path is ranked equal to one that has satisfied five
of the six guards standing in front of the target. The operand channel reads the wanted value at *one* comparison
and substitutes it, but a parser refuses in *sequence* — the value at gate 3 is a function of having passed gates 1
and 2. And a corpus helps only if the schedule can tell good seeds from bad, which is exactly what does not exist.

So the next mechanism is not another source of inputs. It is an **objective over gates**: for every candidate, the
identity of the last guard that rejected it and the straight-line distance from that guard to the target, with a
retained ladder **per gate** rather than per line. Then a bigger corpus stops being a dilution and becomes a set of
starting rungs — which is the only way the 5,949 documents this round harvested can ever pay for themselves.

## What is real and what is not

Real: a demonstration of a fixed bug yields, permanently and with zero model calls, the reachable behaviours of the
test's own call sites — two of the eight open parts here, and 275 of 600 sites measured in an earlier round. Real:
the program tells us the value it wants at an executed comparison; that channel fires and pins when the gate is
single. Real: the repositories contain thousands of documents that enter code the literal seeds never touch.

Not real: that this constitutes learning to use a computer. It is not sentience and it is not instant learning; it is
a search with a coverage-shaped retention rule and no notion of the target. Not real: that more input fixes it —
five thousand documents just measured zero, and the honest reading of that zero is that our search has no gradient,
not that our corpus was too small.

The single bottleneck, stated in one line: **the search has no measure of distance to the part it is trying to
reach, so every mechanism we add is a better map of a place we cannot walk toward.**
