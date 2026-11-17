# What is left for a lesson to buy

**The claim under test.** *"Give the model the most advanced actions, let it experience each one
once, and it learns it permanently. The same trick makes any computer use permanent. Therefore
everything on a computer, and all of advanced software engineering, is solved."*

**The verdict, before the evidence.** Right that a single demonstration is enough to add an action to
the vocabulary — permanently, with no gradients and no retraining. Wrong that it follows that
everything else comes free, and the size of the gap is not a matter of opinion: it is 8 of 40, of
which 3 transfer. Everything below is a measurement on published data with zero model calls.

---

## 1. What was measured, and why it needs no search

The tree's solver now builds its edit space out of the program in front of it: the node types the
program already uses, the operators it already applies, its own names, its own commutative pairs,
its own statement shapes. Last session that space solved **8 of 8** published QuixBugs bugs with
zero model calls (`AIMED_EDITS_FROM_THE_PROGRAM_AND_THE_FAILURE_20261117_V1`).

So the question is no longer *"does a lesson transfer?"* but **"what is left for a lesson to buy once
the space comes from the artifact?"** That question has an exact answer that needs no search:

> For each of the 40 published QuixBugs bugs, is the corpus's own published fix reachable by
> (a) the old hand-written space, (b) one of the classes read off other programs, or (c) neither?

"Reachable" means: some program in the space **is**, function for function, the corpus's corrected
program. That is a membership fact about a set. No execution, no judgement, no verdict — this
document says which fixes are *expressible*, and separately says which are *solved*.

### The instrument had to be fixed first, and the failure is instructive

The first version of the tool re-implemented the space's rules over the structural difference between
the two functions, and reported that `sqrt` and `powerset` were unreachable — while the solve
receipt said both had been solved **from that same space**. The cause was not a bug in the space. It
was that the space writes `(approx) ** 2` and `rest_subsets + (X)`, and the re-implementation
compared against `approx ** 2`. A second implementation of a set is not a measurement of the set; it
is a measurement of the second implementation.

The tool therefore walks the **real space** — the same `space_builder` the solver uses — and compares
every candidate against the corpus's corrected program. It also reconciles the two instruments on the
8 bugs the solver already knows work: all 8 are reachable, with the class each was solved by
(`kheapsort` SLICE, `powerset` PREPEND_TERM, `subsequences` NEST, `to_base` COMMUTE, `shunting_yard`
INSERT_STATEMENT, `flatten`/`hanoi`/`sqrt` the hand-written space). The two instruments now agree
on every task where agreement can be checked.

---

## 2. The result: 40 published bugs, exact

| bucket | count | what it means |
|---|---|---|
| the fix is in the **old hand-written space** | **18** | nothing needs to be learned; the grammar already builds it |
| the fix is reached **only by a class read off another program** | **8** | before donor exclusion — an upper bound, and a dishonest one on its own |
| …of those 8, reached by a class learned on a program that **is not its donor** | **3** | the honest "learn once, reuse it" number: 3 of 40, 7.5% |
| a **single edit exists that no class can build** | **13** | a vocabulary gap, not a lesson gap |
| the fix needs **more than one edit** | **1** | composition |

The classes, their donors, and what they actually reach:

| class | read off | reaches | reaches a program that is not its donor |
|---|---|---|---|
| SLICE | kheapsort | kheapsort | — |
| PREPEND_TERM | powerset | powerset, next_palindrome | next_palindrome |
| NEST | subsequences | subsequences | — |
| COMMUTE | to_base | to_base | — |
| INSERT_STATEMENT | shunting_yard | shunting_yard | — |
| ATTRIBUTE | subsequences | topological_ordering | topological_ordering |
| CALL | powerset | bucketsort | bucketsort |
| BOOLEAN_OP | shunting_yard | — | — |
| IF_EXPRESSION | none | — | — |

Seven of the nine classes reach anything at all. **Four of those seven reach only the program they
were read from** (COMMUTE, INSERT_STATEMENT, NEST, SLICE); two reach nothing in this corpus. Three transfer
(ATTRIBUTE, CALL, PREPEND_TERM), and between them they buy **three** programs. That is the honest shape of
"learn it once and reuse it" here.

**And the number that matters most is the one nobody expects:** 18 of 40 published fixes were
reachable *before any lesson at all*, because the program itself supplies the vocabulary. The lesson
is not what makes the system work. The artifact is.

---

## 3. Why exactly these numbers, from the two mechanisms that were named in advance

**Identifiability.** One trace is consistent with exponentially many hypotheses about what caused the
fix. A demonstration therefore pins a shape only if that shape is *already* in the vocabulary; it
cannot distinguish "this is a slice" from "this is `arr` followed by `[k:]`" unless the vocabulary
contains slices. That is why 5 of the 9 classes reach only their donor: the class was read off a
shape that the other 34 programs do not need.

**Vocabulary insufficiency.** `INSUFFICIENCY_CERTIFICATE_20261113_V1` says that when the causal
observable is absent from the representation, repetition cannot separate success from failure. The 13
rows in the fourth bucket are that certificate, written per program, with the missing expression
named:

