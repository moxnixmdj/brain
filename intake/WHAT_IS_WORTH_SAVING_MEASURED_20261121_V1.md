# What is worth saving, measured

**Date:** 2026-11-21
**Status:** an answer to the user's question, with numbers. It rules out the obvious option.

## The question, exactly

> "should he be goal-directed and save the important learning? The saving in the memory must not
> be only his action because his actions probably will never be needed again... Saving his exact
> experience must be in a very sufficient way, not just saving the exact experience in a dumb
> way. Maybe we should do generalization."

Two options were on the table: **replay the exact experience**, or **save a generalized form**.

## The experiment

Every ceiling-achievable item in a library, in turn, treated as the ONE experience. Memory built
two ways. Applied to every OTHER item in the same library, judged by that item's own hidden test.

* **DUMB** -- replay the saved body with identifiers renamed to the target's parameters.
* **GENERAL** -- lift the saved body's identifiers into slots, refill from the target's stub.

Zero hand-solving, zero model calls, 288 trials.

## Result

    DUMB     8/288  =  2.8%
    GENERAL  0/288  =  0.0%

Both are near-worthless, and **the second one is worthless for a different reason than the
first**. Lifting identifiers is not generalization. It carries a body's *variable names* across
and leaves its *structure* behind.

## Why, and it is decisive

    items whose exact callee sequence appears more than once in their library:  22 / 170

Of the pairs that do collide, they are the same call with a different literal
(`np.convolve(..., mode="full")` vs `mode="valid"`).

**An item's answer is almost never another item's answer.** So a memory of answers — however
cleverly factored — has almost nothing to apply. This is the user's own intuition
("his actions probably will never be needed again") and it is correct.

## The contradiction this exposes

The system already works this way, and it works *far* better than any answer-replay:

| how the answer is obtained | items |
|---|---|
| stored answer, replayed or generalized | 8 / 288 |
| derived at use time from the artifact's own text | **82 / 193** |

The 82 are not retrieved. They are **computed** from the goal, the stub, the artifact's
docstrings and the artifact's signatures, with the item's own test as the arbiter. What persists
between items is not a body — it is *how to ask*.

## So what IS worth saving

Not "the answer" and not "the shape". The evidence from this whole session points at one thing,
and it is the user's word, not mine:

**the question.**

The mechanisms that produced every gain this session are questions with computable answers:

    which spelling did the stub actually bind?          alias_map
    which slots does the callee declare?                inspect.signature
    which artifact does this goal describe?              doc_match_symbols
    what does this module expose?                       the artifact's __all__
    does this body satisfy the item's own test?         the oracle

Every one of those is a **procedure**, and every one transferred unchanged across libraries.
`doc_match_symbols` was written once and paid on numpy, scipy, sympy, nltk and plotly.

A stored answer is a fact about one item. A stored **question** is a capability that applies to
every item that ever has a docstring, which is all of them. That is precisely the conclusion
this project had already reached for shell programs
(`ask_the_host_the_right_question_v1.py`), and it now holds for software engineering with 82
items behind it.

## What this does NOT yet settle

Saving the *question* is still saving something. The open question is whether the five
procedures above should become **data the system can add to, inspect and remove** -- which is
the user's "generalized memory" -- or whether the right answer is that they are five fixed
procedures and the memory is genuinely nearly empty ("the best part is no part").

That is the next measurement, and it is not answered here.

## Not claimed

* 2.8% and 0.0% are measured on this benchmark's items, one experience at a time.
* The 82/193 is the score on the 193 no-dependency items, in the environment as installed.
* `truth.achieved` remains **false**. Authority remains **NONE**.
