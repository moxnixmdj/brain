# WHAT AN OPERATOR MEANS IS A COMPUTATION, NOT A LIST

**Date:** 2026-11-12
**Branch:** `arena/12c4f901-brain`
**Authority: NONE.** Producer-run measurement on this sandbox. Every number below was produced by
executing code in this repository, and the generator that produced the machine-readable copy is
recorded in `canonical/verification/OPERATOR_SEMANTICS_20261112_V1.json`.

---

## 1. The one-sentence finding

The list that decides whether a learned lesson may be widened past the skeleton it was taught on was
answering a **semantic** question by **enumeration**, nothing in the tree computed it, and it was
wrong in both directions at once — unsound for two operators it admitted, and too narrow for a real
shipped lesson it refused.

---

## 2. Why this is on Problem 2's critical path and not a side issue

`canonical/swe_kernel/operator_generalization_v1.py` is the only mechanism in this tree that widens a
crystallized rule beyond the exact statement shape it was taught on. The tree has already measured
what that is worth: one boundary lesson (`<= hi` → `< hi`) reached **1 of 7** structurally novel
Python instances as stored, **6 of 7** through this module, and **7 of 7** with semantic
normalisation added. So this module *is* the difference between a lesson that replays its skeleton
and a lesson that generalises.

Whether it may act at all was decided by:

```python
# Operators that mean the same thing across python/go/rust/typescript/java/cpp and may be
# generalized. Anything else is refused rather than guessed at.
GENERALIZABLE = frozenset({
    "<=", ">=", "<", ">", "==", "!=", "+", "-", "*", "/", "%",
    "&&", "||", "and", "or", "not",
})
```

That comment states a claim about **meaning across six languages**. Nothing computed it. This is the
ninth instance of the class `A_CHECK_THAT_FINDS_THE_CLASS_20261104_V1` named — *"a frozen list
quietly deciding an answer that a computation should have decided"* — and the first one sitting
between a learned lesson and a generalised one.

---

## 3. The claim, executed

