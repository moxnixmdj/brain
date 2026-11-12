# One lesson buys a word, not an operator

**2026-11-12.** Base `6ac2a539`. Branch `arena/413458f8-brain`. Round 8.

The mechanism has been in this repository the whole time, under a name nobody would guess:
`canonical/runtime/taught_words_v1.py`, registered as **`file.question.taught_words.v1`**. It is the
only capability in the 145 whose acceptance predicate is `taught_program_recomputed` — the only one
that does not accept on a written file, but re-runs the thing it learned and compares.

This round runs it, teaches it **one lesson**, and measures what that one experience bought.

```
words added to the lexicon by one lesson              1
requests nobody showed that it can now answer        12
...answered correctly                                11
...answered wrongly                                   0
...refused, and the refusal names the word            1
a composition nobody showed is answered correctly  True
operators added by the lesson                         0
operator parts that were already there               14
```

The lesson was one sentence — *"how many records are in t.txt"* — with two example files. It taught
one word. Then, with no further teaching:

| request nobody showed | answer |
|---|---|
| how many unique records are in t.txt | 18 ✓ |
| how many blank records are in t.txt | 4 ✓ |
| how many records contain ERROR in t.txt | 10 ✓ |
| what is the length of the longest records in t.txt | 48 ✓ |
| count the records in t.txt | 25 ✓ |

`unique` was learned in a different lesson. `records` was learned in this one. They compose, in a
sentence that was never shown, correctly. That is the owner's thesis working, in his own tree, today.

Authority **NONE**. Runs the shipped learner in-process, against its own seed lessons plus one live
lesson written to a temporary directory. Writes nothing into the repository, starts no process, $0,
zero model dependency.

---

## 1. Why one lesson is enough — and what that reason actually is

It is tempting to read the table above as "the learner generalised from one example". It is not
what happened, and the difference decides the whole question.

A lesson is one sentence plus two files plus the right answers. **The sentence's operation is not
given.** The learner enumerates every operation in a fixed algebra — 14 parts: five things to look
at, four filters, one measure, four reducers — keeps those that reproduce the stated answers on
every example, and then attributes parts to words by the smallest lexicon consistent with *all*
lessons. A word counts as known only when every smallest lexicon agrees on it.

So one lesson is enough because **the demonstration is choosing among operations that already
exist**, and because the choice is constrained by everything already known. Two examples suffice
because the algebra is small and shared, not because two examples are magically informative.

The module says it in one line, and it is the most important sentence in the tree:

> *The fifteen parts are built in; only the words are learned.*

(Measured: `len(taught_words_v1.PARTS) == 14`. The docstring says fifteen. Small, real, reported
here, not fixed in this PR.)

## 2. What no number of demonstrations can buy

Ask it something whose operation is not in the algebra:

```
'what is the median number in n.txt'  ->  ok=False  UNKNOWN_WORD:median
```

**Refused — correctly — forever.** There is no `median` part. Ten demonstrations, ten thousand
demonstrations, a thousand environments: the answer does not change, because nothing in the lesson
format can add a part to the algebra. To add one you edit `PARTS`. That is code, not experience.

This is the precise answer to *"why can't we just give the model the most advanced actions, let it
experience each once, and have it learn them permanently?"*:

> **One experience selects a binding among operators you already have. It never creates an operator
> you don't have. The number of things a single lesson can teach you is bounded by the size of your
> built-in operator space — and that space is grown by writing code, not by trying things.**

And the same shape appears in the mechanism on the other side of the tree. `python.patch.search.
test_guided.ast.v1` does not invent a repair either: it enumerates bounded AST mutations and keeps
the one a failing test accepts. A bounded generator plus an independent recomputation. **Both of this
project's working learning mechanisms are selection, not invention** — and both are honest about it.

## 3. Which is why "give it a try everywhere" plateaus

Environments multiply the number of *bindings* available. They do not grow the *operator space*.
Ten thousand new environments, each experienced once, give you ten thousand words for the same
fourteen operations — and a fixed ceiling on what any of them can express.

The measurements from earlier rounds fit this exactly: one demonstration is enough to *carry* a
procedure (14.1/47 programs) and nowhere near enough to *identify* one (10% leader-correct, 0/10
exact), and identification is bought with chosen questions, not with exposure. Identification is the
process of locating a point in the operator space. If the space is small and shared, that is cheap.
If the space is the space of all programs, it is not — which is why the repair loop needs a failing
test to search against, and why the word learner needs two example files per lesson.

The learner here refuses a lesson with **one** example (`TWO_EXAMPLE_FILES_NEEDED`), because — its
own measured reason — one file left two wrong answers out of twelve undetected. Even inside a
fourteen-part algebra, one observation does not pin one word.

## 4. What this says to do next

1. **Treat this module as the reference design, not a curiosity.** It is the only gate in the tree
   that recomputes instead of inspecting, the only one that refuses rather than guesses, and the only
   one whose "I don't know" names the exact word it doesn't know. Two rounds were spent finding that
   the other gates were not like this. The template for fixing them is here.
2. **Grow the operator space deliberately, and pay for it in code.** Every genuinely new capability
   the owner wants — a new computer-use action, a new refactoring, a new query — is a new part, and
   a new part needs: an enumerable form, a way to recompute its result independently, and a refusal
   when the input is outside it. That is the whole design, and it is 500 lines.
3. **Do not spend effort on exposure breadth.** It cannot raise the ceiling. Spend it on
   identification (chosen questions: 100% vs 10% at 2.0 queries) and on recomputable parts.
4. **Fix the one remaining debt** from round 7: `python.task.acceptance.measured.objective.v1` still
   reads `output_verified`, and it leaves `DEFINITE_DEBT` only when it is run against a real receipt.

## 5. Receipts

```
python3 one_lesson_buys_a_word_not_an_operator_probe_20261112.py --list
python3 -m pytest -q canonical/tests/test_one_lesson_buys_a_word_not_an_operator_v1.py    8 passed
```

## 6. Non-claims

One lesson, one word, in a 14-part algebra, on the module's own seed corpus. "Answered correctly" is
judged against the answer the seed lesson already established for the same file and operation, not
against an independent oracle. Nothing here demonstrates that the learner would behave the same with
a larger operator space, and nothing here is a claim about models, sentience, or general computer
use. No capability registered, no lexicon written to the tree, no operator added, `truth.achieved`
false, $0, zero model dependency.
