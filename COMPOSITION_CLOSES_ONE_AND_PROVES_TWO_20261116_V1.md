# Composition closes one and proves two

**Last turn's three refusals were all one shape of failure: the agent had the right effect in its
measured table and still could not reach the goal, because reaching it took two steps or because the
machine has no atom for it. Composing the measured effects fixes the first, and turns the other two
from failures into proofs — 14 of 16 solved, 2 PROVEN impossible, 0 prediction errors, and 15 plans
that met the stated goal and broke something else rejected by a frame condition.**

Date 2026-11-16 · branch `arena/ecf58f14-brain` · authority **NONE** (producer-run sandbox) ·
receipt `canonical/verification/COMPOSE_MEASURED_EFFECTS_20261116_V1.json`

---

## 1. What changed, against the same four machines

`instant_learning_in_a_new_environment_v1` measured the price of a new machine: one trial per
(atom, state class), a shared vocabulary of `PERSIST`/`REMOVE`/`REPLACE`, and 13 of 16 requests
solved. Three were refused, and all three were the same defect — **picking one atom is not acting.**

`compose_measured_effects_v1` plans off-line over the measured table, then executes the plan and
audits every step. Same four machines, same sixteen requests:

| | single atom (last turn) | composed (this turn) |
|---|---|---|
| solved | 13 / 16 | **14 / 16** |
| solved with a two-step plan | — | 1 (`TARBALL` replace = append then delete) |
| proven impossible | 0 (they were just refused) | **2** |
| abstract states exhausted to prove it | — | **4** |
| prediction errors over 15 executed steps | — | **0** |
| unrequested side effects | not checked | **0** |

`tar` has no "replace a member's content" atom; replace is *append then delete*, and the planner
found that plan, executed both steps, and the reader confirmed each one. `git` can only rewrite or
remove the **tip** commit, so "replace entity X" and "remove entity X" are not refused for want of
effort any more — the search over the offered atoms is exhaustive, and the verdict is
`PROVEN_UNREACHABLE_UNDER_THE_OFFERED_ATOMS` with the state space it exhausted.

**A refusal is now a result.** That is the difference between an agent that flails and an agent that
knows what a machine cannot do — and it costs nothing, because it is proved in the model, not
discovered by burning the machine.

## 2. The part I did not expect to matter, and it mattered most

The composer's first run "solved" a removal on the filesystem in one step by **overwriting the thing
to be removed with something nobody asked for**. The stated goal was met. The machine was not.

That is not a bug in the planner; it is a property of the goal language. "Make X disappear" does not
say "and change nothing else", so a planner will take the cheapest satisfaction it can find. Adding a
**frame condition** — everything outside the request must be untouched — rejected **15 plans** across
the four machines that met the goal as stated and broke something else. With the frame in place the
filesystem removal uses `rm`, and every solved request has **zero** unrequested side effects.

This is the frame problem, measured on four machines rather than argued about. It also says something
uncomfortable and useful about the whole plan: **a request is not a goal until it is a predicate with
a frame**, and the number of plans that satisfy the words but not the intent is not small — it was
15 out of 16 requests' worth of search.

## 3. Why the planning is sound and free

- **Free in trials:** planning is breadth-first search over 14 usable operators taken from 29 measured
  cells. It executes nothing. The whole run cost **29 adaptation trials + 15 executions = 44 trials**
  for 14 of 16 — against 34 trials for 11 of 16 by learning each request, which is the paradigm this
  replaces. (Same caveat as last turn: at four requests per machine the demonstrator is still cheaper;
  the crossover is ~6.4 requests per machine.)
- **Sound because conservative:** an operator is a *cell* of the measured table, and its precondition
  is exactly the state class it was measured in — the SAM discipline (Juba & Stern): admit a rule only
  under the condition it was observed under, so a plan is expected to succeed rather than hoped to.
  Measured consequence: **0 prediction mismatches in 15 steps.** The model is trusted for zero trials
  and audited for all of them; a disagreement is reported as `PREDICTION_MISMATCH`, never as success.
  This is the same ordering AGEL-Comp (arXiv 2604.26522) found decisive — verify the plan before
  spending the world, not after.