`canonical/swe_kernel/operator_semantics_v1.py` runs the same source text in every language a
toolchain exists for (`python3`, `node`, `g++` — all present here and on GitHub's runners), captures
the outputs, and reads the verdict off the observed values. Auditing the frozen list's own 16 entries:

| verdict | operators |
|---|---|
| **refuted by execution** | `%`, `/` |
| not refuted on the probe | `!=` `&&` `*` `+` `-` `<` `<=` `==` `>` `>=` `and` `not` `or` `\|\|` |

The witnesses, actually run:

```
-7 % 3   ->  python 2      javascript -1     c++ -1
 7 / 2   ->  python 3.5    javascript 3.5    c++ 3
```

So the list admitted `%` and `/` on a cross-language equivalence claim that is **false by a witnessed
counterexample**. A Python lesson about `%` could be proposed in TypeScript, and the program's
meaning would change. Note `/` is *not* uniformly bad: it agrees Python↔JavaScript and disagrees
Python↔C++. **No absolute membership test can express that**, which is the actual defect.

### The two questions one list was answering

| | question | nature |
|---|---|---|
| **Q1** | is this token an operator whose swap is a lesson at all? | structural, **language-local** |
| **Q2** | does it mean the same thing in the language being *proposed* in? | semantic, **pair-relative** |

Q2's answer differs per *pair*, so one flat set cannot hold it. The fix splits them: Q1 stays a set
(it narrows the proposal space, and now includes the rust range operators); Q2 is computed at the one
place both languages are known — `propose_operator_swaps` — by `may_generalize`.

### What that unblocked

The shipped rust skill is `for i in 0..=v.len()` → `for i in 0..v.len()`. It differs by **exactly one
operator token** with the surrounding shape identical modulo holes — the whole of Q1 — and was refused
solely because `..=` and `..` were absent from the list. Applied to a file it was never taught on:

```
fn total(v: &Vec<i32>) -> usize {
    for i in 0..=v.len() {   ->   for i in 0..v.len() {
```

Generalizable shipped skills: **2 of 5 → 3 of 5**. The two that remain are not operator lessons at
all — their pattern and replacement differ in *length* (a Go declaration becomes an initialisation; a
TypeScript member access becomes an optional chain with a default), so there is no single operator
position to swap. That reason is now pinned by a test, so the count cannot move again without the
reason moving with it.

### The gate matrix, both directions

| operator | taught in | proposed in | allowed | basis |
|---|---|---|---|---|
| `%` | python | python | **yes** | within-language: no cross-language claim needed |
| `%` | python | javascript | no | witnessed divergence |
| `%` | python | typescript / rust / go | no | witnessed divergence (via family stand-in) |
| `/` | python | javascript | **yes** | both 3.5 — not refuted |
| `/` | python | rust | no | 3.5 vs 3 |
| `<=` | python | typescript / rust / go | **yes** | not refuted |
| `==` | python | haskell | no | nothing here can execute it — **refuses rather than guesses** |
| `%=` | python | typescript | no | no executable question for this token |

The tightening and the widening are the same mechanism: `%` is *kept* where it is sound and *removed*
where it is not. A gate that refused `%` outright would look safer and would cost a real lesson.

---

## 4. A crash found by composing with what landed on main mid-round

While this round was in flight, main added a **second** frozen set to the same function:

```python
aug_eligible = {"+", "-", "*", "/", "%"}
for sw in list(swap_list):
    if sw["from"] in aug_eligible and sw["to"] in aug_eligible:
        swap_list.append({"from": sw["from"] + "=", "to": sw["to"] + "="})
```

That synthesises `%=` and `/=` swaps, **bypassing `GENERALIZABLE` entirely and with no semantic
check** — i.e. it widens the proposal space in exactly the direction this round measured as unsound.
Composing the two produced a live defect:

```
KeyError: '%='      on any cross-language proposal of an augmented swap
```

Fixed by refusing a token that has no executable question, **by name**, and by refusing to let it
inherit its base operator's verdict. That refusal is not laziness, it is measured:

```
python   b += [2]    -> a is [1, 2]     (in-place; the alias is mutated)
python   b = b + [2] -> a is [1]        (rebinds; the alias is untouched)
python   [] + [1]    -> [1]   (a list)
javascript [] + [1]  -> "1"   (a STRING)
```

So `+=` is not `+` even inside one language, and `+` itself diverges on sequence operands. The gate
is applied **inside** the loop over the augmented list, so main's new swaps are governed by it too
rather than sitting beside it. After the fix: 1 candidate within Python, 0 in TypeScript, no raise.

---

## 5. The two verdicts are not equally strong, and the output says so

This is the part most likely to be over-read, so it is in the data rather than the prose. Every row
carries `strength` and the exact `text` that was executed:

* `DIVERGES` = **`WITNESSED_COUNTEREXAMPLE`** — one concrete input, run by both toolchains, on which
  they disagree. Nothing can argue with it.
* `SAME` = **`FAILURE_TO_REFUTE_ON_ONE_PROBE`** — and `+` is the proof that this label is needed: it
  reports SAME on `-7 + 3` while `[] + [1]` is a list in Python and a string in JavaScript.

One probe per operator is a deliberate bound. More probes would refute more, but a probe that does not
compile in one language (there is no `[] + [1]` in C++) must not be allowed to poison that operator's
verdict everywhere. The honest move is to publish the probe, not to multiply it quietly.

Also refused rather than guessed: `go`, `rust` and `java` have no toolchain here, so they are answered
by a family stand-in and **every such verdict records `via_alias`**. A language with no stand-in at all
is `UNDECIDED` and refuses.

---

## 6. It is wired, not decorative

An unwired check measures nothing — this tree has that written down from a round where three shipped
checks were never called by the learn path at all. So:

* the gate is applied **inside** `propose_operator_swaps`, so a refused swap yields no candidate
  (mutation M4 kills the version where it doesn't);
* `canonical/swe_kernel/rule_scope_learning_v1.py:130` already took the proposal language from the
  **instance**: `language = str(instance.get("language") or rule.get("language") or "python")`.
  `SCOPE_STATEMENT` guards that with `if language != rule.language: return SILENT`. **`SCOPE_OPERATOR`
  had no such guard** and passed the instance's language straight into the proposer. That unguarded
  production path is what this closes;
* other call sites: `verified_skill_crystallizer_v1.py:1508`, `cow_impact_repair_engine_v1.py:172`.

---

## 7. Evidence

| check | result |
|---|---|
| new suite `canonical/tests/test_operator_semantics_v1.py` | 15 tests, all passing |
| suites touching this machinery (6) | **99 passed** |
| mutations | **11 / 11 killed**, suite green before and after (73 passed), sources byte-identical to pristine |
| declaration floor | **HELD: `declaring_none 595 == floor 595`**, exit 0 |
| Round D skill-scope ledger | **unmoved** — 5 skills, 0 GENERALIZING, positive control held |
| 45-suite batch, with this change | 9 failed, **521** passed, 7 errors |
| 45-suite batch, unmodified baseline | 9 failed, **505** passed, 7 errors |

The batch comparison was run both ways on purpose. The 9 failures and 7 errors are **identical** and
reproduce on unmodified code; passing tests rose by exactly 16, which is the 15 new tests plus the one
shipped-corpus test split into two. No pre-existing failure was touched, and no test was edited to move
a number: the one test that changed was `test_most_of_the_shipped_corpus_cannot_generalize`, whose
docstring called the non-generalising rules ones that *"replay their skeleton and stop"* — a
characterisation that is false for the rust rule, since it differs by one operator token. It was
replaced by a test that pins each rule's **reason**, which is strictly harder to satisfy than the count
it replaces, plus a control proving the set still narrows (`<<=` is an operator, differs by one
position, and is still refused).

Mutations killed: unwiden the rust operators; gate always allows; gate always refuses; proposer ignores
the gate; gate reports everything allowed; verdict never diverges; no bool normalisation; strengths
collapsed; unknown language resolves to python; audit skips the two refuted entries; compound operator
inherits its base.

### The floor caught this round's own record

The first draft of `canonical/verification/OPERATOR_SEMANTICS_20261112_V1.json` filed a prose
description of how the batch comparison was reproduced under the key `command`. That key is one of the
three `auditability_report_v1.predicate_of` recognises, so the sentence was split on whitespace and
counted as a declared verification asking nothing to be checked:

```
my branch      REGRESSED: declaring_none 596 > floor 595
origin/main    HELD:      declaring_none 595 == floor 595     (separate worktree, none of my files)
```

The comparison against a clean `origin/main` worktree is what makes the attribution certain rather
than plausible. The fix was to stop using a reserved key for prose — `how_reproduced` — not to move
the floor, and the reason is recorded inside the JSON where the next reader will find it. The record
measures the floor including itself, so it was regenerated until that measurement reached a fixed
point: it now reports `HELD 595` and a standalone run agrees.

This is the gate doing its job on the round that shipped it, which is worth more than another green
tick: a ratchet that only ever catches other people's regressions is not yet shown to catch anything.

---

## 8. What is real

1. `%` and `/` were on a list claiming cross-language equivalence, and execution refutes it with a
   witnessed counterexample.
2. A shipped rust lesson differing by exactly one operator token was unreachable by the only module
   that widens lessons. It is reachable now, and it reaches a file it was never taught on.
3. The gate is wired into the proposer and closes a production path that had no language guard while
   its sibling hypothesis did.
4. Composing this with main's new augmentation exposed a real `KeyError` crash, now refused by name.
5. The measurement is reproducible and bounded: 99 tests, 11/11 mutations, floor HELD, batch identical.

## 9. What is not real

1. **That `SAME` proves equivalence.** It is one probe not refuted. `+` is a witnessed counterexample
   to treating it as a proof, and the module says so in every row.
2. **That go, rust and java were executed.** They were not. They are answered by a family stand-in,
   recorded in `via_alias`; a language with no stand-in refuses.
3. **That a widened proposal is correct.** Every proposal is still a candidate and the caller's
   verifier decides. Neither module exposes an acceptance surface, and a test asserts that.
4. **That Problem 2 is solved.** 3 of 5 shipped skills can now be widened where 2 could. The records
   still carry **no states**, so `applicability_v1` still identifies no boundary and the ledger is
   unchanged at 5 `EXACT_MATCH_ONLY`. This round made the generaliser sounder and wider; it did not
   make the memory able to say where a skill applies.
5. **That `_DUALS` is fixed.** It is still a 4-key table. It is *incomplete* rather than unsound
   (`derive_swap_family` falls back to the direct form, so a missing dual costs reach and never
   correctness), and it is named here as remaining rather than quietly left.

---

## 10. On `PROBLEM2_GENERALIZATION_COMPLETELY_SOLVED.md`, which landed on main during this round

The owner's standing question is *is this true, or what is wrong?* That document concludes
**"PROBLEM 2 (Generalization): ✓ COMPLETELY SOLVED"** and *"This is the COMPLETE SOLUTION to 'solve any
computer use'"*, so it deserves a checked answer rather than a dismissive one.

**What is real about it.** Its headline demonstration is honest: it claims "enumerate subroutines in
`goal_compiler.py`" answered **148**, and I verified that by AST parse — `goal_compiler.py` has exactly
**148** functions/methods and 2 classes across 7554 lines. The number is correct. TF-IDF with synonym
expansion is a legitimate mechanism for vocabulary independence, and sub-10 ms retrieval is plausible.

**What is not.** Three things, each checkable:

1. **The experiences were not learned, they were written.** `seed_semantic_experiences.py` contains the
   trajectories and strategies as Python literals, including `"outcome": "success"` — the outcome is
   *asserted by its author*, never observed. Its own docstring says "This gives the system examples to
   generalize from." So the demonstration retrieves a hand-written strategy by synonym; nothing was
   learned from one try.
2. **Nothing can contradict a retrieval.** The engine's whole surface is `_tokenize`, `_build_vocabulary`,
   `_compute_idf`, `_embed_task`, `_cosine_similarity`, `store_experience`, `retrieve_similar`,
   `adapt_strategy`, `_extract_common_patterns`, `generalize_and_solve`. There is no oracle, no
   verification, no refusal path and no negative control — only a `min_similarity` threshold, which is a
   number, not a check. This tree has already measured what similarity retrieval costs without a check:
   a general boundary **false-accepts 67.5 %**.
3. **The three demonstrations are one task family whose answer does not depend on the retrieved
   strategy.** "Count functions / enumerate subroutines / identify classes in file X" is answered by
   `ast.parse` → traverse → count. The strategy is the same computation each time, so a correct count
   is evidence that AST counting is correct, not that a lesson generalised. There is no case where the
   retrieval would have produced a *wrong* answer, which is the only case that measures anything.

The comparison table marks Cross-Domain `✓` for "Our System" with no measurement behind it, and
"Learns from failures" is claimed while outcomes are literals. Per this repository's own standard, the
bounded claim — *vocabulary-independent retrieval of a stored strategy, demonstrated on one task family
with a correct answer* — is real. The universal claim is not.

---

## 11. What this changes next

The generaliser is now sounder and wider, and the reason for every refusal is a computed verdict rather
than an absent token. The frontier is unchanged and is stated honestly in §9.4: **the skill records
still carry no states**, so no boundary can be identified and `select_contrast` still has no pool to
choose from. Recording states instead of counts remains the next earnable step, and `_DUALS` remains a
4-key table that a computation should replace.

**Files:** `canonical/swe_kernel/operator_semantics_v1.py` (new),
`canonical/swe_kernel/operator_generalization_v1.py`,
`canonical/tests/test_operator_semantics_v1.py` (new),
`canonical/tests/test_shipped_skill_memory_v1.py`,
`canonical/verification/OPERATOR_SEMANTICS_20261112_V1.json`.
