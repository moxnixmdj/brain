# The space is assembled, not listed — and no single vocabulary covers it

**2026-11-16 · branch `arena/78a8c032-brain` · 40 published QuixBugs bugs · no model, no weights, no network**

Receipts: `SYNTHESIS_FROM_THE_FAILURE_20261116_V1.json` (this turn) ·
`COMPARISONS_CLOSE_THE_LAST_MILE_20261116_V1.json` (hand-written families, 18/40) ·
`QUIXBUGS_EDIT_KIND_TRANSFER_20261112_V1.json` (learned edit kinds, cross-corpus, 20/40) ·
`IDENTIFICATION_COST_IN_A_REAL_SPACE_20261116_V1.json` (what one question is worth).

---

## 0. The answer, in one paragraph

The direction is right and the quantifier is wrong. One verified experience is permanent **storage**;
it is not a **rule**. Measured in this tree: after one demonstration a real repair space still holds a
median **1,037** programs
(10.018 bits left), and an edit *shape* learned from one showing
transferred to about **1–2 of 20** held-out bugs. What does transfer is a vocabulary learned across a
**different corpus** — 20 of 40 bugs repaired having never been shown a single QuixBugs fix —
and what no single vocabulary does is *cover* the space: the two independent mechanisms repair
**26 of 40 (65%)** between them, each under half alone, with **8**
bugs only the learned one reaches and **6** only the hand-written one. So "give it the
smartest actions once" is real, useful, and provably not the whole answer: what it learns is a
vocabulary, and vocabularies do not compose by themselves.

## 1. Every way this project has built a hypothesis space, on the same 40 bugs with the same judge

The judge is always the corpus's own pytest file on a fresh copy, with the answer key absent.

| how the space is built | repaired | cost | why it stops |
|---|---|---|---|
| hand-written list of edits | **0 / 20** held out | 280 candidates | the fix type is absent; no budget reaches it |
| one demonstration → induced edit kinds | **~1–2 / 20** | — | a template fires only where its precondition literally holds |
| kinds learned from **another corpus** (164 HumanEvalFix fixes; no QuixBugs fix shown) | **20 / 40** | ~1000 test runs/bug | the *kinds* travelled; the bugs never did |
| hand-written families (permutation, composition, atom shape, insertion, comparison) | **18 / 40** | 200,529 candidates, 510 s | blind outside five families |
| **synthesis from the failure** (this turn) | **3 / 31** | ~2,000 evaluations, 0.2 s | reaches only fixes that *are* the returned value |

**This turn's build is the informative negative.** Synthesis from the failure has no vocabulary at all —
no list, no demonstration, no template. Given only the defect and its examples it observed the locals
in scope at the return and built `(not depth)` for `is_valid_parenthesization` from 655 candidate
expressions in 0.2 s. It repaired 3: bucketsort, is_valid_parenthesization, quicksort — every one already
reachable by the hand-written families, so it adds **0 new** bugs.

That is the sharpest result today: **a vocabulary-free construction and a hand-written vocabulary hit
the same wall from opposite sides.** The wall is neither "our list is incomplete" nor "we need a better
synthesizer". It is that the fixes are not all of one kind.

## 2. The composition result — the one real capability gain on the shelf

| mechanism | repaired |
|---|---|
| hand-written families | 18 / 40 |
| learned kinds, cross-corpus, clean | 20 / 40 |
| **union** | **26 / 40 (65%)** |

Only the learned mechanism reaches: depth_first_search, hanoi, knapsack, levenshtein, longest_common_subsequence, minimum_spanning_tree, shortest_path_lengths, to_base.
Only the hand-written families reach: bitcount, kth, lis, max_sublist_sum, mergesort, sieve.

Both parts already exist here, and no run has ever put them side by side. **That is the fastest
capability increment available and it needs no new mechanism** — which is precisely where the user's
thesis both predicts and fails: the actions do not merge themselves.

Caveat that changes the number: this is a **projection from two receipts** judged by the same oracle on
the same 40 bugs, not one run of a composed system. Both runs are deterministic and use the same
verifier, so "run both, keep whichever passes" repairs the union — but it must be measured as one run
before it is quoted as a score. Half the learned mechanism's repairs are another program rather than
the published fix (10 of
20); they pass the corpus's own tests, which is the only claim made for them.

## 3. Why "therefore everything" does not follow — five steps, five numbers

| # | step | measured |
|---|---|---|
| 1 | act at all | **55 of 92** held-out pages (56 after 2.5× compute) |
| 2 | one success ⇒ a rule for the next instance | **60.0%** vs **15.0%** cache — real, large |
| 3 | storage ⇒ correct knowledge | ungated permanence **breaks a correct program** |
| 4 | N verified skills ⇒ a verified sequence | two correct skills compose to a **no-op** |
| 5 | learned procedure ⇒ any computer use | best 2026 agent **20.6%** binary, OSWorld 2.0 |

Steps 1, 3, 4 and 5 are not learning problems. They are evidence problems: what could have failed the
candidate, and what does the failure leave behind.

## 4. The single bottleneck, in a form that can be tested

**The hypothesis space — and specifically that it must be assembled from each failure's own evidence,
because no fixed vocabulary covers it.**

Not the learner: learning selects inside the space, and one showing transfers to 1–2 of 20. Not the
budget: 2.5× compute bought one page in 37. Not the oracle alone: identity needs
10.018 bits removed before a question means anything, and once the
space is right **one** chosen question suffices — mean **1.31** after the first demonstration, across
the 16 tasks that held a repair; on the 7 tasks where none was in the space, no number of
questions helped. The space binds on all 40 here, and it does not arrive from one place.

## 5. The smartest things to do, in the order they pay

1. **Compose the two mechanisms and measure the union as one run** — projected 26/40, needs no
   new idea, only the harness that exists.
2. **Try synthesis-from-the-failure first on every bug**: 0.2 s to test the highest-yield shape before
   any enumeration starts.
3. **Route family work with the identification instrument**: one question tells you whether a task is
   space-broken or observation-broken. Never spend 25,000 candidates on a task it refutes instantly.
4. **Do not build a fourth vocabulary.** Three have been measured; the ground between them is empty.
5. **Kill list:** more demonstrations as coverage; more environments with the same vocabulary; quoting
   retired benchmarks (SWE-bench Verified is contaminated — OpenAI stopped reporting it in Feb 2026);
   any bottleneck claim without a per-task test of which factor binds.

## 6. Non-claims

- **Not sentience.** The only proxy here — does experience change competence on a new problem — is
  measured and small. Nothing here measures, implies, or requires a creature.
- **Not general repair.** 40 single-function Python bugs. Synthesis-from-the-failure refuses a fix that
  needs a new statement or a different recurrence rather than approximating it.
- **The union is a projection** from two receipts, not one composed run.
- Half the learned mechanism's repairs are not the published fix, only a program its tests accept.
- Producer-run, one machine, authority **NONE**. No tolerance widened, `truth.achieved` unchanged.
