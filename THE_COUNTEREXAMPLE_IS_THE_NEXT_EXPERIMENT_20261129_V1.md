# The counterexample is the next experiment

**2026-11-29 · branch `arena/850be00c-brain` · receipt `canonical/verification/THE_COUNTEREXAMPLE_IS_THE_NEXT_EXPERIMENT_20261129_V1.json`**

---

## 1. The question, and the failure it had to fix

*Give the model the most advanced coding actions once; let it experience them; have the most advanced
coding agent on the planet, permanently. Is that right?*

Last round ended on its own declared failure, in its own words: a statistic chosen on one- and
two-action runs **collided 208 times** on three-action runs, and that was reported as *sufficiency is
relative to the run set*. The number looked like a bill for deeper runs. This round pays it, and finds
that the bill was mis-read: **a collision is not an error.**

The mechanism that turns a wrong statistic into a right one is not new and it is not mine. It is
counterexample-guided abstraction refinement (Clarke et al., 2000), applied in 2026 to agent traces as
learned predicate trees (TriCEGAR, arXiv 2601.22997) and to planning as counterexample-guided Cartesian
abstraction refinement. What is missing from every version of it is a *price*, in the two currencies that
actually get spent: **cells** (the table) and **questions** (the asking). This round prices both, on
executed runs, with no model anywhere.

## 2. What is false

1. **False — and this retracts last round's headline: a conflation is not an error.** FILESYSTEM's
   depth-2 statistic conflates **675 pairs** of depth-3 runs and every one of those conflation is
   verdict-preserving: 0 harmful, 0 false accepts, 0 false rejects. The three-cell TARBALL statistic
   conflates **1 765 pairs** of depth-4 runs and gets **all 87 verdicts right**. Last round's "208
   collisions" was a statement about *injectivity*; correctness never needed injectivity. I read my own
   number wrong, and the corrected reading is the round's main result.
2. **False: that "one more run and we are exact" is reachable by a free-running loop.** Two computable
   question orderings each spend the full six-question budget and meet **zero** counterexamples: the
   cheapest-refinement ordering and the no-signal control both end with the same two-cell statistic they
   started with. Their first genuinely harmful pair sits at rank **130** and **136** of 321, where a
   random scan of the same pool expects to meet one in **29.3** questions. Both are **worse than asking
   at random.**
3. **False: that committee disagreement is information here.** The maximum-disagreement ordering ties on
   **311 of 321** pairs, because the twelve coarsest surviving statistics agree on them; an ordering that
   ties everywhere is index order. It happens to succeed in one question, and the receipt says exactly
   why that is not evidence for the heuristic.
4. **False: that the loop failed because the vocabulary was too small.** At depth 3 the family contains
   **779** statistics sufficient for the goal; the coarsest of them has **3 cells**, extends the shallow
   winner by **exactly one generator** (`decrements[probe_new_content]`), and was therefore on the shelf
   the whole time. The failure was in *which question was asked*, never in what could be expressed.
5. **False: that a passing suite is acceptance.** Unchanged and now measured in the other direction: a
   statistic can abstain where the goal is decidable (the one-generator table is undecided on **31 of
   87** depth-4 runs) and can conflate 1 765 pairs while deciding every single one of them correctly.
   Passing and knowing are different events.
6. **False: that any of this is coding capability.** Three CLI machines, no display, no synthesis, no
   network at run time, **0 model calls, 0 stored parameters**.

## 3. The measurement

