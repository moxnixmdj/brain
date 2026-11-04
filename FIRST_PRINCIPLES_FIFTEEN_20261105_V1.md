# First principles, pass fifteen — the last hole, and the oracle defect hiding under it

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

## 1. S10: SYNTAX, the hardest of the three

`SYNTAX` was the last failure kind no producer could touch, and it is hardest for a structural reason
rather than a coding one: **every repair in this project is authorised by running the owed test**, and
a file that does not parse cannot be run. The oracle is unavailable exactly where the repair is
needed.

So verification had to be two-stage, and the order is the whole of the honesty:

1. `ast.parse` must succeed — a **precondition**, never a repair
2. the candidate must then pass the owed test, through the normal screen and the normal gate

A candidate that only parses is not a repair and is never reported as one. Nothing here widens an
acceptance rule; it produces candidates a parser will accept so the existing oracle can speak.

| world | BEFORE | AFTER |
|---|---|---|
| missing `:` | unchanged | **REPAIRED** |
| unclosed `(` | unchanged | **REPAIRED** |
| unexpected indent | unchanged | **REPAIRED** |

## 2. What was underneath it

`indent` repaired in a direct screen but not through the creature. The tempting reading — "the
producer is fine, the loop is quirky" — would have been wrong, and chasing it found a defect that had
been corrupting the screen for passes.

**_restore_slot_delta restored overridden files as symlinks, while slots are built with hard links.**
The comment two lines above the slot builder already explains why that matters: a symlink lets
`pathlib.Path(__file__).resolve()` escape back to `/input`, so a test the insert its own parent on
`sys.path` imports the **original** module. Wave 1 was immune because a fresh slot is hard-linked.
Every **rested** slot was poisoned.

Consequence: candidate **7 through 36** of any batch — the majority of the creature's candidate list —
could be scored by the base file's behaviour instead of its own. Measured directly, on a package
world, before the fix:

    candidates 0-5 : correct, each failing with its own value
    candidate  6   : `return a + 1`  ->  reported "seen 2"  ->  scored TEST_FAILED

A verbatim correct fix, silently failed, by a symlink two functions away.

After the fix the same batch returns `[6]`. `indent` repairs 3/3.

## 3. Why this is the most important result in five passes

It is not a new capability. It is a **measurement instrument that was lying**, and it has been lying
since before pass twelve — which means every "the producer cannot do X" conclusion I have written in
this series has to be treated as unproven until re-measured. Two of them were already wrong: the
`BINDING` decline and the `SIGNATURE` decline were both partly this bug reporting a real candidate as
a failure.

The honest summary of passes twelve through fifteen is therefore not "four producers added". It is:

> The system's bottleneck was never the producers. It was that the screen could not say why a
> candidate failed (pass 12), was handed truncated failure text (pass 14), and was testing the wrong
> file for every candidate after the sixth (pass 15).

Four passes of capability work, and the three largest wins were all repairs to **the instrument**.

## 4. Scoreboard, with the caveat now attached

| kind | pass 13 | pass 15 |
|---|---|---|
| VALUE | 7/8 | 7/8 |
| TERMINATION | 1/1 | 1/1 |
| BINDING | 1/1 | 1/1 (re-verify: may be more) |
| SIGNATURE | 0/1 | 1/1 (re-verify: may be more) |
| SYNTAX | 0/1 | **3/3** |

The annotations are the point. Numbers gathered before the symlink fix are not trustworthy, including
numbers I reported confidently yesterday.

## 5. Next falsifier — a re-measurement, not a new feature

**S11.** Re-run every producer screen in this series against the fixed screen, and report the honest
delta: `operator_family` (12 shapes), `derived edit classes` (held-out worlds), `binding`, `signature`,
`syntax`, and the multifile engine. Prediction to be falsified: **at least one producer that appeared
to cover N shapes actually covers more**, because its correct candidates were in slots 6+.

If nothing changes, then the screen bug only ever cost the smaller batch sizes, and the earlier
numbers stand. Either way this is the only responsible next step: I do not get to keep capability
claims measured on an instrument that has since been shown to lie.

## 6. Standing bar

Different at the end than the start, in the way that matters most: not one more producer, but a
screen that tests what it says it tests. The creature repairs worlds in a class it could not touch
this morning — and, more consequentially, every measurement in this project is now being taken with an
instrument that is honest, which changes the value of everything measured before it.
