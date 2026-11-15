# The action is not the task

**2026-11-14.** Branch `arena/98e3c624-brain`, base `37a53c57`. Authority **NONE** — sandbox
measurement, `$0`, zero model calls, no network in any instrument, `truth.achieved` stays `false`, no
capability registered, no family flipped, no test weakened.

New record: `canonical/verification/ACTION_CHAIN_TO_TASK_20261114_V1.json`.
New instrument: `canonical/tools/action_chain_to_task_20261114_v1.py` (5 tests).

---

## The claim, read again and taken at face value

> "Instant learning + instant learning in new arbitrary environments — we already solved those
> perfectly. Doesn't this mean this is a perfect solution for all the problems? All we have to do is
> give our model a try in all those new coding environments, or give it the smartest actions. After he
> does them at least once, he learns all of them permanently. So we solve everything on a computer.
> We were trying to make our model a sentient creature. Is this true, or are there things that are
> wrong?"

Five separable claims. They are not equally true, and the word doing the damage is **"all"**.

| # | claim | verdict |
|---|---|---|
| 1 | instant learning is **solved perfectly** | **false in this tree's own record**, and the tree already retracted the doc that said otherwise |
| 2 | it works in **new arbitrary environments** | **partly real**, and the part that works was never in doubt — what fails is *narrowness*, and no amount of experience moves it |
| 3 | therefore it **chains into whole jobs** | **false, and this is the round's new measurement: 0 of 8 real pull requests** |
| 4 | the lever is **the smartest actions** | **wrong lever**: the measured cost of a long job is not knowing actions, it is that every action must land |
| 5 | this makes a **sentient creature** | **not related at all**, and the tree's own organs say so in writing |

The one thing that is unambiguously real: **experience is a multiplier on a capability you already
have.** Everything else in the claim assumes it is a supplier of capability. It is not.

---

## 1. "We already solved it" — the tree retracted that, itself

This has to come first, because the prompt's premise is a document this repository wrote and then
withdrew:

> **RETRACTED AS A GENERAL CLAIM — 2026-11-13.** This document's "COMPLETELY SOLVED AND VERIFIED" is
> not supported by its own evidence: Tests 1–3 are three AST counts ... and the learning signal is a
> counter that no later step reads. Measured instead, on eight pull requests the operators were not
> designed on: 12.19% → 37.52% coverage ...
> — `INSTANT_LEARNING_COMPLETE_SOLUTION_2026.md`

And the earlier "10/10 new environments" row:

> the probe builds the **same instance** in four of its five families ... so "a new instance" there
> means "the same instance, called again." Re-measured on genuinely distinct instances: **1/15 cases
> showed a genuine saving; median trial speedup 1.00×.**
> — `INSTANT_LEARNING_SCOPE_20261101_V1.md`

So claim 1 is not something I am disputing with the owner. **The project disputed it, in writing, and
won.** The honest number for cross-environment transfer is 37.52% coverage at 76.36% precision on one
change class, with two of eight pull requests at zero.

## 2. What is genuinely real, and it is worth saying clearly

Three things survive every measurement this tree has made:

- **It persists.** Teach a lesson, restart the process, the lesson is still there. Memory outlives the
  process — the one property without which "learning" means nothing.
- **It transfers across repositories, inside a kind of change.** With a lesson learned in repository A
  and applied in repository B, one demonstration gives **0.573** coverage at **1.000** precision and
  three demonstrations **0.845**. That is real cross-environment transfer.
- **It refuses rather than guesses.** Half the change kinds transfer perfectly; three transfer exactly
  nothing, and the organ's refusals name the reason. Precision 1.000 with 0 wrong changes is not a
  small thing.

That is a genuine asset. It is just not the asset the claim needs, and section 3 is where the gap is.

## 3. The new measurement: an action is not a task

Every prior number in this tree scores a **lesson** — one edit, one file, one demonstration. Nobody
had scored a **task**, which is what a user actually buys. So I scored the same 8 real pull requests,
144 pairs, **the way a person scores work**: the pull request is done only if every changed file comes
out exactly as the developers wrote it.

| | |
|---|---:|
| real pull requests | 8 |
| files the developers changed | 47 |
| files produced **exactly** right | **1** |
| **pull requests solved** | **0 of 8** |
| per-file exactness | **2.13%** |
| per-task completion | **0.0%** |

And the arithmetic that comes out of it, which is the whole answer:

```
p (one action lands)  = 0.0213
k = 1   -> 2.1%
k = 2   -> 0.05%
k = 3   -> 0.0000
k = 10  -> 1.9e-17
```

