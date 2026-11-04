# First principles, pass twenty-three — the deletion I predicted, and the deletion I refused

Date: 2026-11-05. Authority: NONE. Spend: $0. `truth.achieved`: false.

## 1. The counting that should have happened twenty passes ago

Every producer's output was tagged, and one process per shape ran the whole board. Which tool first
produced the passing candidate:

| tool | shapes won |
|---|---|
| `interpretive` | mul, mod, floordiv, augassign2, binop |
| `operator_family` | augassign, whileacc, boolop, offbyone, compreh |
| the other seven | **0 of 10, while producing candidates on all ten** |

The "nine producers" architecture is two producers and seven that generate work for the screen to
reject. Last pass I wrote that as a suspicion. This pass it is a count.

## 2. The deletion test

| configuration | board | candidates screened |
|---|---|---|
| all nine producers | 10/10 | 162 |
| only the two winners | 10/10 | 78 (**−52%**) |
| thin ambient stack | 10/10 | 83 (−49%) |

That looks like a mandate to delete seven modules. **It is not, and this is the important part of the
pass.** Worlds the board never tests:

| world | full | pruned |
|---|---|---|
| binding typo (`NameError`) | SOLVED | **FAILED** |
| missing colon (`SyntaxError`) | SOLVED | **FAILED** |

The producers that never win a board shape are the only ones that repair binding and syntax failures.
They are not overhead; they serve failure *kinds* the board does not contain.

> A uniform benchmark makes uniform-looking conclusions. The board has ten VALUE shapes and zero of
> anything else, so "seven producers are useless" was a true statement about the board and a false one
> about the system.

Deleting them on the strength of the best measurement in twenty-three passes would have been the worst
decision in twenty-three passes. The measurement was not wrong. The scope of the claim was.

## 3. What I did instead — per-kind pruning

`should_consult(kind, tool)` declines a tool for a kind only when it has appeared at least four times
there **and** either never produced a candidate or never won one. Per kind is the whole point:

* VALUE loses eight tools — none of them has ever won a VALUE repair
* BINDING and SYNTAX lose **none** — their producers do win there

| configuration | screened | board | binding | syntax |
|---|---|---|---|---|
| cold | 162 | 8/8 | SOLVED | SOLVED |
| per-kind competence learned | **83** | 8/8 | SOLVED | SOLVED |

Half the screening, nothing lost, nothing deleted. That is a real improvement in the thing this system
actually pays for — probes — produced by measurement rather than by adding a tenth mechanism.

## 4. Why this one is different from the previous twenty-two

For the first time the change was **subtraction driven by evidence**, and it came from the creature's
own record of what it had done, not from my belief about what should work. And the subtraction survived
a control that the previous pass's addition did not: it changed cost without changing capability,
whereas the competence *ordering* changed nothing at all.

It is also the first time a measurement nearly cost a capability, and the reason it did not is that I
tested outside the benchmark instead of congratulating myself inside it.

## 5. The honest ledger for twenty-three passes

| what changed | measured effect |
|---|---|
| four authored tables → interpretation (pass 19) | 8 cold repairs, 0 with it removed |
| interpretation → fitted edit grammar (pass 20) | rank of winning shape 122 → 1 from own rejected data |
| grammar → hole detection (pass 21) | names `BinOp->IfExp` on 3rd process; acts on nothing |
| competence ordering (pass 22) | **zero** measured effect on cost or capability |
| per-kind pruning (pass 23) | **−49% probes**, capability unchanged |

One real efficiency gain in twenty-three passes, and it was a deletion. Everything else was knowledge
the system holds about itself, which is a precondition for intelligence and not an instance of it.

## 6. Next falsifier

**S28.** The per-kind skip is the first thing here that pays, so the honest question is whether it
*pays more the longer it runs*, or saturates. Run sixty distinct failures across mixed kinds, record
screened-per-repair after every ten, and see whether the curve falls, flattens, or — the outcome that
would refute me — rises, because early skips cut off the tool that would have won later.

Prediction to falsify: it will flatten quickly at around half the cold cost, because the skip only
removes tools that never win and there is a floor of work the two winners always do. If instead it
keeps falling, that means something in the system is still learning per-failure, which would be a
better result than any pass so far.