- **Reused, not rebuilt:** the machines, the measurement, the reader discipline and the effect
  vocabulary are imported from last turn's tool. This file adds a 40-line search, a frame test, and
  the audit. `transfer_learning_v1.drive` was read and not used, for a reason stated in the file: it
  plans by *acting* in an environment, and acting is exactly what is being economised here.

## 4. What is still not solved — and it is no longer planning

1. **The effect vocabulary.** `cp` duplicates a content — a shape outside `PERSIST`/`REMOVE`/`REPLACE`
   — so the measurement could not classify it and the composer cannot use it. `tar`'s
   append-to-existing-name produced a second unclassified cell. **Composition multiplies vocabulary;
   it cannot create it.** This is the third mechanic you named, appearing one level up: in code it was
   token vocabulary, here it is effect vocabulary, and in both places repetition cannot supply what the
   representation cannot name.
2. **The specification.** The engine is handed a predicate on machine state. A person says *"file the
   report"*. Turning an intention into a predicate — with the frame included, since we now know the
   frame is not optional — is untouched here, and it is the largest unbounded thing in the chain.
3. **Scale.** A real GUI has thousands of atoms, so the (atom × state class) table explodes. The
   existing answer in this tree is to spend trials by *decision value* rather than in order
   (`universal_active_transfer_learner_v2`), and on a screen the tax is much larger: OSExpert
   (arXiv 2603.07978) needed explicit exploration of an environment's unit functions before any
   transfer to unseen UIs appeared at all.

## 5. So: right or wrong?

**Right about the unit, wrong about the quantifier.** One verified experience per (action, state
class) is the correct quantum, and it is permanent *because it is a measurement, not a memory*: it
survives relabelling, reordering and a new session, and it is audited on every use. That is a real
revolution over learning each request by demonstration, and it is measured, including its price.

**Wrong that it closes computer use.** With composition, the chain now reads:

> expressive atoms → measured effect table → a composer → a frame → a goal predicate

Everything on that chain that has been *measured* works. The two links that have not been solved are
**naming new effects** (vocabulary) and **turning intention into a predicate** (specification).
Neither is a learning problem, and no amount of "experiencing it once" addresses either: you cannot
learn the name of an effect you have no word for, and you cannot demonstrate a predicate nobody has
stated.

**And the honest sentence about the creature:** what exists is a procedure acquirer with a verifier it
cannot forge and zero learned parameters. That is capability, not sentience; no test in this tree
measures sentience and this mechanism does not create it. Saying otherwise would be the exact
unverified claim the laws forbid.

## 6. The single bottleneck, third time, sharpened each time

> Turn 1: the size of the hypothesis space is the **vocabulary**; its reach per demonstration is the
> **invariant set**.
> Turn 2: for computer use the invariant is the **effect vocabulary** and the size is the
> **(atom × state class) table**; the binding constraint is **composition**.
> Turn 3: composition is not the binding constraint. It costs 40 lines and 0 trials.

**The binding constraint is the specification**: turning what a person wants into a predicate on
machine state, complete with the frame that says what must not change. Every remaining failure in
this experiment is downstream of it or of a missing effect name — and the frame result shows that an
incomplete specification is not a small error: it lets an agent destroy the machine while satisfying
the words.

## 7. Non-claims

- Four CLI/database machines, 18 atoms, 16 requests, one corpus. A cost law and a soundness result,
  not a benchmark score; none is claimed or improved.
- `PROVEN_UNREACHABLE` means unreachable **under the offered atoms and the content projection**. It is
  a proof about the model, not about the machine's every conceivable interface.
- Producer-run, authority **NONE**, no independent verification, no terminal or capability credit.
- Zero model dependency, zero network at run time, zero spend. Every verdict is a machine's own reader
  before and after the command.

## 8. Reproduce

```
python3 canonical/tools/compose_measured_effects_v1.py --out /tmp/compose.jsonl --receipt /tmp/compose_receipt.json
python3 -m pytest canonical/tests/test_compose_measured_effects_v1.py -q
```