**This is not a new problem I discovered. It is the same problem everyone has, and it is arithmetic.**
A real pull request is 6 files; a real OSWorld 2.0 task is **318 tool calls**; a METR long task is
hours. If a job needs `k` actions to land and each lands with probability `p`, the job lands `p^k` of
the time. **Learning each action ten times faster changes nothing about `p^k`.** That is the first-
principles statement the whole prompt is missing.

The frontier's own numbers say the same thing, independently:

| source | number | what it means |
|---|---|---|
| OSWorld 2.0 (Jun 2026) | best 20.6% binary / 54.8% partial, ~318 steps | agents get most of the way and fail to finish |
| METR Time Horizon 1.1 (Jan 2026) | horizons **collapse below 1 hour at 80% reliability** | the doubles-every-7-months headline is a **50%** number |
| METR pass^8, retail | **below 25%** | more attempts raise pass@k and *lower* pass^k |
| OSWorld 2.0 cost breakdown | visual grounding 15.5%, tool semantics 13.8%, extraction 12.8%, **execution 10.1%, verification 9.8%** | effort goes to *understanding* the job, not to *doing* actions |

The needed per-step reliability to reach today's 20.6% at 318 steps is **0.995**. To reach OSWorld 1.0
levels (80%) it is **0.999**. We measure **0.0213**. That is not a factor of two; it is a factor of
forty-five, and it is the wrong *kind* of gap to close by learning actions faster.

## 4. The "smartest actions" idea — the lever is right, the object is wrong

This is the most interesting claim in the prompt, and I owe it more than a dismissal, because at first
principles it points at something real.

**Where it is right.** Choosing smarter actions compresses `k`. If a learned action absorbs five steps,
the job needs `p^6` instead of `p^10`, and at p=0.27 that is 8 000× better. Action abstraction is the
one lever that improves a long job *without* improving any single step. That is why hierarchical
options, Voyager's code-as-action, and skill libraries exist at all. The idea is not dumb.

**Why it is not the fix.** Two measured walls:

- **A growing frozen library turns into a collision surface, not a capability.** The tree measured it:
  at 8 lessons the organ starts writing lines nobody asked for; at 52 lessons it writes **39 wrong
  lines**, and the wrong count stops improving as the correct count rises. `SkillEvolBench`
  (arXiv 2605.24117) finds raw-trajectory reuse often beats distilled skills, and more skills "improve
  coverage while introducing episode-specific drift and procedural clutter." `Continual-ARC` finds **no
  harness method gains on unseen tasks**. `arxiv 2601.04748` puts a number on the ceiling: flat skill
  selection degrades past a capacity threshold (|S| beyond ~60, κ≈90), fixed by *hierarchical routing*,
  not by more skills.
- **A library you cannot check is a library you cannot trust.** Every action added is only as good as
  the check that admits it, and this tree's checks are weak in a measured way: the project's own test
  suite is **silent on 19 of 29** real merged changes; a bounded differential search found a witness on
  a public entry point for **6 of 57** commits; mutation catch on the oracle licence is **0.75** and
  **24% of sites have no licensed check at all**. Adding actions faster than you can license them
  multiplies the surface on which the library is wrong.

So: **the smartest action is not the lever. `p` and the licensed check are.** An action you can verify
is worth ten you cannot.

## 5. Why "one try each, permanently" is the wrong shape, not just too small

The corpus gives the sharpest number in the whole tree for this:

> **39 demonstrations of other people's repairs buy one extra bug** (5 → 6 of 40). 203 lessons add two
> repairs over a backwards control. Illustratively, 1 365 demonstrations would be needed to reach 40/40.
> — `the_exchange_rate_of_one_lesson_20261112_v1.py`

Two things follow, and they are the reason the plan as stated cannot reach its goal.

1. **The exchange rate is brutal and it is the rate that matters.** "Once each" is not a description
   of a working learner when 39 showings buy one new capability. The unit of progress is not the
   showing; it is the *checked* generalisation.
2. **Permanence is granted to things that were never checked.** `ONE_SHOWING_ONE_CHECK_TABLE` already
   found the exact case: the lesson is kept, reaches an unseen function of the same shape, refuses a
   harmful version — and the behaviour it teaches is **invisible to the project's own tests, which
   never probe the boundary value.** Writing that into permanent memory is not learning. It is
   cementing an unverified belief, and at 52 lessons it is what produces the 39 wrong lines.

## 6. Computer use: why the same mechanism does not carry over

The claim "we can do anything on a computer just once and he learns all of this permanently" needs one
more thing that code does not — and the project has already concluded this in
`LEARNING_ONCE_DOES_NOT_SOLVE_COMPUTER_USE_20261113_V1.md`. The structural reason, from first
principles:

