# Learning-to-learn: measured at the scale I said I would, and it fails

**2026-11-03**, `f05cba7`+. This is the experiment `THE_DEEPEST_LAYER_20261103_V1.md` ranked #1,
run at the size it demanded — **10 held-out kinds, not 4** — with a **stopping rule written
before the run**.

## The pre-registered rule

> The features have already been changed twice after seeing a negative result. This is the LAST
> change decided that way. Whatever the run reports, the next step is a decision, not another
> tuning pass.

I am holding to it. This document is the decision, and no further feature tuning happens.

## Result at 10 held-out kinds

| | |
|---|---|
| held-out kinds | **10** (never trained on) |
| learned choice solved | **5 / 10** |
| beat the default policy | **1 / 10** |
| beat the mean of 5 random draws | **3 / 10** |
| **verdict** | **NO_COMPOUNDING** |

Against a coin flip it wins 3 of 10. Against always picking the boring baseline it wins **one**.
That is the honest number and it is not close.

## Why it fails — measured, not guessed

The mechanism's map from "what this problem looks like" to "which search to use" is wrong, and
the failure is structural rather than a lack of data.

**One bucket, seven kinds, opposite policies.** Feature bucket `b1_m2_r1_d0_g0` contains seven
kinds. Within it:

- `adjacent_sort`, `sliding_pairs`, `tri_lock`, `letter_shift`: depth-first is **1095×** better
- `dial_lock`, `stack_pushout`, `ring_rotate`: depth-first is *worse* or **cannot solve them at all**
- `double_dial`: both work, and the choice is irrelevant

The ledger averages over that bucket and picks depth-first, so on a genuinely new occupant of the
bucket it is right about half the time — which is exactly 3/10 against the coin flip.

**And the deep reason: the feature vector cannot see the goal.** `dial_lock` and `adjacent_sort`
are indistinguishable to it — same branching, same reachable-state growth, same distance reading.
But one is solved by turning each dial (depth-first is fine) and the other is a permutation puzzle
where depth-first dives into a cycle and never returns. The distinction that decides the policy
lives in **how the goal constrains the state**, and every feature I can compute without solving
the problem throws that away.

## Three bugs in my own instrument, found by calibrating it

Worth recording, because each of them would have produced a confident false result:

1. **`stack_pushout` was unsolvable by construction.** Push grew the list, pop removed one — and
   its starts and target differed by exactly two, so the target length was unreachable. Every
   policy scored it "unsolvable" and the benchmark reported that as a fact about the terrain.
2. **`letter_shift` and `double_dial` raised on every action** — a parse bug (`"0_up"[1]` is
   `"_"`). They were counted as "no policy can do this" rather than "my environment is broken".
3. **The "1.2× prize" and then the "948,766× prize"** were both artifacts of a `10**6` penalty
   constant applied to unsolvable kinds. When five of ten kinds are unsolvable for every policy,
   any total dominated by that constant is arithmetic about the constant, not about learning.

None of these changed the verdict — the verdict was negative before and after. They changed how
much I could *trust the reason*, and the reason is the part that generalises.

## What this rules in, and what it does not

**Ruled out:** choosing among five hand-written search policies via a coarse, kind-blind feature
view does not transfer to unseen kinds. Not "needs more data" — needs a different object.

**Not ruled out**, and now the only interesting question left:

- **A richer state/goal representation.** The missing information is goal structure. A candidate
  that can see *how* the goal constrains the state — a partial ordering, a conserved quantity, a
  metric — is a different bet from a bucket of scalar summaries, and this run says nothing about it.
- **Composing policies rather than choosing one.** Every failure above is "one policy for the
  whole search"; a search that interleaves breadth and depth is not in the vocabulary at all.
- **Most likely, and least flattering:** on problems this small, the right move is *not* learning
  to choose a strategy. It is a decent heuristic search, and the compounding question does not
  arise until the problem class is big enough that no fixed strategy covers it.

## What is still true from earlier

The per-kind transfer result stands and was re-verified today after the goal-identity fix:
**8/15 one-trial, 0/15 worse, 6.33× trial speedup.** That is real, and it is a skill cache.

`truth.achieved` stays `false`. No capability registered. Two of three attempts at compounding are
now **measured negatives**, and the third has a mechanism that does not work. That is the honest
state of the thing this repository is actually for.

---

## 12. Note on the session that produced this (recorded because it changes what the artifacts prove)

The sandbox was rebuilt between two turns. The local clone reset to the base commit and `pytest`
and the whole substrate were gone. **The pushed branch was intact** (`f05cba7`); the recovery was
`git fetch` + `reset --hard origin/arena/e55485af-brain`, and the working tree's uncommitted files
survived the rebuild.

One consequence is worth stating plainly: the **code** that produced the ten-kind result was lost
in the reset while the **result document** survived. So the numbers in
`LEARN_TO_LEARN_BENCHMARK_20261103_V2.json` were re-derived after re-applying the code, and the
re-run reproduces them **exactly**:

```
test kinds=10  learned solved=5
beat default=1/10   beat random mean=3/10
NO_COMPOUNDING
```

That is a lucky recovery, not a methodology: a result whose producing code can vanish is a result
one step from being unreproducible. The tests in
`canonical/tests/test_compounding_and_goal_identity_v1.py` (7 of them) now re-run the benchmark in
CI, so this number cannot drift away from the code again.

## 13. What V1 versus V2 shows about experiment size

| | 4 held-out kinds (V1) | **10 held-out kinds (V2)** |
|---|---|---|
| learned solved | 4/4 | **5/10** |
| beat default | 1/4 | **1/10** |
| beat random mean | 4/4 | **3/10** |

At four kinds the mechanism looked like *"beats random 4/4, just needs a better default"*. At ten
it looks like **"does not beat a coin flip"**. The larger experiment did not produce a new finding
so much as dissolve a favourable one — which is the whole reason the stopping rule exists.