| program | one edit that exists | why the space cannot build it |
|---|---|---|
| mergesort | `len(arr) == 0` → `len(arr) <= 1` | recombines the site with one of its own operands |
| lis | `length + 1` → `max(longest, length + 1)` | encloses the site with a call over a neighbouring expression |
| possible_change | `total < 0` → `total < 0 or not coins` | joins the site with `not <atom>` |
| detect_cycle | `hare.successor is None` → `hare is None or hare.successor is None` | builds a *new* comparison from two atoms, then joins it |
| next_permutation | `perm[j] < perm[i]` → `perm[i] < perm[j]` | permutes a comparison's operands |
| get_factors | `[]` → `[n]` | a list literal over an atom |
| kth | `k` → `k - num_lessoreq` | a binary operation with a neighbouring atom |
| levenshtein | `1 + levenshtein(...)` → `levenshtein(...)` | strips a term |
| shortest_paths | `weight_by_edge[u, v]` → `weight_by_node[v]` | a subscript over a different name |
| shortest_path_lengths | `(j, k)` → `(k, j)` | a permutation inside a tuple |
| depth_first_search | insert `nodesvisited.add(node)` | statement built from the program's own material |
| reverse_linked_list | insert `prevnode = node` | assignment built from the program's own material |
| wrap | insert `lines.append(text)` | call-statement built from the program's own material |

Not one of these is a *new action the model has never seen*. Each is the program's own material
combined by the language's own syntax. A demonstration of any of them would teach one instance and
still leave the other twelve unreachable — which is precisely the measured failure of the lesson
route.

---

## 4. The next rung, measured but deliberately not shipped

If the missing bucket is "recombination of the site with the material around it", the principled fix
is not a longer list of shapes — it is the language's expression grammar applied to the statement the
site sits in, with a bound on how much bigger than the site the answer may be:

> no candidate may be more than **4 nodes** larger than the expression it replaces; the material is
> every expression in the statement, *complete*, not a sampled subset.

Measured on the 13 escapes plus the composition, as a membership probe at the site the difference
names (a substitution test, *not* a walk of the widened space): **9 of 14 become reachable** — the 26
already reachable plus those 9 is **35 of 40** published fixes. What remains is 3 statement-granularity insertions, 1 that
needs two levels of recombination, and 1 true composition.

This is the established shape of expression-level repair, not an invention here: S3 enumerates
expressions *starting at the size of the buggy expression* under a cost bound, and deductive repair
builds a grammar of *variations of the expression at the localised fault*. The difference is that
this tree has no solver and no types — one candidate is ~1 ms — so the budget can be spent on
candidates rather than on the symbolic machinery.

It is not in `RULES` yet, and that is on purpose: turning it on changes the space, and every shipped
solve receipt describes the space it was produced from. It gets its own solve run, not a quiet edit.

**One more thing that rung taught, which cost real reachability:** with a fixed "keep the N most
promising neighbours" cap, *which* fixes the rung could reach changed with N — `len(arr)` fell off the
list and `len(arr) <= 1` became unreachable, while `perm[i] < perm[j]` came into reach. A cap is not
a measurement. The bound has to be a property of the *answer* (its size), never of an index into a
list.

---

## 5. What this means for the other half of the claim — computer use

The same structure, measured elsewhere: on OSWorld 2.0 (108 long-horizon workflows) the best
configuration completes **20.6%** of tasks outright, and completion collapses towards zero past two
hours; under **7%** of the action budget is spent on detecting or correcting errors; the failure
clusters are implicit state, multi-item tracking, conflict disambiguation and a changing environment.
None of those is "the agent has not been shown the click once". Each is *the fact the goal depends on
is not observable at the moment of acting*.

An experienced action is a row in a vocabulary. A demonstrated workflow is one instantiation of a
plan. Neither makes a hidden variable visible, and neither writes an expression the representation
cannot express.

---

## 6. The single limiting factor

> **Can the fact the goal depends on be observed at the moment of acting, and can the action
> satisfying it be expressed by what the artifact already contains?**

Observability binds computer use. Expressibility binds software engineering. Learning is neither —
which is why the numbers above are so lopsided: the artifact bought 18 fixes, the classes bought 8
(3 reusable), and the remaining 14 are the vocabulary arguing with itself.

---

## 7. Integrity of this document

* **40 of 40** rows measured on published QuixBugs (`jkoppel/QuixBugs`, MIT). No synthetic data.
* The 8 bugs already known to work are used **only** to reconcile the two instruments. They are
  never counted as evidence of coverage — that would be self-congratulation.
* **Zero model calls, zero network calls at run time, zero execution.** Reachability is not a solve
  and is never written as one.
* Every number here is reproducible by one command —
  `python3 canonical/tools/what_the_learned_classes_cover_v1.py --quixbugs /tmp/QuixBugs --extra-probe`
  — and is recorded, row by row, in
  `canonical/verification/WHAT_IS_LEFT_FOR_A_LESSON_TO_BUY_20261117_V1.json`. The experimental rung is
  recorded there as `MEMBERSHIP_AT_THE_SITE__NOT_A_SPACE_WALK__NOT_SHIPPED`, because that is what it is.
* Tests: `canonical/tests/test_what_the_learned_classes_cover_v1.py` (the difference instrument is
  exact, reachability walks the real space, a class reaching only its donor reports no transfer, and
  the buckets partition the rows).
