# First principles, pass twenty — the frame, not the table, is what needed changing

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

You asked the same question a third time. Each time the answer was one level deeper, and this pass I
think it reached the bottom of what is wrong.

## 1. Three levels of the same fault

**Level 1 (passes 1-18):** four authored tables, one per failure class. I write the rules.

**Level 2 (pass nineteen):** I replaced the tables with interpretation — derive the edit from the
measurement instead of from my list. Strictly better: cold start works, constants are impossible, it
generalises across function names. But the *shape* was still mine: "the defect is an operator, and it
should have been a different operator." An index failure walked straight past it, as I predicted.

**Level 3 (this pass):** the fault above both of them. Look at what the loop actually does:

    failure text -> authored classifier (what kinds exist?)
                 -> authored patterns  (how do I recognise them?)
                 -> authored prior    (which producer first?)
                 -> NINE authored producers, fixed order
                 -> screen by execution, keep the winner, DISCARD THE REST

Adding a tenth producer — which is exactly what "extend it to indexing" means — makes the system
**more** static. Every pass so far has been adding to that list while claiming to make it less static.
That was the real contradiction, and you kept pointing at it.

## 2. What was actually missing

Not another hypothesis. The machinery to hold hypotheses and fit them.

The screen executes *every* candidate and the loop read only the winner. Every rejection — the larger
half of everything measured — was thrown away. So the system could only ever learn from successes, which
is why it needed a prior success to learn anything at all (the habit mechanism's fatal limit).

`synthesized_edit_grammar_v1` — keeps the whole screen:

* the hypothesis space is a grammar: `root × argument index × transformation × operator`, plus a
  subscript shape. Not a list of edits.
* each hypothesis predicts its own effect and is **refuted offline** when the prediction is wrong. No
  probe, no subprocess, no budget. The nine producers emit 100% of what they generate and let the screen
  decide; this one discards most of its own candidates before anyone runs anything.
* every screened candidate — pass *or* rejection — updates the fit, and the fit is what orders the next
  proposal.

## 3. The measurement that settles whether it is a learner or a table

Same code. Same binary. Only the store differs.

| world needing | cold ranking of the winning shape | after fitting | proposed cold | proposed fitted |
|---|---|---|---|---|
| `a[0]` -> `a[1]` | 122 / 248 | **1 / 248** | `a[-2]` (wrong) | `a[1]` (**right**) |
| `a - b` -> `a / b` | 7 / 248 | 2 / 248 | correct | correct |
| `a + a` -> `a + b` | 5 / 248 | 8 / 248 | correct | correct |
| `a + b` -> `a * b` | 3 / 248 | 6 / 248 | correct | correct |

Capability changed with no code change, from data the creature collected itself. That is the only
version of "not static" I can defend, and it is the first time in twenty passes I have been able to
produce it in a table.

Active vs control, one world per process, all nine producers and habits silenced:

| world | grammar ON | grammar removed |
|---|---|---|
| index `a[0]`->`a[1]` | SOLVED | FAILED |
| arith `a-b`->`a/b` | SOLVED | FAILED |
| arith `a+b`->`a**b` | SOLVED | FAILED |
| operand `a+a`->`a+b` | SOLVED | FAILED |
| index `a[0]`->`a[-1]` | FAILED (not derivable from the measurement) | FAILED |
| bool `a<b`->`a>=b` | FAILED (outside the grammar) | FAILED |

## 4. Four defects in my own new code, none found by reading it

1. **`_pick("whole")` returned the `Return`, not its value.** Every candidate ever offered had
   `signature() == None`, so `observe()` counted nothing: the "learner" was a fixed table with a
   learning interface bolted on. The tell was `tracked: 0` after six observations.
2. **The information-preservation check subtracted parameters.** In `def f(a, b): return a[0]` the only
   name the body reads *is* a parameter, so the requirement emptied itself and `b & b` — an expression
   that deletes `a` — passed the check written to stop exactly that. And `b & b` also passes the
   generalisation gate, because its output moves when `b` moves. Nothing downstream would have caught
   it. A repair may not stop reading what the original read.
3. **Proposer and predictor disagreed, twice, in opposite directions** — subscripts inside larger
   expressions, and negative indices. Each time a correct hypothesis was scored right and then never
   emitted. A predictor that disagrees with its own proposer is worse than no predictor.
4. **A control that stubs the factory leaves the mechanism running.** Third time in this series.

The pattern is stable enough to state: the artefact has been right and my account of it wrong, roughly
ten times to zero the other way. What works is refusing the story — silencing every producer, running
one world per process, and printing what the code actually did instead of what I expected.

## 5. What is still authored, and what is still static

The **grammar's shape** is mine. `A op V`, `A + 1`, `A[-1]` are decisions I made about what an edit can
look like. Only the choice among them is learned. A different shape explores a different family — that
limit does not go away by calling the thing a learner.

Still outside it entirely: multi-statement defects, wrong control flow, an edit spanning two functions,
anything where the evidence is not an argument tuple. Those still fall to the nine producers, and a cold
creature facing them still repairs nothing without me.

## 6. Next falsifier

**S21.** Give the grammar a *second* hypothesis shape it was not designed around — say, changing a
comparison operator to a negation of itself, or swapping the two operands — and require it to discover
from screened evidence that the new shape is the one that works, with the shape's own parameters absent
from my code. Prediction to falsify: it will need me to add the shape by hand, because the grammar has
no operation that *invents* a shape. If that holds, then the honest claim is that the creature learns
*within* a space I author, and the next real problem is how a space gets extended without me — which is
a different and much harder question than anything in this document.
