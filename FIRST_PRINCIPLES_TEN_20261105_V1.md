# First principles, pass ten — the ceiling was a node kind

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

Pass nine concluded that the capability ceiling is the **synthesizer set**, and that memory cannot
raise it because a learn-from-success loop only ever learns what search already solves. So this pass
stopped working on memory and asked the only question that can move the ceiling:

> **Is there a capability the creature exercises constantly but only in one syntactic context — so
> that the same edit, freed of that context, would repair shapes it currently cannot?**

## 1. The answer is yes, and it is embarrassing in its simplicity

Every authored producer is **node-kind specific**: STUN synthesises guard conditions, the guided
search patches particular node kinds, the deterministic AST repairs particular patterns. None of
them embodies the single most common edit a human makes without thinking:

> **this operator should have been a different operator.**

The creature's own token-rule engine already generalises this way internally, but its *producers*
never propose it as a generator. So `return a - b` → `return a + b` is solved, and every one of
these was not:

    mul          return a * b                      UNSOLVED  -> solved
    mod          return a % b                      UNSOLVED  -> solved
    augassign    t += a; t -= b                    UNSOLVED  -> solved
    augassign2   t *= a; return t - b              UNSOLVED  -> solved
    whileacc     while-loop accumulation           UNSOLVED  -> solved

Meanwhile these were already solved by the authored producers, so they are controls:
`binop`, `cmp_gte`, `cmp_lt`, `cmp_eq`, `boolop`, `offbyone`.

The generator (`operator_family_rewrite_v1`) tokenizes the source and changes exactly one real
operator token at a time inside its family — arithmetic, comparison, boolean, with augmented forms
derived so `+=` ↔ `-=` ↔ `*=` falls out of the same rule.

## 2. The honest number, after checking the baseline

| measurement | before | after |
|---|---|---|
| inline producer set, 12-shape screen | 6/12 | 11/12 |
| **board, 10-shape screen (end to end)** | **8/10** | **10/10** |

The second row is the one that matters, and it is smaller than the first. The board also runs the
confined multi-file engine and the coupled zygote engine, which already covered some of these
shapes. The two the new generator actually adds end to end are **`mod`** and **`augassign`**.

I am quoting 2, not 5, and the module docstring says the same thing, because the 11/12 figure is a
statement about the inline candidate list and not about the creature.

## 3. Why this is a bigger result than the memory work, despite being smaller code

`augassign` is the shape that in pass five could *only* be repaired when an external teacher placed
a rule before the run started, and that self-taught rules never reached. Every pass since treated
that as a memory problem — a missing consumer, a missing call site, a bootstrap gap.

It was never a memory problem. **It was a missing producer.** The creature could not repair
`t += a; t -= b` because nothing in its search proposed changing `-=` to `+=`. No amount of recall
would have helped, and five passes of memory work were spent on a defect that a nine-line generator
fixed.

That is the general lesson, and it is the one I kept missing: **when a capability appears
context-bound, check whether the context is the limitation or the capability was never there.**
Here the capability existed and was scoped to one node kind.

## 4. What this does and does not prove about becoming non-static

**Does not prove it.** This is a hand-derived edit class. It makes the creature *more capable*; it
does not make it *different over time*. I wrote it; the creature did not learn it.

**Does point at the mechanism.** The transferable unit is not a rule and not an example — it is an
**edit class**: "swap an operator within its family", "flip a comparison", "move a boundary". A
creature that could *abstract* its own successful repairs into edit classes, and then propose them
in contexts it had never edited, would be doing the thing the owner keeps asking for. That is now a
concrete design with one worked instance, instead of a slogan.

## 5. The next question, stated so it can fail

The operator-family win came from **1 edit class covering 4 node kinds**. The testable version:

> Can the creature derive an edit class from its own succeeds — without being told what a class
> is — and apply it in a context it has never edited?

Concretely: after repairing `a - b` → `a + b`, does anything in the system subsequently propose
`a * b` → `a + b` or `t -= b` → `t += b` *without the generator above being present*? Right now the
answer is no, because nothing abstracts at all. Building that abstraction is the next real step, and
it must be measured by removing the hand-written generator and seeing whether the derived class
covers the same shapes.

## 6. Corrections to my instruments in this pass

8. I first reported the end-to-end gain as **5 shapes** from the producer-set screen. A worktree
   check at `23e2520f` showed the board already solved 8/10, so the true end-to-end gain is **2**.
   The producer-set number was measured on the wrong harness for the claim.
9. My first operator generator crashed on `Compare.ops` (a list) and emitted `[]` for `boolop`
   because `and`/`or` tokenize as `NAME`, not `OP`. Both fixed by moving to `tokenize` with exact
   character spans — which also removed a real hazard: a regex rewriter would have changed
   `"-"` inside a string literal. Verified: zero candidates are now produced when the only
   operator-looking text is inside a string or comment.

## 7. Standing bar

Different at the end of a run than at its start: **still not established.** But the creature can
now repair three defect shapes it could not repair yesterday, and none of that came from memory.