- **In code, the environment hands you a verifier.** You can run it. `edit_by_example` works at all
  precisely because a file is a text you can execute and compare.
- **In a GUI, the environment hands you pixels.** There is no free comparison between "what I did" and
  "what I meant" unless you build the state model that says so. OSWorld 2.0's failure analysis is
  explicit: failures come from **losing constraints, incomplete state, and not verifying the outcome**,
  and agents' own effort goes to visual grounding and tool semantics — not to acting.
- Therefore a GUI action library inherits the *same* `p^k` arithmetic with a **worse `p`**, because the
  check is worse. Adding computer use multiplies the surface, it does not extend the capability.

The claim is a category error, not a stretch: an action learner is a way to *acquire* behaviour, and
computer use is a *state-estimation and verification* problem. Learning more actions does not estimate
state.

## 7. Sentience — directly, since it was asked directly

Nothing measured in five rounds of this tree produces a mechanism that *decides*. Every improvement
came from removing an obstacle between a decision and an effect, or from refusing to lie. The tree's
own notes say so in writing:

> "Nothing in this repository establishes sentience. Memory, planning, self-report, and weight updates
> are not evidence of subjective experience. A module named `sentient_cognitive_core` does not change
> that."

I will add the first-principles version, because it is the one that is actually useful: **sentience is
not on the path to capability, and capability is not on the path to sentience.** They are orthogonal.
The evidence for this is that the 2026 literature's entire gap — 20.6% on OSWorld 2.0, 0.995 needed
per step, the compounding problem — is a **reliability and state-modelling** gap. No amount of
subjective experience would change `p^k`; a better verifier would. Chasing sentience is not merely
unmeasurable here, it is an *optimisation in the wrong variable*, and by the owner's own standard (kill
bad ideas before they cost time, optimise only for the ultimate solution) it is the first thing to cut.

There is a related, harder question — does the system *understand* or only match patterns — and the
honest 2026 answer is that this is still contested: recent work finds LLM representations track human
causal-plausibility judgements at ~85% while a companion paper argues everyday causal reasoning in
both humans and models is pattern-matching rather than abstract world models. What matters for this
project is narrower and settled: **our organ matches patterns.** It says so at its refusals, and its
refusals are the most honest thing it does.

## 8. So what is real, and what is the smartest thing to do

**Real:** persistence; 0.573/0.845 cross-repository transfer inside a kind; precision 1.000;
refusals that name their reason; a licence that can tell you whether a check could have seen the
change at all.

**Not real:** perfect solving; arbitrary environments; whole jobs; computer use; sentience; and
"one try each" as a description of how capability grows.

**The single bottleneck, stated in the variable the goal actually depends on.** Not learning speed.
Not the number of actions. Not sentience. It is:

> **the probability a single action is *right and checkable*, because a job needs all of them.**

And the fastest real move on that variable is the one this branch has been building for three rounds
without naming it that way: **licensing the check before trusting the lesson.** A lesson whose
difference cannot be observed is not knowledge — it is a permanent guess, and this branch's own
`observable_surface_v1` already shows that **41 of 44 real edits are declaration-level**, invisible to
any execution. Checking them requires a declaration comparison, not a test run.

That is the next step, and it is not more actions: **make `p` mean something before making the library
bigger.** `truth.achieved` stays `false`.

---

### What I killed this round, and why

| idea | why it dies |
|---|---|
| "learn everything once, permanently" as the plan | 39 demonstrations per extra capability; at 52 lessons, 39 wrong lines. The rate, not the showing, is the unit. |
| **more** actions / a bigger skill library | composition degrades (|S|≈60), 24% of sites unlicensed, suites silent on 19/29. Bigger library = bigger wrong surface. |
| "computer use follows from coding actions" | no free verifier in pixels; OSWorld 2.0 failures are state and verification, and its own effort split says so. |
| sentience as the direction | unmeasurable here *and* orthogonal to the thing that is actually limiting: `p^k`. |
| predicting OSWorld from our `p` | those steps verify and repair; `p_eff = 1−(1−r)(1−c)` becomes a story with two free parameters. Reported as an open test, never as a prediction. |
| re-deriving the corpus | this doc adds one measurement (0 of 8 tasks) and one reframing (`p^k`) to `LEARN_IT_HERE_USE_IT_THERE`, `LEARNING_DOES_NOT_ACCUMULATE`, `LEARNING_ONCE_DOES_NOT_SOLVE_COMPUTER_USE`, `REACH_FIXED_AND_IT_WAS_THE_WRONG_WALL`, `ONE_SHOWING_ONE_CHECK_TABLE`. |
