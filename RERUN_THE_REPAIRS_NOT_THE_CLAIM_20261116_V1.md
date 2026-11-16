# Re-running another arm's repairs instead of believing them

**2026-11-16 · branch `arena/c542a50f-brain` · 20 claimed repairs, re-judged · no model, no weights, no network**

Receipts: `RERUN_THE_LEARNED_ARMS_REPAIRS_20261116_V1.json` (this turn) ·
`QUIXBUGS_EDIT_KIND_TRANSFER_20261112_V1.json` (the claim) ·
`COMPARISONS_CLOSE_THE_LAST_MILE_20261116_V1.json` (the hand-written families, 18/40).

---

## Why this exists

Yesterday's note projected a **26/40 union** between the hand-written families (18/40) and the
edit kinds learned cross-corpus (20/40), and then — in the very next PR — warned that the
union might be inflated because the tree's fast screen can accept a candidate that pytest rejects
(I had found 3 such cases on the nine bugs with no JSON).

A projection resting on an arm nobody re-checked is worth nothing, and a warning about one's own
number is worth nothing either unless it is tested. So this turn tests it.

## What was done

That arm's record stores, per repaired bug, the operator and **the exact lines the repair removed and
put in**. So the repairs can be re-run rather than believed: apply the recorded line changes to the
defective program, then ask the corpus's own `pytest` on a fresh copy. No lessons, no learner, no
screen — a check on a recorded claim, not a reproduction of the mechanism.

## What it found

| | count |
|---|---|
| claimed repaired | 20 |
| **confirmed by the corpus's own pytest** | **16** |
| refused by the corpus's own pytest | 0 |
| not reconstructible from the record | 4 (depth_first_search, next_palindrome, rpn_eval, shortest_path_lengths) |

**Zero of the reconstructible repairs were false.** The four that could not be rebuilt are a limit of
my reconstruction, not evidence against the claim: their recorded lines are truncated (a multi-line
dict literal in `rpn_eval`, an assignment in `shortest_path_lengths`) and I will not score what I could
not run.

Also recorded, and it corrects me: that tool counts `screen_said_pass_runner_said_no` per bug, and the
total across all forty is **0**. It re-checked every screen
acceptance with the benchmark's runner. So yesterday's caveat was too strong *about that arm* — its
numbers are runner-verified. The screen really can over-accept (my three cases stand, they are in the
previous receipt) but it did not contaminate this one.

## The union, recomputed on verified evidence only

| set | repaired | how verified |
|---|---|---|
| hand-written families | 18 / 40 | corpus pytest, every task |
| learned kinds, cross-corpus | 16 / 40 | corpus pytest, re-run this turn from the record |
| **union** | **24 / 40 (60%)** | both sides pytest-only |

Only the learned arm reaches: hanoi, knapsack, levenshtein, longest_common_subsequence, minimum_spanning_tree, to_base — **6 bugs**.
Only the hand-written families reach: bitcount, kth, lis, max_sublist_sum, mergesort, next_palindrome, rpn_eval, sieve — **8 bugs**.

So the union is real, it is **24** rather than the projected 26, and the shape of the finding
survives the correction: **two vocabularies, disjoint in both directions, each under half.** The
missing bugs are not in the overlap; they are in the gap between two vocabularies that do not merge
themselves.

## What is real and what is not, one more time

**Real.** Instant storage of a verified experience. One-demonstration generalisation on real code
(60.0% vs 15.0% cache). Admission that refuses a harmful lesson. A vocabulary-free synthesis that builds
`(not depth)` from a failure in 0.2 s. Identification settling in ~1.31 chosen questions when the space
holds the repair. And now: an arm's claimed repairs re-runnable from its own record — the property that
makes any of these numbers quotable at all.

**Not real.** That one experience is a rule (~10 bits survive it). That more environments buy coverage
(2.5× compute bought 1 page in 37; 0/10 for a new kind). That making a missing observable present is
the fix (0 of 9 repaired). That the smartest actions are the missing piece (list 0/20, one-demonstration
shape 1–2/20, cross-corpus kinds 16/40). That anything here is sentience.

**The single bottleneck: the hypothesis space — assembled, not listed.** Every arm measured here is a
vocabulary, each covers a different third of the corpus, and nothing in the tree composes them under
one judge. That composition, with pytest as the only verdict, is the next build and it needs no new idea.

## Non-claims

- 40 single-function Python bugs. Not general repair, not SWE-bench, not computer use.
- 4 claimed repairs were not reconstructible: counted as unknown, never as confirmed or refuted.
- Re-running a recorded line change is not re-running the learner; the mechanism's own claim is only
  checked here to the extent its record allows.
- Producer-run, one machine, authority **NONE**. No tolerance widened, `truth.achieved` unchanged.
