# First principles, pass eight — the ceiling was a constant I chose

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

Question asked (eighth time): *is this the smartest approach?* Answered by auditing the last
seven passes rather than defending them. Short answer: **no**, and the audit says exactly why.

## 1. The system is static, measured

Census over 1,035 decision points (if/while/ternary tests in the four files that govern a repair):

| | count | share |
|---|---|---|
| read anything the creature learned from its own history | 28 | **2.7%** |
| numeric threshold with no history behind it | 101 | 9.8% |

And the single function that decides whether a repair happens,
`experiment_in_cow_sandbox`: **41 decision points, 0 reading history.**

So "static code" is not a metaphor here. The creature's behaviour is overwhelmingly a function of
numbers I typed, not of what it has experienced. That is the deepest answer to the owner's
question, and it is worse than anything the memory work was going to fix.

## 2. Every one of my seven passes optimised the wrong layer

Passes 1-7 asked *"why is this mechanism not reached?"* — a question that can always be
answered by adding a call site. S1 through S6 produced real but bounded findings (memory worth
1 shape of 9; a gate rejecting honest repairs; self-taught rules inert). Each was treated as the
topic. None asked: **which authored number is actually doing the work?**

## 3. Then I built the "smart" thing and it failed its own falsifier

`learned_producer_order_v1`: learn per-shape producer order from outcomes, hierarchical prior,
authored order as the empty-memory tie-break. Written, then measured against held-out shapes:

| | authored | global reorder | per-shape | oracle bound |
|---|---|---|---|---|
| candidates screened | 71 | 62 | 55 | — |
| **wall time** | **0.064 s** | 2.218 s | 2.140 s | 0.017 s |

33x slower. The authored order looks arbitrary but encodes something better than my score did:
**cheap-first**. My module optimised win-rate and paid for it in time. Deleted, not shipped, not
disabled — deleted. (The oracle row is the interesting one: 4x headroom exists, but it is
per-shape-cheapest-producer, not per-shape-most-likely.)

Repeated-shape test (the claim that actually matters): second encounter with the same defect
shape cost the same as the first. **Experience did not help.**

## 4. What the measurement actually found

An honest candidate takes a median of **4 ms** (min 4, max 215 across 15 runs).

The per-candidate wallclock budget was **2,000 ms** — 452x the median — and it is charged *per
candidate*, so a single candidate that never terminates costs the whole budget. On a while-loop
world, 2.07 s of a 2.43 s repair was one hung candidate.

A/B, seven worlds, three trials each:

| budget | repaired | total | worst single world |
|---|---|---|---|
| 2.0 s | 7/7 | 6.09 / 6.22 / 6.29 s | 2.20 - 2.46 s |
| **0.5 s** | **7/7** | **2.97 / 3.05 / 3.06 s** | **0.71 - 0.74 s** |

Same repairs. Half the wall time. Worst case cut to a third. 0.5 s is still 2.3x the slowest
honest candidate ever measured here.

It was also, all along, the reason a learner could never have found it: a candidate killed at the
deadline was reported with the same exit code as an honest test failure, so *"never terminates"*
and *"wrong answer"* were indistinguishable. Now reported as `WALLCLOCK_EXCEEDED`.

## 5. What this says about becoming non-static

A creature that cannot question its own cost model cannot become smart; it becomes fast or slow
by my hand. The three things that would actually change its nature, in order of leverage:

1. **Budgets that are measured, not authored.** The timeout result is the template: measure the
   distribution of honest cost, set the budget from it, re-measure. Every other hardcoded number
   (candidate caps 36/24/16/12/10/6, `max_rounds`, `total_timeout_s`) is a candidate for the same
   treatment, and each is worth more than the memory plumbing.
2. **One decision that reads history** — after (1), not before. Doing it first is what this pass
   did, and the falsifier said no.
3. **A search whose *shape* comes from experience** (the producer set, not its order). Untested;
   the order version failed, which is evidence the cheap version of this idea is wrong.

## 6. Corrections to my own instruments in this pass (5-7)

5. **`learned_producer_order_v1` scored win-rate only** and was 33x slower than what it replaced.
   Deleted. Its author (me) briefly reported "55 vs 71 candidates, learned wins".
6. **Two harnesses were broken before they were believed**: a `TemporaryDirectory` whose path was
   used after deletion (every screen ran against a dead directory, so *nothing* worked), and a
   repeat-test that never recorded, so its "learning helps" was noise.
7. **A test candidate removed the function under test**, so the import failed instantly and I read
   "no timeout" where a hang was expected. The marking code was right before my test was.

## 7. Standing bar

Different at the end of a run than at its start: **still not established.** Retention works,
self-crystallization works, and neither consumes anything. Memory is not what makes this creature
work, and this pass found that the thing that *does* dominate its behaviour is a set of numbers
nobody measured.
