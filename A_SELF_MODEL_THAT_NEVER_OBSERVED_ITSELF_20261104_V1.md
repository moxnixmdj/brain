# Round 27: a self-model that never observed itself

You asked, for the third time, whether this is the smartest approach, and to think from the deepest
layer. The third repetition is data. It means my *shape* of answer was wrong, not merely incomplete:
I had spent three rounds making the creature's **claims** more honest, which is a defensive property.
Honesty is not intelligence. A creature that refuses everything is perfectly honest and completely
useless.

So this round I stopped asking "is this claim true?" and asked the question underneath it:

> **does using this creature make it better at anything?**

For a static program the answer is no, and always no — every run is the first run. That is what the
word means. So the answer is measurable, and on this tree it was **no**.

## What I measured, and it is worse than a missing feature

**1. Use buys nothing.** Three tasks sharing one period-3 table were solved. A fourth task using the
same table then paid the full cold price. `WARM == COLD`, exactly. The organs are a cabinet of
finished answers, not a body of knowledge.

**2. The tree is 79% orphaned.** Of 2160 modules under `canonical/runtime`, **1711 are never imported
by anything.** I want to be careful about this one: it is round 22's finding restated, and restating a
finding is not progress. It matters here only as scale.

**3. The self-model was a fossil.** This is the find. `MetaCircularOrganGraph` constructs a
`CausalFeatureSelfPredictor`, **persists its weights**, publishes `predictor_observations` in
`summary()`, and called `self.predictor.update(...)` **zero times**. After three of its own attempts:

    predictor_observations:  0
    predict_pass_probability: 0.5   (forever, for every problem)

It reported a number that looked like learning and was a constant. And `predict_cost` was called in
exactly one place: inside the class that defined it. A thermometer wired to nothing.

**This is the purest instance of the thing you have been objecting to.** Not a hardcoded constant in
a decision path — a *simulacrum* of self-knowledge, complete with persistence and a reporting field,
that had never observed anything. It would pass any test that asked "is there a self-model?" Yes.
There is one. It is decorative.

## Why the obvious fix is the wrong fix

The obvious move is to make experience *refuse*: "I failed at this shape before, don't try." I
measured that before building it, and it is a trap:

> Inducing a period from three seeds costs **19** questions at k=4, **34** at k=7, **54** at k=11 —
> and all three are the **same shape**. The hardcoded `growth_evidence_budget = 24` is too generous
> for k=4 and permanently too small for k=11, where it does not merely fail: it spends 24 questions
> and then issues a *budget verdict* about a problem whose real cost was 54.

A memory that trims the budget after the k=4 failure **ratchets the creature downward** and never
attempts k=11 — and every individual decision along the way still looks prudent. That failure mode is
invisible from inside, which is what makes it dangerous.

So experience governs effort **one-directionally**: it may only ever give a shape *more* room than a
cold creature would have had. The floor is the old constant. Measured result:

| | budget |
|---|---|
| cold start | 24 |
| after one induction | 38 |
| after two | 53 |
| after three | 71 |

It cannot shrink. `test_experience_can_never_shrink_the_budget` exists specifically to keep it that
way.

## A metric I got wrong, and caught by measuring it

My first counterfactual defined a question as *avoidable* if the answer left the survivor set
unchanged. It reported **12 of 25** questions avoidable — a 48% efficiency win, exactly what I was
looking for.

It was wrong. All 12 were Door-3 refutation probes: questions asked of a claim that had already
survived everything, to see whether it would break. **A probe that agrees is not a wasted question —
it is a failed attempt at refutation, and that attempt is what makes a sole-survivor claim credible.**
Suppressing them would have removed the verification and left the claim standing on nothing, while
reporting an efficiency gain.

The instrument was also **incomplete the first time**: `floor(x/7)` showed "2 questions, 0 avoidable"
because both were spent inside Door 3, which the counterfactual did not instrument. I only found the
12 because I fixed the instrument and re-ran.

Both errors are recorded in the source rather than quietly corrected, because the failure mode —
*an efficiency metric that rewards not checking* — will be back.

## What actually changed

`canonical/runtime/experience_v1.py` (new): a ledger keyed by **problem shape**, where the shape is
computed from *only* what is known before any question is asked — arity, given-evidence count,
distinct-output count, whether any argument is a container. That restriction is the honesty of the
whole module: if the shape used the outcome, "prediction" would be retrospection.

Wired into the organ graph:

- every outcome recorded, on **every** exit path, via a wrapper rather than per-exit instrumentation —
  the method has more than a dozen returns and the next one added would be the one that is missed;
- the counterfactual is **observed**, not assumed: survivors are compared before and after each answer;
- the self-model is now **trained by the creature's own attempts** — 0 → 27 observations over a
  battery, and it discriminates: a shape it keeps solving is rated **0.403**, one it keeps failing
  **0.122**, with predicted cost 1.32 vs 1.00;
- experience **sizes** the growth investment, and can only widen it.

## Measured

- Self-model observations: **0 → 3** after three tasks (was 0 forever).
- Discrimination: solvable shape **0.403** vs hopeless **0.122**.
- Growth budget: **24 → 38 → 53 → 71**, monotone non-decreasing, cold start unchanged at 24.
- `k=4/7/11` still `INDUCED_OPERATOR_CRYSTALLIZED` at **19/34/54** questions — unchanged, correctly.
- **19 new tests pass**; **271 passed, 20 subtests**, three failures which are **byte-identical on the
  stashed baseline** (verified by stashing and re-running, not assumed).

`truth.achieved: false` · `authority: NONE` · $0 · no sentience claim · no external models · no
neural weights.

## What is still static, stated plainly

The ledger keys on a coarse shape and consults counts. It is not a world model, it does not
re-represent anything, and 79% of the tree remains unreachable from the reasoning core. What it does
now have is the one property whose absence made everything else decorative: **a path by which using
it changes it.** That is a floor, not a ceiling, and the next round should be judged by whether that
path carries anything worth having.
