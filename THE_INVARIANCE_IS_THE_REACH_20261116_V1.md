# The invariance is the reach

**One verified demonstration, folded by this repository's own kernel, repairs the bug it came from
and, with nothing else changed, five bugs it never saw — or none at all, depending on whether the
system already knows what does not matter. That is not a metaphor. It is the paired result below,
same kernel, same demonstrations, same targets, one canonicalization apart.**

Date 2026-11-16 · branch `arena/68eb44a5-brain` · authority **NONE** (producer-run sandbox) ·
receipts `canonical/verification/ARM_LEARNED_IN_ONE_RUN_20261116_V1.json`,
`canonical/verification/WHAT_ONE_VERIFIED_REPAIR_TRAVELS_20261116_V1.json`

---

## 1. The claim under test, and the claim I had to take back

The owner's thesis, in his words: *give the model the most advanced actions, let it experience them
once, and it knows them permanently.* The last answer I gave was: **one verified experience is
permanent storage, not a rule.** The composed run's learned arm was a *replay from a record* — it
re-cited twenty lessons it could not re-learn — and every template the repository's kernel could
induce from a single demonstration came out `LITERAL`, so it fired exactly where it was taught.

That answer was too strong, and this turn is the correction, measured. Two things were wrong with the
experiment, not with the thesis:

1. **No arm in this tree had ever learned from its own judged repairs inside a run.** The learned arm
   replayed a record; the record's lesson corpus is not in this repository. So "learned" was, at that
   one point, a citation.
2. **The kernel was never given the one thing a single demonstration cannot supply and every
   demonstration needs: an invariance.** Not a fact about bugs — a statement of what does not matter.

## 2. What was built (no new abstraction was invented for the occasion)

`canonical/tools/arm_learned_from_its_own_verified_repairs_v1.py` adds an arm that learns from the
run's own experience: every repair the corpus's own `pytest` accepts becomes a `(defective, repaired)`
pair, and `canonical/swe_kernel/induced_edit_basis_v1.py` — existing, unchanged — folds those pairs
into templates. The vocabulary may only be built from repairs accepted on tasks **earlier in the same
pass**, so every task is repaired cold with respect to the tasks after it. No answer key, no record,
no cross-corpus lesson, no lookahead.

Two arms read that vocabulary, and they differ by **one function**:

| arm | precondition the template must satisfy at a site |
|---|---|
| `LEARNED_THIS_RUN` | the demonstration's literal spelling |
| `ALPHA_LEARNED_THIS_RUN` | the demonstration's literal spelling **after every bound name is canonicalized to `n0, n1, …`** |

`alpha_canonical` renames only what the function itself introduces — parameters, assignment targets,
nested defs and lambdas. Globals, imports and builtins are **free** and stay literal, because renaming
one would change which computation the program denotes. That is the whole addition: bound names are
α-renameable, and that is a theorem of the lambda calculus, not a fact about code that a person
looked up.

## 3. The paired measurement — everything else held fixed

**In the run** (41 task files, one command, one judge, 342.5 s):

| | literal preconditions | α-canonical preconditions |
|---|---|---|
| tasks where the vocabulary fired | 23 | 28 |
| candidates proposed | 304 | 384 |
| candidates that survived the target's own examples | **0** | **4** |
| candidates sent to the corpus judge | 0 | 4 |
| repairs accepted by the corpus judge | **0** | **4** |

Four survivors, four judged, four accepted. The example filter was tight enough that **no judge call
was wasted** — and the four wins cost 0.2 s each, against 6.7 s, 14.8 s and 25.8 s for the
hand-written families on the same bugs (mergesort: **129× cheaper**).

**One demonstration, pushed up three rungs** (`what_one_verified_repair_travels_v1.py`, 24 verified
repairs, each lesson built from exactly one pair):

| rung | what it asks | result |
|---|---|---|
| 1 · same bug | does the lesson fire on its own defective program, and does the judge accept? | **15 of 24 repaired**, 14 of them reproducing the accepted program byte-for-byte |
| 2 · same bug, renamed | both sides renamed by one consistent permutation of bound names | **15 of 24** — identical to rung 1: the lesson was never about spelling |
| 3 · a different bug | the same one-pair vocabulary applied, α-canonical, to all 39 other bugs | fired on **333 (demonstration, target) pairs across 39 of 39 targets**; **11 transfers**; **5 distinct bugs repaired** — `find_first_in_sorted`, `find_in_sorted`, `mergesort`, `next_palindrome`, `quicksort` |

Rung 2 is the control that makes rung 3 mean something: invariance costs **nothing** on the bug the
lesson came from, so its gains elsewhere are not bought with a loss at home. Rung 1 is the control
that the mechanism is live: a zero at rung 3 is a counted zero, not a broken fold.

