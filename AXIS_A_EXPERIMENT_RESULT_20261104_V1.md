# Axis A: the experiment ran, and the falsifier fired

**2026-11-04.** Pre-committed protocol from `FIRST_PRINCIPLES_THREE_20261104_V1.md` §3, executed
against the creature's own episodes. The falsifier I wrote down before seeing any result was:

> *if held-out skill does not improve over the fixed-10 baseline, the axis is not the limit and I
> report that instead of shipping the mechanism.*

It did not improve. Nothing is shipped. What follows is the result, including the two instrument
errors that nearly made it look otherwise.

Authority **NONE**. Spend $0. `truth.achieved` false.

---

## 1. The gate that nearly killed the experiment: the data barely exists

Before building anything I measured how much experience the creature can produce. Collecting every
settled episode from its own board:

| sessions run | episodes collected |
|---|---|
| 6 | 40 |
| 20 | **40** |

Not a typo. Twenty sessions of twelve cycles produced exactly the same 40 episodes as six, because
**life is spent**: by the fifth or sixth session the creature has no remaining life and attempts
nothing. Every session after that is a no-op that re-reports a cumulative `closed` count.

So the entire learnable dataset of this creature's lived experience is **n ≈ 40**, over 32 distinct
tasks, with several base features perfectly collinear on it
(`host_ready == grounding_complete == not missing_dep_or_env_block` for every single episode). That is
the information-theoretic ceiling on any learning claim here, and any experiment that reports a
skill difference below ~0.1 on n=40 is measuring noise.

## 2. The result

Baseline: logistic model on the fixed 10 features, leave-one-out. Treatment: the same model plus a
grammar of candidate primitives (pairwise conjunction and difference over the 7 features that vary),
with primitives **selected inside each fold** so no fold sees its own outcome.

| arm | out-of-sample Brier | skill |
|---|---|---|
| fixed-10 baseline | 0.1793 | **+0.2661** |
| grammar, candidates = conjunctions + differences | 0.1754 | +0.2822 |
| grammar, candidates = **conjunctions only** | — | +0.2395 |
| grammar, candidates = **differences only** | — | +0.2822 |
| random pool, 20 arbitrary candidates per fold | — | +0.248 … +0.258 |

**The +0.016 is an artifact.** Read the selected primitives: across all 40 folds the treatment chose
`diff(family_empirical_pass_centered, family_observation_confidence)` and a second difference — **0 of
80 selections were conjunctions.** A difference is a *linear* combination the baseline model can
already express, so it adds no hypothesis-space capability at all; it only regularises. The arm that
actually required new expressive power — conjunctions — scored **+0.2395, i.e. 0.027 *below* the
baseline**. "Both" and "diff only" are identical strings of numbers, which is the tell.

## 3. And the +0.016 is not even outside noise

Paired per-fold differences on the primitive actually selected:

| quantity | value |
|---|---|
| delta skill | **+0.0033** |
| mean per-fold squared-error change | −0.00082 (sd 0.049) |
| folds improved | 27 / 40 |
| **95% bootstrap CI** | **[−2.23, +2.70]** |

The interval spans more than four skill units and contains zero. A 27/40 split is a coin. There is no
there there.

## 4. Two instrument errors, recorded because they are the point

This is the seventh and eighth self-inflicted measurement defect in this line of work, and both
would have produced a confident wrong answer:

1. **The "treatment" that added a constant column.** My first paired comparison difference-tested
   `X[i][1] - X[i][2]` — `host_ready` minus `grounding_complete`. On this data those are *identical
   for every row*, so the added feature was the constant 0. The script reported delta skill
   `+0.0000`, sd `0.0000`, and a bootstrap CI of `[+0.0000, +0.0000]`. A perfectly tight, perfectly
   meaningless interval. It read as "no effect, high confidence" and the truth was "no feature".
2. **The selection metric did not match the reported metric.** Primitives were chosen by *training-fold
   Brier*, then the arm was scored by *out-of-sample* Brier. Selection on training fit and reporting
   on held-out fit is the standard way to manufacture a difference that does not exist, and it is
   exactly what produced the +0.016 before I looked at *what* it had selected.

Both are the same underlying failure as every earlier one in this session: **I trusted a number before
checking what produced it.** The only reason this document says "no effect" instead of "small win" is
that the second error was caught by asking which primitives won.

## 5. What this does and does not establish

**Established:** adding a grammar of primitives to this predictor does not improve held-out prediction
on the data this creature can generate. Axis A — "it cannot invent new concepts" — is **not** the
binding constraint. Fixing it would have produced a mechanism, a test file, a commit and no learning.

**Not established:** that expressive power never matters. The experiment is *starved*, not decisive:
n=40 with 7 varying features, several collinear, and 2 selections per fold against 42 candidates is
approximately guaranteed to overfit whatever it picks. On a thousand episodes of a task distribution
with real feature variation, the answer could reverse. The honest statement is that **this system
cannot generate the evidence needed to answer the question**, which is a finding about the system and
not about grammar-based feature invention.

## 6. The consequence, which is the useful part

Every learning axis in this tree — A, B, C, and the fitted self-model of axis D — is now blocked by
one thing that is not a modelling problem at all:

> **The creature produces ~40 episodes in its entire life, and then it is dead.**

Twelve cycles per session against a 40-unit life grant; the predictor's own `MIN_SETTLED` is 20. The
system was given a mind with a vocabulary of ten and an experience budget of forty, and the last three
turns were spent arguing about which organ to sharpen.

That reframes the next step entirely, and it is not a repair. Before any axis can be tested, the
creature has to be able to live long enough to produce the evidence — either by a larger life grant,
or by making a cycle cost less than it earns. Until then every result in this line of work, including
the honest ones, is being measured at the edge of where measurement is possible.

## 7. Non-claims

Single creature, single host, one board composition; 40 episodes is the population, not a sample of a
larger one. The baseline logistic model is mine, not the tree's `EpistemicSelfBeliefEngine`, so these
skill numbers are not comparable to the earlier −0.084/+0.246 figures, which came from the tree's own
scorer on its own ledger. The CI is a percentile bootstrap over 40 paired folds and should be read as
"indistinguishable from zero", not as a precise interval. Nothing here is independent verification,
and no change was made to the repository to obtain it — this document is the entire deliverable.