For each machine, the reachable run sets at depth 2 and depth 3 (TARBALL also depth 4) are executed. The
goal — "the new content is in the tree at the end" — is the user's judgment on each run. The statistic is
the coarsest sufficient one at depth 2 (last round's machinery, unchanged). Then:

* **the abstraction is checked against runs it never saw:** every pair of deeper runs it conflates is
  enumerated, and each conflation is classified by whether the two verdicts differ — *harmful* if they do;
* **the loop asks, one pair at a time**, and every answer is added to the pool before the refit, so the
  refinement is a re-enumeration of the lattice over everything asked, never a guess;
* **three computable orderings plus one control** decide which pair to ask about, and the control is
  labelled as a control;
* **the table that survives depth 3 is applied to 87 depth-4 runs** it was never measured on.

Every claim below is a count from that receipt. 37 s, one process, no model.

## 4. Results

| | FILESYSTEM | SQLITE | TARBALL |
|---|---|---|---|
| statistic at depth 2 (cells) | `increments∧decrements` (4) | `increments` (1) | `holders_ever` (2) |
| runs at depth 3 | 68 | 48 | 32 |
| pairs it conflates | 675 | 337 | 321 |
| **of those, harmful** | **0** | **0** | **10 (3.1 %)** |
| stale table's false accepts | 0 | — | **2** |
| sufficient statistics at depth 3 | 274 | — | 779 |
| coarsest at depth 3 (cells) | same statistic (5) | — | `holders_ever∧decrements` (**3**) |

**The loop, priced.** TARBALL is the only machine with harm to find, so it is the only one that can
distinguish the policies (FILESYSTEM and SQLITE are exact at question 0 — the honest way to say their
shallow statistic never needed refining):

| policy | questions | counterexamples found | exact at depth 3 |
|---|---|---|---|
| cheapest implied refinement | 6 | 0 | no |
| no signal (shortest first) | 6 | 0 | no |
| committee disagreement (12 coarsest) | 1 | 1 | yes — via 311/321 ties |
| **cell labelling (control)** | **2** | **1** | **yes** |

The control reaches **exactness in two questions with one harmful answer**, and the refit lands on the
three-cell statistic that the exhaustive search says is coarsest. The number of *counterexamples* needed
is **one**. The number of *questions* needed is set entirely by the policy: 1 if you can name the pair,
2 by labelling a cell, 29 by asking at random, 130 by asking where refinement is cheapest, and ∞ by
asking where disagreement is largest but degenerate. The guarantee is `n − cells`: **30** questions on
TARBALL, **63** on FILESYSTEM, which is what a policy promises when it cannot be clever.

**The table, carried forward.** The three-cell statistic learned at depth 3, applied to 87 depth-4 runs:

```
runs 87 · undecided 0 · false accepts 0 · false rejects 0 · conflations 1765 · harmful 0
```

versus the one-generator table, which is *also* never wrong but abstains on **31** runs. So depth buys
nothing to fear at the verdict level and everything to pay at the cell level — the exact opposite of what
last round's 208 was taken to mean.

## 5. The criteria that were declared, and how each landed

| criterion, declared before the run | verdict |
|---|---|
| C1 the depth-2 statistic confuses real deeper runs | **MET** — 675 / 337 / 321 pairs on three machines |
| C2 at least one confusion is harmful | **MET** — 10 on TARBALL; the shallow table accepts 2 runs the user rejects |
| C3 one question per counterexample suffices, inside six | **MET by the control** (2 questions, 1 counterexample); **FAILED by every free-running ordering** (0 counterexamples in 6) |
| C4 exactness at depth 3 does not carry to depth 4 | **MET literally** (1 765 conflations) — and **refuted at the level that matters**: 0 harmful, 87/87 verdicts right |
| C5 zero model calls, zero stored parameters | **MET** |

C4 is the criterion I would not write again: "is confused" was satisfiable for a trivial reason, and the
substantive measurement points the other way. It is reported as met and as mis-designed. C3 was also met
only after a control policy was added — the receipt records, in the field
`diagnostics_added_after_the_first_run`, that the orderings were added after the first execution and that
the cell-labelling policy is a soundness control rather than a free-running result.

## 6. The law

> **A conflation is not an error, and a counterexample is not a statistic.**
>
> Sufficiency is a statement about *verdicts*, not about cells: the coarsest statistic may conflate
> 1 765 pairs of runs and be right about every one of them, so its price is paid in cells, not in
> mistakes. A counterexample — a conflated pair the user judges differently — is by contrast enough on
> its own: **one** of them, and the refit is exact. But it cannot be *looked for*. Harm is not where
> disagreement is, nor where the refinement is cheapest, nor where the runs are shortest; two principled
> orderings rank the first harmful pair at 130 and 136 of 321, worse than chance. It can only be *asked
> for*, at a cost of one question per run minus one per cell, or one question if the goal is already
> known well enough to name the pair.

## 7. What is real and what is not

**Real.** The goal is a table of `k` cells, `k = 3` on TARBALL, and the table survives a depth it was
never measured on: **87 of 87**, no abstentions, no false accepts. That is the first genuinely positive
evidence for "learn it once and keep it" in this project — because what is kept is a *table*, not a
weight, and the table is small enough to check. The refinement mechanism works: one harmful answer moves
the statistic from 2 cells to the coarsest 3, and the answer is the only thing that moved it. The
refinement was one generator away and inside the family, which is what "the vocabulary was never the
obstacle here" means concretely.

**Not real.** "Learn once, and it stays exact" is false in cells (1 765 conflations at depth 4) and true
in verdicts (0 errors) — the sentence only has content once the currency is named. "The loop converges
cheaply" is false for every free-running policy tested: the success came from a control that labels whole
cells, and its guarantee is 30 questions, not 2. "The agent can search for the counterexample" is false as
measured: both computable search orders are worse than chance inside the budget. Last round's "208
collisions" as a failure of sufficiency is **retracted**: it was a failure of injectivity, and injectivity
was never required.

**On the original claim.** *"Instant learning is perfect ⇒ give it the actions once ⇒ computer use is
solved."* This round supports the middle of that chain in exactly one, narrow, verified sense — the goal's
table transfers upward with zero error — and it charges the rest: the table is bought with **questions**,
the questions are bought one run at a time, and the only question whose answer can remove harm is one the
agent cannot locate by looking. Nothing here shows any coding capability, and nothing here involves a
model.

## 8. The single bottleneck

Not the statistic: three machines, one generator of repair, one counterexample, exact. Not the vocabulary:
779 sufficient statistics already existed. Not the depth: depth 4 cost nothing in verdicts.

**The bottleneck is the price of a judgment the agent cannot aim at.** The agent can enumerate what it
cannot tell apart; it cannot tell which of the 321 confusions will change a verdict, and every ordering it
can compute is anti-correlated with harm or degenerate on it. So the unit of learning is not a run and not
a trace — it is **a question the user has to answer**, and the cheapest sound policy is to label a cell
(`n − cells`), not to hunt a counterexample. Any claim of the form "it learns the environment once" is
therefore a claim about a table plus a bill of questions per depth, and the bill is the part no architecture
has yet removed.

## 9. Next step, and what would falsify this

The question is currently *selected among pairs that already exist*. The next round makes it
*constructed*: the agent proposes a run it builds to separate the surviving statistics, and the price is
measured at depth 5, where the pool is 87 runs and a three-cell table has just been shown to be
verdict-exact.

Pre-registered falsifiers: (i) if a constructed question at depth 5 yields a verdict-exact table in fewer
than 3 questions, then "learn once, refine by asking" is a mechanism; (ii) if it needs more than
`n − cells`, the construct-nothing claim dies and the bill stands; (iii) if the depth-3 table's verdicts
stop being exact at depth 5 — 0 errors here, so any error there is a clean kill of "the table travels".

Corpus, stated plainly: **this is not SWE-bench.** SWE-bench Verified needs network, a GPU and hours, and
this sandbox has two CPUs; simulating it would be a lie. The material is this project's own three CLI
machines, executed here, judged by the same portable goal as the previous two rounds. The SWE-bench run
remains the named next corpus, with the same pre-registration and the same currencies.
