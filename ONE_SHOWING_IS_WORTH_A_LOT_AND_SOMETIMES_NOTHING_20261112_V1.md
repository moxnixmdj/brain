# One showing is worth 4.7× a replay — and a quarter of the time it is worth exactly nothing

**2026-11-12.** Branch `arena/2b093755-brain`. Authority **NONE** — producer-run measurement, `$0`,
zero model calls, `truth.achieved` stays `false`, no capability registered, no family flipped. The
organ measured (`edit_by_example_v1.py`) is not edited by this round.

The owner's framing, this time, is already the right one:

> **Problem 1: exact recall — SOLVED.**  **Problem 2: generalisation — NOT SOLVED. Focus on solving
> problem 2 perfectly with the smartest solutions in the fastest way.**

That split is correct, and it is the most useful thing said in this whole exchange. But the label on
problem 1 needs one correction, and it changes what "solve problem 2" can mean.

---

## 1. What "solved" is worth, measured

Problem 1 is not solved perfectly; it is solved at a measurable exchange rate, and this tree has
measured it four times in four regimes:

| regime | replay exact | reuse without the exact match | what the gap is called |
|---|---:|---:|---|
| MiniWoB++, 50 pages, fresh seeds 1080–1089 (`#6770`) | 15.2% | **68.8%** | the version space |
| MiniWoB++ full, seeds 1060–1079 | 14.0% | **65.5%** | the version space |
| repeated change in real code, one example | — | **15.8%** at 95.5% precision | the operator algebra |
| SWE teach→reuse bridge (`#6769`, reproduced) | — | admitted a skill, reused it once | the check that admits it |

**Replay is the worst arm available, in every regime.** A stored exact solution loses to a
demonstration that was generalised once, by 4.7× on GUI tasks. So problem 1 is not the asset the
plan treats it as — the asset is already problem 2's mechanism, running at partial strength.

## 2. The correction this round makes to the generalisation story

Three documents on `main` report one-demonstration transfer at **95.5% precision**. All three are
right, and all three answer the wrong question for a deployer.

> 95.5% is precision **per asking** — over 440 askings, most of them refusals. It answers *"when the
> organ edits, is the edit right?"*
>
> The decision a deployer makes is different: *"I am about to change this codebase having seen one
> example — is the demonstration I was given worth acting on?"* That is precision **per chosen
> demonstration**, and it is **87.0%** (80 right, 12 wrong).

Twelve wrong changes out of 92 is not a rounding error. It is 13% of every change the mechanism
proposes, and no prior document in this tree states it, because every prior instrument pooled the
refusals into the denominator.

The full curve, over all 89 candidate demonstrations, is the part that was missing:

| reach (siblings the lesson fits) | demonstrations | changes made | right | **wrong** | precision | of the people's changes recovered |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 28 | 0 | 0 | 0 | — | 0% |
| 1 | 13 | 28 | 24 | 2 | 85.7% | 11.0% |
| 2 | 8 | 130 | 122 | 2 | 93.8% | 45.4% |
| 3 | 8 | 24 | 24 | **0** | **100%** | 27.9% |
| 4 | 5 | 53 | 43 | **10** | 81.1% | 63.2% |
| 5 | 5 | 55 | 55 | **0** | **100%** | **94.8%** |

**Reach is not monotone in precision.** Ten of the twelve wrong changes sit in the reach-4 stratum,
*above* the exact stratum at reach 3. Any rule of the form "more reach is always safer" is false, and
the honest operating point is not "maximise reach" — it is "maximise reach, then price the risk".

At maximal reach one demonstration recovers **94.8%** of what the people did, with **zero** wrong
changes. That is the strongest single result this tree has for one-shot transfer, and it holds on
2 tasks of 15.

## 3. Declining is free, and that is the whole of what it is

The organ may refuse to be taught. What does declining buy?

| decline unless the best demonstration reaches ≥ | tasks acted on | tasks declined | right | **wrong** | precision |
|---:|---:|---:|---:|---:|---:|
| 0 | 15 | 0 | 80 | 12 | 87.0% |
| **1** | **11** | **4** | **80** | **12** | **87.0%** |
| 2 | 8 | 7 | 76 | 10 | 88.4% |
| 5 | 2 | 13 | 19 | **0** | **100%** |

Declining four tasks costs **zero** correct changes — those tasks were never going to recover
anything, so refusing them is pure loss-avoidance on wasted work and buys **nothing** in precision.
**The twelve wrong changes survive every threshold until you decline thirteen of fifteen tasks.**

That is the honest shape of "solve problem 2 perfectly": the mechanism produces a small, mostly
correct, sometimes wrong change, and *the information needed to tell which is which is not in the
demonstration*. Reach ranks candidates well (r=0.88) and calibrates risk badly.

## 4. A class of change the metric cannot see

215 of the 1,889 changes the people made are **import-line changes (11.4%)**. The organ refuses
import-only demonstrations by construction — its own sentence is *"the two example files hold the
same code, apart from import lines that were added or removed"* — and the recorded metric reports
coverage against the 1,674 that remain. A repeated change made in imports alone is therefore a kind
of change this mechanism can **never** learn, and no document in the tree names the size of that
hole. It is the second-largest single refusal class after `NO_FORM_IN_FILE`.

