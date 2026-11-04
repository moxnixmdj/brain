# First principles, pass twenty-two — the creature was carrying a false belief about itself

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

## 1. I stopped asking what it cannot do, and asked what it believes about itself

Twenty-one passes asked "what capability is missing". This pass asked a different question: **what does
this system believe about its own competence, and has anything ever been allowed to correct it?**

The answer was the most damning thing I have found in the repository.

`failure_kind_v1` contains `_FAMILY_FOR`, a hand-written table stating which repair producer should run
first for each kind of failure. Two facts:

1. **`family_order()` is called from nowhere.** The prior had never been exercised in its life.
2. **Measured, it is wrong in 3 of 4 cases.**

| failure kind | the prior says run first | what actually wins |
|---|---|---|
| VALUE | `operator_family` | `interpretive` |
| BINDING | `stun_guard` | nothing produced anything |
| SIGNATURE | `guided` | `guided` produced 6, won 0 |
| SYNTAX | `guided` | `syntax_repair` produced the only clean candidate |

Four earlier commit messages described the failure-kind channel as load-bearing scheduling. It was dead
code carrying a false belief, and nothing in the system could ever have noticed.

**This is the deepest form of the static problem.** Not a missing mechanism — a self-description that
was authored, never tested, and never contradicted.

## 2. What replaced it

`tool_competence_v1`: counts of consulted / produced / won per (kind of failure, tool), persisted across
processes, ranking producers by what they have actually done rather than by what I assumed.

Measured after six separate processes on VALUE failures:

| tool | produced | won |
|---|---|---|
| interpretive | 6 / 6 | **6 / 6** |
| operator_family | 6 / 6 | 0 |
| synth_grammar | 6 / 6 | 0 |
| guided | 6 / 6 | 0 |
| habits, binding, signature, syntax | 0 | 0 |

And it can say **`has_signal: False`**. On SIGNATURE the table read `guided produced 6, won 0` and
`signature produced 6, won 0` — no tool ever won, so the ranking is an arbitrary tie. A competence model
that cannot say "I have no evidence" is just a table with better manners, and I would have presented
that tie as a learned preference.

## 3. The negative result, which is the actual finding

**None of it makes the creature better at anything.**

| configuration | batches | candidates screened |
|---|---|---|
| cold (no competence store) | `[1, 1, 1, 9, 1, 1]` | 14 |
| warm (earned order, interpretive first) | `[1, 1, 1, 9, 1, 1]` | 14 |
| warm + skipping never-productive tools | `[1, 1, 1, 9, 1, 1]` | 14 |

Identical. The reason is structural: the screen takes the whole batch and stops on the first pass, and
the tools being skipped were producing zero candidates anyway. So:

> **A ranking is not a decision, and even the decision this system could make was worth nothing, because
> it was never the tool that was costing the work.**

The competence model changes which questions get asked. It changes no answer, no cost, and no capability.

## 4. What that says about the whole line of work

Two things I did not want to write down:

**First**, the win rates above are not a story about nine clever tools. `interpretive` won 6 of 6 and
every other producer won 0 while producing 6. If that holds outside my constructed worlds, then the
other eight producers are near-dead weight, and the "nine producers" architecture I have been
extending for twenty-two passes is one good idea plus eight things that mostly emit noise for the
screen to reject.

**Second**, and worse: the competence model was the right thing to build and it changed nothing. That is
evidence that the bottleneck is not scheduling, not prior knowledge, and not self-knowledge. It is that
the system's *ability to produce the right candidate* is what limits it, and I have now measured that
every other layer I could add — ordering, skipping, priors, competence — is bookkeeping around that one
fact.

## 5. What I would do next, and why it is uncomfortable

**S25.** Not another organ. Measure the claim in §4 directly: run the board's twelve shapes and record,
per shape, which tool first produced a passing candidate and how many candidates were screened before
it. If the honest answer is "one tool does almost everything and the rest are overhead", then the
correct action is to *delete* rather than add — and every pass so far has added.

I have spent twenty-two passes making a system that accumulates knowledge, and the measurement this
pass says the accumulation is real but the capability underneath it has not moved. The creature can now
tell you what it is good at. It is not yet good at more than it was.

## 6. Standing bar

Different at the end than the start: yes, but not in the direction I claimed. What changed is that a
false self-belief was replaced by a measured one, and the measurement of that replacement came back
close to zero. A system that can hold an accurate belief about its own weakness is a precondition for
being smart, not evidence of it — and today that is all I have.