The vocabulary learned inside the run ended at 47 templates, of which 9 are `RELATIONAL` (holes
carrying the transfer), 5 are supported by **two or more independent bugs**, and 15 fired on programs
they were never taught. The support-2 template `hole → hole[1:]` — taught by `longest_common_subsequence`
and `mergesort` — is what repaired `next_palindrome`.

## 4. Why this is the right answer, from first principles

A demonstration is two artifacts: a defective program and a repaired one. Everything a mechanism can
learn from it is an **alignment** of the two. With one demonstration, the only alignment available is
between the two sides of that pair — which is why the kernel's first output is `mid → mid + 1`, and
why with one demonstration there is nothing to anti-unify *across* and every template comes out
literal. The demonstration can therefore supply **content** and it cannot supply **reach**.

Reach has to come from somewhere else, and there are exactly two possible sources:

- **experience** — more demonstrations, so that differences *between* them can be abstracted. This is
  the thesis, and it fails on its own arithmetic: the identifiability measurement already in this tree
  says one trace leaves 1,037 survivors (10.018 bits), and the replay arm's twenty lessons could only
  be re-checked where the record named the line.
- **structure the system already has** — an invariance saying what does not matter, so one
  demonstration covers a whole equivalence class of programs. This is what the α result measures.

**The demonstration is the content; the invariance is the reach; and the invariance cannot be learned
from the demonstration, because one demonstration has nothing to compare.** That is the precise sense
in which "show it once and it knows it permanently" is true and false at the same time. It is true for
everything the representation already quotients out. It is false for everything else, and no amount of
showing changes that — showing adds instances, not invariances.

## 5. What it bought, stated without inflation

**Capability: nothing.** All four in-run wins and all five rung-3 repairs land on bugs the three-arm
composition already repaired. The total is **24 of 40 either way**. What changed is the *route*: four
of those bugs are now reached by a rule the system induced from its own verified experience at 0.2 s,
where it used to spend up to 25.8 s enumerating a hand-written list. That is a cost win and it is
labelled as one in every row (`already_repaired_by_the_three_arms`).

**And a ceiling this kernel cannot pass, counted:** 15 of 24 accepted repairs are self-reproducible as
a context-preserving substitution. The other 9 need a new statement, a coordinated multi-position
edit, or a subtree rewrite — the rungs the corpus has always said are missing (9 leaf / 18 node /
7 multi / 6 shape over 40 fixes). No invariance creates those; they are vocabulary, and vocabulary is
still the wall.

## 6. The bottleneck, sharpened rather than moved

The standing answer was *the hypothesis space — assembled from each failure's own evidence, not
listed*. This turn splits that space along its real seam:

> **the space's SIZE is the vocabulary; its REACH PER DEMONSTRATION is the invariant set.**

Everything else was held fixed and only the invariance moved: 0 survivors → 4 survivors, 0 repairs → 5
bugs repaired by a single demonstration. The vocabulary stayed where it was (24 of 40, both ways).
Which means the next unit of capability is not another demonstration and not another hand-written
edit kind — it is **the next thing the system can be told does not matter**: that an integer literal is
interchangeable with another integer literal, that `<` and `>` name the same relation up to operand
order, that an index and the value at that index are different roles for the same symbol. Each such
invariance is one canonicalization and multiplies the reach of every demonstration already held. That
is a part that pays for itself, and it is the only part on the table that does.

## 7. Non-claims

- 40 single-function Python bugs, one public corpus. Not general repair, not SWE-bench, not computer
  use. The corpus is one the author did not choose, which is the only reason its numbers are quotable.
- Producer-run. Authority NONE. No independent verification; no terminal or capability credit.
- `RECORDED_LEARNED_REPAIR` is still a **replay** from a record whose lesson corpus is not in this
  repository. It is kept because dropping it would change the composition for reasons unrelated to
  this question; nothing here credits it.
- One task file (`node`) is a class module with no top-level function and is now reported `NO_FUNCTION`
  rather than `NO_EXAMPLES` — a reclassification, not a repair.
- Zero model dependency, zero network calls at run time, zero spend. The invariance is a theorem; the
  vocabulary is a fold over judged repairs; the verdict is the corpus's own tests on a fresh copy with
  the answer key absent.

## 8. Reproduce

```
python3 canonical/tools/arm_learned_from_its_own_verified_repairs_v1.py \
  --quixbugs <QuixBugs> --record canonical/verification/QUIXBUGS_EDIT_KIND_TRANSFER_20261112_V1.json \
  --prior canonical/verification/COMPOSED_REPAIR_ONE_RUN_20261116_V1.json \
  --out /tmp/learned_pass.jsonl --receipt /tmp/learned_receipt.json --budget-s 40

python3 canonical/tools/what_one_verified_repair_travels_v1.py \
  --quixbugs <QuixBugs> --pass-jsonl /tmp/learned_pass.jsonl \
  --out /tmp/travel.jsonl --receipt /tmp/travel_receipt.json
```