## 5. Why "give it the smartest actions once" cannot be made to work as stated

Three independent literatures, all from 2026, converge on the same shape this measurement found:

* **Induction level decides whether a skill helps at all.** Skills induced from whole trajectories
  *lower* success below the no-memory baseline on every benchmark (by 1.2 points as text, 4.1 as
  code); the same prompt applied to single subtasks raises it. The level, not the count, is the
  variable. ([2608.20274](https://arxiv.org/html/2608.20274v1))
* **One-shot extraction is not enough, and the fix is a closed loop, not more examples.**
  "Closed-loop optimization outperforms one-shot induction … one-shot skill extraction, even when
  the underlying induction agent is capable, cannot ensure the generated skills are faithful."
  ([MIND-Skill, 2605.08670](https://arxiv.org/html/2605.08670v1))
* **Model-generated skills show non-trivial negative transfer**, and a skill's utility is
  independent of model scale and baseline strength — so "give it to a better model" is not a fix.
  ([Microsoft Research, 2026](https://www.microsoft.com/en-us/research/publication/from-raw-experience-to-skill-consumption-a-systematic-study-of-model-generated-agent-skills/))

The mechanism behind all three is the one measured in §2. A demonstration does not specify a
change; it *selects among changes the system can already express*. Where the selector is
ambiguous, some selections are wrong — 13% here — and no amount of "the smartest action" removes the
ambiguity, because the ambiguity is in what the example failed to show.

**So the answer to "can't we do this now?" is: you can, and it works about 87% of the time per
decision, recovers a fraction of the work, and silently emits one wrong change in eight. That is a
useful tool and it is not an agent that learns a skill permanently.**

## 6. Where the smartest next step actually is, measured

Not more demonstrations (the second buys +8 points and then flattens). Not a better tie-break (four
were tested; none beat path order). The ordered list, by measured value per unit of work:

1. **The check is the missing organ, not the learner.** Every figure above assumes *no* check ran.
   The record's own ceiling arm — "every try kept, as if a check had settled it" — recovers **390**
   changes against the strict arm's **265**, at the same 96.8% precision. Running a project's own
   tests converts agreement-with-people into correctness and roughly halves the loss. It costs
   minutes per candidate. Nothing else on this list is close.
2. **Import-line operators** — 215 changes, 11.4% of the corpus, structurally unreachable today.
3. **`NO_FORM_IN_FILE` is not an operator gap.** 162 of 440 askings (36.8%) refuse because the
   demonstrated change simply does not occur in the target file. These are *correct* refusals and
   must not be counted as failures in any progress metric, or the metric will chase them forever.
4. **Subtask-level decomposition** (§5, first paper): the one lever with an external controlled
   result showing it flips a net-harmful skill library into a net-helpful one.

## 7. Reproduce

```
python3 canonical/tools/repeated_change_one_example_measure_v1.py \
    --collect /tmp/pulls_v2.json \
    --as-recorded-in canonical/verification/REPEATED_CHANGE_ONE_EXAMPLE_20261112_V1.json   # 54 s, 89 files, every hash checked

python3 canonical/tools/when_one_showing_should_be_trusted_20261112_v1.py \
    --pulls /tmp/pulls_v2.json \
    --out canonical/verification/WHEN_ONE_SHOWING_SHOULD_BE_TRUSTED_20261112_V1.json      # 68 s
```

`canonical/tests/test_when_one_showing_should_be_trusted_v1.py` — **16 passed**. Two runs produced
byte-identical `headline`, `precision_by_reach`, `abstention_policies` and
`pre_registered_prediction`.

## 8. What this round got wrong

1. **The abstention claim was first written as `cost >= 0`, comparing a precision (0.8696) against a
   count (19).** The condition was trivially true and the claim "held" without measuring anything.
   This is the fifth recorded instance of the same defect in this tree: *a check that reports
   success without exercising its subject.* Restated as an equality of two counts and pinned by
   `test_the_abstention_claim_compares_like_with_like`.
2. **The import-line share was first read from an aggregate row that does not carry the field**, and
   raised `KeyError` rather than reporting a number. Now summed from the per-pull-request rows and
   pinned by `test_the_import_share_is_summed_from_the_finer_grain`.
3. **I predicted monotonicity and was wrong.** Nothing in the reach distribution suggested it; I
   assumed it because the curve looked well-behaved at the top. The docstring's prediction section
   now states the non-monotonicity as the claim, so a later run cannot quietly drop it.
4. **The 0.86 → 0.67 "drop" is not a regression.** The recorded round scored capture against the
   spread of candidate *shares*; this round scores it against the ceiling on absolute changes
   recoverable. Both are reported, labelled, and pinned so neither can be quoted as the other.

---

## 9. The held-out test: the curve did not transfer, and that is the answer

Everything in §2 was measured on the fifteen pull requests the effect was noticed on. That is a
description, not a prediction. So a second corpus was collected, disjoint from the first **by kind of
change**: six queries that share no word with the discovery run's eight, on kinds the organ had never
been run on — a dataclass replacing an init, a timeout added to a request, an environment read moved
to a settings object, a bare except made specific, a deprecation warning added, percent-to-format.

Nine pull requests, 53 files. (23 GitHub calls were refused by a secondary rate limit and passed
over; they are counted in the record so the corpus is not silently a smaller one.) The prediction was
written in the collector's docstring before the search ran.

| | discovery corpus | **held-out corpus** |
|---|---:|---:|
| tasks | 15 | 9 |
| kinds of change | 8 | **6, none seen before** |
| candidate demonstrations | 89 | 53 |
| demonstrations the organ **cannot learn** | 24.7% | **73.6%** |
| changes the organ made | 290 | **5** |
| changes that were right | 268 | **0** |
| changes that were **not what the people did** | 14 | **5** |
| precision when it edits | 92.4% | **0.0%** |

**On kinds of change it has never seen, every change the organ made was wrong, and it refused
three-quarters of the demonstrations outright.**

The reason is visible at the level of one file. For `a16bitsysop/freeagentPY#18` the demonstrated
change was an import line gaining a name; the people's change in `bank.py` was to stop inheriting
from a base class and call a serializer function instead. The organ did not attempt that. It added
the imported name to a file that needed something else entirely:

```
what the people did        -from .base import FreeAgentBase      +from .utils import serialize_for_api
                           -class BankAPI(FreeAgentBase):        +class BankAPI:
what the organ did         -from .base import FreeAgentBase
                           +from .base import DEFAULT_API_BASE_URL, FreeAgentBase
```

That is not noise. It is the mechanism, working exactly as designed and giving the wrong answer:
**reach is a syntactic question — "does the demonstrated form occur here?" — and it was read as a
semantic one.** On the discovery corpus the two coincide, because every task there repeats *one*
change and a file where that form occurs usually needed that change. On a corpus of unfamiliar
kinds, a file can contain the form and need something else entirely.

### What this settles

* **P1 held, on new kinds, in the strongest possible direction.** Chosen-demonstration precision is
  0.0% against the pooled 95.5%. The correction in §2 was not an artefact of one corpus.
* **P2 failed.** The discovery curve is not monotone; the held-out curve has three strata all at
  zero, so there is no fall to detect. A claim that could not be tested on the second corpus is a
  claim about the first corpus, and it is now recorded as failed rather than quietly dropped.
* **The generalisation problem, stated exactly.** One demonstration plus reach solves a *kind of
  change* that the system already knows how to express, in a codebase where that kind recurs. It does
  not solve "give it the most advanced actions once". On an unfamiliar kind the organ has no
  operator, so it either refuses (73.6%) or reuses an operator that fits syntactically and means
  something else (5 changes, 0 right).

This is the same law the 2026 literature reports from the other direction: skills induced from whole
trajectories *lower* performance below no-memory on every benchmark because the induced artefact is
tied to its source task, and the fix is a closed verification loop rather than a better
demonstration. ([2608.20274](https://arxiv.org/html/2608.20274v1),
[2605.08670](https://arxiv.org/html/2605.08670v1),
[Microsoft Research 2026](https://www.microsoft.com/en-us/research/publication/from-raw-experience-to-skill-consumption-a-systematic-study-of-model-generated-agent-skills/))

### What this means for "solve problem 2 perfectly"

The measured ordering of the next steps changes, and the first item is now unambiguous:

1. **A semantic check per edit, not a better demonstration.** Reach cannot distinguish "this file
   contains the form" from "this file needed this change", and no rearrangement of candidates fixes a
   predicate that is asking the wrong question. The organ's own ceiling arm — every try kept, as if a
   check had settled it — recovers 390 of the people's changes against the strict arm's 265 at the
   same 96.8% precision on the discovery corpus. A test run converts the 0/5 above into refusals,
   which is strictly better than wrong edits.
2. **Per-kind calibration or per-kind operators.** The held-out result says a single learned operator
   does not span kinds. The tree already knows this shape: one reducer for a word problem cost "one
   lesson, two files, about ten lines" and then answered 5 of 5 held-out instances. The price of a
   new kind is code, and on this corpus the price is 6 kinds.
3. **Do not count `NO_FORM_IN_FILE` as failure.** It is the organ correctly declining, and it is
   36.8% of askings on the discovery corpus and the dominant refusal on the held-out one.

**Reproduce the held-out half:**

```
python3 canonical/tools/hold_out_the_precision_curve_20261112_v1.py --collect /tmp/pulls_holdout.json   # 950 s, resumable
python3 canonical/tools/when_one_showing_should_be_trusted_20261112_v1.py --pulls /tmp/pulls_holdout.json \
    --out canonical/verification/ONE_SHOWING_HELD_OUT_20261112_V1.json
```

`canonical/tests/test_when_one_showing_should_be_trusted_v1.py` now runs **21 tests**, five of them
pinning the held-out result — including one that asserts the failed prediction stays failed.
