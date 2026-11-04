# Round 28: the instrument was lying, and the abstraction was a bin

Round 27 ended by challenging itself: *does the experience path carry anything worth having?* I
closed with a floor and a promise to measure it. This round is that measurement, and the honest
summary is that **most of what round 27 claimed does not survive it.**

Two results were fabricated by my own instruments. One abstraction was worse than a constant. And one
thing turned out to be real, and it is not the thing I was building.

## Defect 1: the self-model was reading the answer off the label

Round 27 reported:

> self-model observations 0 → 27, and it discriminates: solvable shapes **0.403**, hopeless **0.122**.

The features I passed to `predictor.update` were:

```python
"features" = { ..., "solved": bool(result["ok"]), "status": str(result["status"]) }
```

**Those are the outcome.** I trained the model on the label and then asked it to predict the label.
Of course it separated solvable from hopeless — I had handed it the answer and called the result
self-knowledge.

This is the worst error in this tree so far, and specifically worse than the fossil it replaced. The
fossil was a self-model that never observed anything. This was a self-model that appeared to work,
complete with a measured-looking discrimination number, and the appearance was entirely leakage. It
would have survived review, because I was the one who would have reviewed it.

Re-measured with **pre-decision features only** — arity, evidence count, distinct outputs,
container-ness, candidate count — over 26 tasks:

| | measured |
|---|---|
| online solvability accuracy | **0.308** |
| majority-class baseline | **0.615** |

**Worse than always answering "solvable."** So the fix is not a better model. The fix is that a
self-model which cannot beat the trivial answer must not be allowed to govern anything, and the code
now says so instead of consulting it because it exists. `candidate_count` was added as a legitimate
pre-decision feature: the grammar search is free and spends no oracle question, so it is genuinely
available before the creature commits to asking.

## Defect 2: the shape key is worse than a constant

Round 27's central abstraction was a ledger keyed by problem *shape*. Leave-one-out over 26 tasks:

| predictor | cost MAE |
|---|---|
| by shape | **9.74** |
| grand mean (no shape at all) | **9.24** |

| predictor | solvability accuracy |
|---|---|
| by shape | **0.545** |
| majority baseline | **0.615** |

**13 of 26 tasks collapsed into one bucket spanning 1 to 54 oracle questions.** A key that predicts
worse than a constant is not an abstraction, it is a bin.

I tried the obvious repair — add the `growth` regime switch to the key — and it changed **nothing**:
7 shapes before, 7 after, MAE unchanged. Because the cause is structural, not a missing field:

> **Cost is driven by the PERIOD of the structure, and the period is not knowable before asking for
> it.** No refinement of pre-decision features can recover it. That is not a bug to fix; it is the
> reason the abstraction cannot work as designed.

The lesson generalises past this module: I built an inductive bias (shape) for a target (cost) whose
determinants are not observable in the input. That is not a tuning error, it is a modelling error, and
no amount of extra features repairs it.

## What turned out to be real

One mechanism survived, and it is not the one I built.

Cold, inducing a period costs **19** questions at k=4, **34** at k=7, **54** at k=11, **64** at k=13 —
and at k=13 a 24-question budget makes it fail outright.

Warm — after the same shape has been induced a few times — the same task is answered in **3–4**
questions, and the answer is a **composed operator**, not a memorised table:

| k | cold | warm | held-out wrong (warm) |
|---|---|---|---|
| 4 | 19 q | **4 q** | 0/48 |
| 7 | 34 q | **3 q** | 0/48 |
| 11 | 54 q | **3 q** | 0/48 |

That is the first time in this tree that a solved problem made a later, *different* problem cheaper
**without making it wrong**. It is also a distinction worth naming, because round 27 conflated them:

| mechanism | what it does | does it get cheaper? |
|---|---|---|
| raise the budget | lets the creature buy its way to k=13 | **no** — it pays every time |
| learn a transferable form | the next induction is already expressible | **yes** |

Both are legitimate. Only the second is the difference between static and alive. The budget mechanism
I built last round is the first. The gain I measured this round came from the creature reusing a
*form* it had built — which is what the organs do, not what my ledger does.

**So the honest attribution is: the ledger's budget sizing is real but tactical; the transferable form
is real and is the thing worth having; and my two headline claims from last round were both wrong.**

## Measured

- Self-model: leakage removed, honest accuracy **0.308** vs **0.615** baseline — and now explicitly
  not permitted to govern.
- Shape key: **MAE 9.74 vs 9.24**, accuracy **0.545 vs 0.615** — worse than a constant, stated as such
  in the source and pinned by `TheShapeKeyMustEarnItsKeep`.
- Transfer: cold **19/34/54** → warm **4/3/3**, **0/48 wrong** at every period.
- Budget sizing: intact after the leakage fix — 24 cold → 38 → 53, never narrowing.
- **298 passed, 20 subtests**, the same three failures that are byte-identical on the stashed baseline.

`truth.achieved: false` · `authority: NONE` · $0 · no sentience claim · no external models · no
neural weights.

## What I got wrong about method

Three rounds running, the defect was in my **instrument**, not my reasoner: a vacuous test, an
uncallable API, backwards degrees of freedom, an uninstrumented code path, an efficiency metric that
rewarded not checking, and now an outcome used as a feature. Each presented as a finding.

The pattern that catches them is single and cheap, and I did not apply it until this round:
**before claiming a mechanism works, measure it against the trivial alternative.** A self-model must
beat "always solvable." A shape key must beat the grand mean. An efficiency metric must not improve
when verification is removed. Every one of those checks takes minutes and every one of them would
have caught the error before it reached a round note.
