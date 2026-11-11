# The optimal path to "literally anything on a computer"

Stated goal: solve any computer use, including advanced software engineering, by the fastest
and most optimal mechanism available. This page is the first-principles answer, with every
number measured or cited.

## The decomposition

Any system that does "anything on a computer" needs six parts. This project has one.

| part | what it does | have it? | evidence |
|---|---|---|---|
| **1. Carrier** | execute an action on the machine | **YES** | argv exec, no shell, confined (r53) |
| **2. Contract gate** | refuse when the pre/postcondition fails | **YES** | 3/3 wrong picks caught (r60) |
| **3. Memory** | keep what worked, permanently | **YES** | sqlite, exact undo (r59) |
| **4. Model** | read a novel screen or codebase and decide | **NO** | 0 parameters |
| **5. Actuator** | pixels, pointer, browser | **NO** | no display, no pointer in this runtime |
| **6. Planner** | decompose a goal into steps | **NO** | composition returns None (r51) |

Parts 1-3 are done and are the *easy* parts, and the industry mostly does them badly. Parts
4-6 are the hard parts, and no amount of work on 1-3 produces them.

## What the fastest correct path actually is

**Do not build 4. Attach one. Build the gate that makes attaching it safe.**

That is not a shortcut around the hard part; it is the only arrangement in 2026 where the
hard part is honest about its failures. The measured argument:

    model proposes skill -> carrier executes it -> contract + shape gate verifies it

    WRONG wc -l     for "unique lines of"    -> SHAPE_MISMATCH  (caught)
    WRONG cat       for "sha256 of"          -> SHAPE_MISMATCH  (caught)
    WRONG sort -u   for "count the lines of" -> SHAPE_MISMATCH  (caught)

3 of 3 type-changing wrong picks caught, with no model attached, because the gate is a
property of the contract layer.

This is the architecture the field converged on independently. **ToolGate** (Findings of ACL
2026) is the same shape: Hoare-style pre/postconditions per tool, precondition gates
invocation, postcondition decides whether the result may be committed, and the symbolic state
"evolves only through verified tool executions, preventing invalid or hallucinated results
from corrupting the world representation." Its most prevalent reported failure is parametric
hallucination at 8.4% -- which is exactly what a gate is for. **Predefined-tool execution**
(EMNLP 2026 Industry) proves the hallucination-suppression property under its assumptions
across 276 agent executions. **SIGIL** (2026) adds a verified loader at 0.495 ms.

## The one error the gate cannot catch, stated plainly

A wrong pick between two operations that return the **same kind** of answer. Asking for
unique lines and getting `sort` instead of `sort -u` returns lines; the shape gate is
satisfied; the answer is wrong. Measured and pinned.

Consequence: **the model must never be the only decider.** The arrangement that survives is
model-proposes / gate-disposes / ambiguity-asks, and the ask path already exists (r55-r58).

## The order of work that minimises wasted effort

1. **Attach a model to `answer_or_ask`'s selection step only.** It replaces the cue table.
   Everything downstream already verifies. Expected gain: the 4/8 and the 7/8-tie ceiling
   collapse, because a model can map a paraphrase onto a taught operation.
2. **Widen the gate from kinds to operations.** The same-kind hole is the remaining silent
   failure. This is a contract-schema change, not a model change.
3. **Actuator last.** GUI is not blocked by a missing demonstration; it is blocked by
   grounding, and 2026 reports 0-10% success on unseen UIs and a drop from 26.3% to 8-10%
   after fine-tuning on 22.5K human trajectories. Attaching a model to a headless box buys
   nothing.
4. **Coding is step 1 plus files.** It does not need a separate mechanism; it needs the model
   from step 1 and a workspace. Today: 0.

## What is not on this path

- Teaching more operations. Measured destructive (r52, r57).
- Widening the cue table. Provably cannot beat the tie ceiling (r55).
- Claiming the substrate is learning. It files (r59).

## The honest sentence

**The revolutionary thing here is not a learner. It is a gate.** A model with a gate around
it is defensibly useful; a model without one is a guess with a receipt. This repository
already has the gate, and the next correct move is to put a model behind it -- not to keep
measuring the gate.
