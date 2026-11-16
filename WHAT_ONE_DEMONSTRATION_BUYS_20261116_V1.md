# What one demonstration buys

**2026-11-16 · branch `arena/8ec547dd-brain` · measured on 40 real published bugs**

Receipt: `canonical/verification/WHAT_ONE_DEMONSTRATION_BUYS_20261116_V1.json` (every count below is
folded from the raw rows of the runs, not typed).

---

## The question, taken literally

> Give our model the most advanced coding actions, let it experience them once, and it learns them
> permanently. Add coverage of every action and the smartest actions, and you have the best coding
> agent on the planet. Why can't we do this now?

The direction is right; every "therefore" is false. This note takes the part that is still false
*after* the earlier notes removed the others — and it does not argue the point. It measures it on a
public corpus of real bugs, end to end, with the corpus's own tests as the only verdict and no model
anywhere in the loop.

## What was already real

The tree can localize a repair to one statement, derive an operator rule from a single
demonstration, verify it on a mutated twin, and refuse to store a lesson that breaks a program it was
never taught on. One demonstration really does buy a rule that transfers to a different module. None
of that is rebuilt here.

What had never been tested is whether any of it makes the *next real bug* repairable. This is the
number.

## The measurement

**Corpus.** [jkoppel/QuixBugs](https://github.com/jkoppel/QuixBugs) (MIT): 40 real buggy Python
programs, each with the authors' own pytest file and JSON test data. Nobody here wrote these bugs,
chose them, or can see a fixed version during a run.

**Why not SWE-bench Verified.** It cannot be run honestly here: a container and a multi-GB
environment per instance, with a network oracle at run time. The standing rule is *test only on hard
real tests our own system runs*. QuixBugs is the hardest **open** corpus that runs at \$0 on one
machine with no model and no network. It is not the frontier, and this note does not claim it is.

**Integrity, enforced rather than promised** (`canonical/tools/quixbugs_end_to_end_repair_measure_v1.py`,
tested in `canonical/tests/test_quixbugs_measurement_integrity_v1.py`):

1. `correct_python_programs/` is **never copied** into a task directory; `build_task` asserts its
   absence before every task.
2. Every test file and program is hashed and recorded; the verdict is the corpus's own test, re-run
   by the harness.
3. The repair loop is candidate-only, so its own `pass: true` is never evidence: the harness applies
   the candidate to a **fresh** copy and runs the test there.
4. Defects that never terminate are reported as *unmeasurable*, not as failures and not as successes.

---

## Finding 1 — the edit vocabulary is a hard zero, not a slow search

The tree's repair primitive enumerates a hand-written list: swap a comparison operator, swap a binary
operator, swap `min`/`max` or `any`/`all`, add a `None` guard, substitute a literal mined from the
tests.

`bitcount`'s published fix is `n ^= n - 1` → `n &= n - 1`. There is **no `ast.AugAssign` rule in that
list**, so the repair is not hard to find — it is *unreachable* at any depth, any candidate count, any
budget. A search cannot return a hypothesis its generators cannot build, and an oracle can only choose
among the hypotheses it is shown.

> Measured: 280 candidates tested, 0 accepted, 83 s. The failure is not search. It is vocabulary.

## Finding 2 — real fixes sit on a ladder, and the ladder is measurable

`classify_fix_shape` names, for any fix, the smallest edit space that can express it — the smallest
subtree that differs, without descending into it:

| rung | what the fix is | count | tasks |
|---|---|---|---|
| `RUNG_LEAF` | one operator / name / literal swapped | **9/40** | bitcount, breadth_first_search, bucketsort, find_first_in_sorted, hanoi, knapsack, quicksort, sieve, topological_ordering |
| `RUNG_NODE` | one node replaced at one position | **18/40** | detect_cycle, find_in_sorted, flatten, is_valid_parenthesization, kheapsort, kth, lcs_length, levenshtein, lis, longest_common_subsequence, max_sublist_sum, minimum_spanning_tree, next_palindrome, pascal, possible_change, powerset, shortest_path_length, sqrt |
| `RUNG_MULTI` | several coordinated positions | **7/40** | gcd, mergesort, next_permutation, rpn_eval, shortest_path_lengths, shortest_paths, to_base |
| `RUNG_SHAPE` | a statement inserted or deleted | **6/40** | depth_first_search, get_factors, reverse_linked_list, shunting_yard, subsequences, wrap |

**Two thirds of real fixes (27/40 = 67.5 %) are a one-node substitution.** A leaf-only basis — the
most generous reading of the hand-written list — reaches 9/40 = 22.5 %, and the list as it actually
stands does not even reach that, because it omits `AugAssign` and has no rule for an arbitrary
identifier swap (`bucketsort` needs exactly that).

Two honest caveats about the ladder, because it is easy to over-read:

- It describes the **published** fix, not the minimum edit that passes. `next_permutation`'s published
  fix is a two-position swap (rung MULTI), and the hand-listed basis repaired it with a single
  comparison swap. So 27/40 is a **lower** bound on what a one-node space can reach.
- A rung is a property of the *fix*, not of the bug's difficulty. Two programs at the same rung can
  differ completely in how hard it is to find the position.

## Finding 3 — a demonstration can be compiled into a template, and the template travels

`induced_edit_basis_v1` replaces enumeration with induction:

1. compare the defective and repaired ASTs, ignoring inert string statements (QuixBugs appends the
   **buggy** source inside a string literal — a first run that did not strip these read documentation
   as edits, and had to be thrown away);
2. keep only the **deepest** differing position, so `binsearch(mid, end)` yields a lesson about the
   argument, not a fact about one call site;
3. when the node type changes, the fix is **containment** — `mid` becomes `mid + 1`, a sum becomes
   `max(0, sum)` — expressed as *the old node, wrapped*, with a hole in the new tree;
4. record the ancestry of node types as the applicability condition, and the number of independent
   demonstrations as support.

Taught on the **training half only** (20 bugs, split by `sha256(name)`), this produced 9 leaf and 25
node templates. The relational ones are genuine rules, not source text:

```
Name  (Call)    H  ->  H + 1                taught by find_in_sorted
BinOp (Assign)  H  ->  max(0, H)            taught by max_sublist_sum
BinOp (Assign)  H  ->  max(longest, H)      taught by lis
Call  (BinOp)   H  ->  H - 1                taught by next_palindrome
Name  (BinOp)   H  ->  H ** 2               taught by sqrt
Name  (Call)    H  ->  H[1:]                taught by longest_common_subsequence
BinOp (Return)  1 + H  ->  H                taught by levenshtein
```

**The transfer that actually happened.** `pascal`'s bug is `for c in range(0, r)` where the published
fix is `range(0, r + 1)`. It was repaired by the template induced from **`find_in_sorted`** — a
different program, in the training half, shown once:

```
pascal   REPAIRED__CORPUS_TEST_PASSES   candidates tested: 8   taught_by: [find_in_sorted]
         mutation Name->Name(RELATIONAL), context ['Call'], score 4 -> 0
         verified on a fresh copy by the corpus's own test -> 5 passed
```

Eight candidates instead of 274, and the lesson came from a program that does not contain the bug
being fixed. That is what a permanent, transferable capability looks like when it is real.

## The result, including the part that is not flattering

Both mechanisms were run end to end on the **same 20 held-out bugs**:

| | hand-listed basis (control) | induced basis (treatment) |
|---|---|---|
| repaired | **2/20** — next_permutation, quicksort | **1/20** — pascal |
| candidates tested | 5,021 | 224 |
| accepted an edit but could not close the task | 14 | — |
| nothing strictly improving | 2 | 17 |
| defect does not terminate (unmeasurable) | 2 | 2 |

**The successes are disjoint.** Intersection empty; union 3/20. Neither mechanism dominates:

- The control repaired `quicksort` (`>` → `>=`, a comparison) because its list already contains
  comparison swaps. The treatment could not: the training half never demonstrated that operator
  **pair**, and identity does not transport.
- The treatment repaired `pascal` because `H → H + 1` was demonstrated once and generalizes. The
  control could not: it has no index-offset rule, and it spent 274 candidates and 2 accepted edits
  failing to close it.
- 22× fewer candidates for the treatment, and 22× fewer does not mean better — it means *cheaper per
  attempt and narrower per basis*.

That is the honest state: **an induced basis is not a better hand-listed basis. It is a different
one, and the two fail on different things.**

---

## The answer to "why can't we just do this now"

Because a demonstration is not one thing. It carries bits at several abstraction levels, and they
travel different distances:

- **The identity of the edit** (`^=` becomes `&=`) transports to almost nothing. The corpus's 40
  fixes are 40 *distinct* edits; showing 20 of them teaches the other 20 essentially nothing. This is
  why the treatment refused 17 of 20 held-out bugs: not one template's precondition held.
- **The shape of the edit** (`X` becomes `X + 1`; a sum becomes `max(0, sum)`) transports to every
  program where the same context and precondition occur. That is exactly the one case that worked.
- **The goal of the edit** ("make this count monotone", "handle the degenerate case") transports to
  everything and is not an edit at all. Nothing in the tree infers goals, so this level is not merely
  unlearned — it is unrepresented.

So "show it once and it learns permanently" is true only at the level of the **shape**, and only when
the basis can express that shape and the precondition happens to recur. On a corpus of distinct
fixes, that is rare — and its rarity is measurable, not a matter of taste.

**The single bottleneck, restated after this measurement:** the **hypothesis space of edits** — its
vocabulary and its abstraction level. Not the oracle, not the budget, not the transfer of weights, and
not the verifier (the previous note's bottleneck) which only begins to matter *after* a candidate
exists. Here, for a third of real fixes, no candidate can exist at all, and for the rest, whether one
can exist is decided by a 12-line list.

Every other gap this project has measured — identification, admission, scope, coverage — sits
downstream of that one.

## What this buys, and what it does not

**Bought:** an induced basis that folds one demonstration into a transportable template; a rung
classifier that says, for any fix, whether a basis can express it at all; an end-to-end measurement
against a real public corpus with the answer key provably absent; and 25 tests pinning the mechanism
and the measurement's own integrity — including one that caught the consolidator trusting a flag a
row set about itself instead of deriving transfer from `taught_by`.

**Not bought, and not claimed:**

- QuixBugs is 40 single-function programs. No frontier claim, no SWE-bench comparison.
- A repaired task is a repaired program, not a repaired repository.
- The producer ran this. Sandbox measurement, authority `NONE`.
- `RUNG_MULTI` and `RUNG_SHAPE` (13/40) have no template form yet. Several coordinated positions and
  statement insertion need a different shape of rule, not a bigger candidate list.
- Two defects (`sqrt`, `bitcount`) never terminate, so the oracle answers "timeout" instead of "N
  failures". Both mechanisms are blind to them, and the control's own contract refuses to even start.
  That is a distinct gap and it is not addressed here.
- No sentience claim. Nothing here is measured as understanding; it is measured as repairs.

## What the next build must be

The two failures point the same way: a rule has to be abstracted past the identity of the edit it was
learned from, and the abstraction has to be *chosen by evidence* rather than by taste.

1. **Class-level comparison edits.** One demonstration of a boundary relaxation should yield "relax
   strict `<` to `≤`, and its mirror `>` to `≥`", so `knapsack` transfers from a demonstration of
   `quicksort`. This is the rung that turns identity into a family, and the training half already
   contains the witnesses.
2. **Coordinated multi-position templates**, for the 7/40 that need two edits held together.
3. **Insertion templates with a precondition**, which is exactly where `lesson_localization_v1`
   already refuses by design and for the right reason: emitting an operator rule for a missing guard
   would fire 32 times and repair nothing.
4. **A timeout objective**, so a non-terminating defect has a signal to descend instead of being
   unmeasurable.

Then the same question is asked again on the same corpus, and the ladder moves.
