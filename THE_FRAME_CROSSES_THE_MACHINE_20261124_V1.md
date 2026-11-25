# The frame crosses the machine. 189 of 192 goals answered on a machine that shares no name with the one that taught the frame — and the two things that did not work are the useful part.

*2026-11-24 · branch `arena/50c05c04-brain` · base `c4f529eb`*
*Receipt: `canonical/verification/THE_FRAME_CROSSES_THE_MACHINE_20261124_V1.json`*
*Instrument: `canonical/tools/the_frame_crosses_the_machine_v1.py` (2m32s, 864 real runs, 82 real cells)*
*Kernel: `canonical/swe_kernel/canonical_frame_v1.py` · Machines: `canonical/tools/frames_that_cross_machines_v1.py`*
**Model calls 0 · parameters stored 0 · network at run time 0 · $0**

---

## 1. The question, and what already answered it

> "What if we make a perfect algorithm: it goes into any new arbitrary environment, asks the right
> question, and knows what it should know from instant knowledge. Should he learn everything, or be
> goal-directed? What should he save, and what should he *generalize*?"

This tree had already answered most of it, and this round did not rebuild any of it.

| already measured | number | where |
|---|---|---|
| an effect **is** a computable object: which relations moved between two readings | 5 relations, 3 vocabularies | `THE_VOCABULARY_IS_THE_ARTIFACT_20261125` |
| a rename moves **no** whole-reading frame — `mv` is invisible, so experience of it is experience of nothing | 1 atom, `hash_before == hash_after` | same |
| a goal is a **quotient of the trace**; its price is a number of cells | 3–6 cells against 20–68 runs | `THE_GOAL_IS_A_QUOTIENT_OF_THE_TRACE_20261128` |
| sufficiency is **reachability-relative**: shallow holds, deeper collides | 208 collisions | same, F5 |
| learning an environment's atoms once beats learning each request | crossover 25.78 requests | `instant_learning_in_a_new_environment_v1` |
| a check must be able to say **which** thing it is looking at | 8 of 8 citations accepted a decoy | `A_CHECK_THAT_NOBODY_RUNS...20261203` |

**What nobody had done is carry anything across a machine boundary.** Every number above is about
one machine. "Instant learning in a new arbitrary environment" is a claim about the crossing, and
the crossing had never been executed with a mechanism whose carried payload was small enough to
cross. That is the only new thing here.

## 2. The object

A **frame** is `(relation, slot-kind)`. Five relations the tree already uses — `CARD`, `MULTISET`,
`ORDER`, `IDENT`, `PAIRING` — aimed three ways: the whole reading, the rows one **content** selects,
the rows one **identity** selects. Fifteen frames, all computed from the two fields a machine's own
reader prints.

A **template** is what moves between machines: the frames that moved, under slots, with
**no literal in it**. `mv`'s template is `+IDENT@CONTENT, +PAIRING@WHOLE` — one identity vanished,
one pairing appeared, *the content the goal names*. It says nothing about `old_name`, `new_name`,
`alpha_one`, a commit hash or a member path. It instantiates on any machine that can name a
content, which is why it crosses.

A **labelling** is only used when a template names structure rather than a slot, and it is only
usable when it is **unique**: two labellings that both fit mean the template means two things on
this machine, and `instantiate` returns `REFUSED__LABELLING_NOT_UNIQUE`. It never takes the first
fit. That is measured, not asserted.

## 3. The measurement

**Nine machines**, seven of them new work and two reused (`FILESYSTEM`, `GIT`, `TARBALL`,
`SQLITE` from the existing file, used as-is). Real `git`, `tar`, `gzip`, `sort`, `sh`, `chmod`.
They share **no literal at all**.

### L1 — what the old vocabulary could not even say

| machine | effects that changed the reading | sayable as `CARD`/`MULTISET` **over the whole reading** |
|---|---|---|
| LIST | 8 | 4 — and the 4 it cannot name are **ORDER** and **MULTISET@IDENT** |
| GIT2, ARCHIVE2, JOURNAL, VAULT | 5, 3, 6, 4 | all |
| FILESYSTEM, GIT, SQLITE, TARBALL | 2, 6, 2, 2 | all |

Half of `LIST`'s effects are unsayable to the old vocabulary, and `sort` is one of them: it changes
the file and leaves the multiset *exactly* unchanged. This is the `mv` finding reproduced on a
second machine, by an instrument that was not written to find it.

### L2 — how many judged runs before one frame survives

Supervision is the weakest thing a user can give: "this end state is the one I meant", per run.
A prior over frames is built **leave-one-machine-out** from the other eight machines' identified
frames, and it only ever re-orders hypotheses.

| machine | goals | frames reachable | identified, no prior | identified, with prior |
|---|---|---|---|---|
| FILESYSTEM / GIT2 / JOURNAL / LIST / ARCHIVE2 / SQLITE / TARBALL | 5 / 25 / 25 / 54 / 10 / 5 / 5 | 5 / 15 / 10 / 15 / 10 / 5 / 5 | **5 / 6 / 6 / 6 / 6 / 5 / 5** | identical |
| GIT | 34 | 15 | 4 | 4 |
| VAULT | 10 | 5 | 2 | 2 |

**A frame is identified from one judged run on most machines** — `archive`, `append`, `sort` all
land exactly, and the survivor *behaves like the goal on the deeper pool*, which is the stronger
half of the claim. On the hardest machines (GIT: identity is a hash, so a shallow pool cannot
separate `IDENT` from `PAIRING`; LIST: 15 frames, several equivalent on a 4-row file) it takes 2
runs, and a few goals are never pinned: the hypothesis survives, it just is not unique.

**The prior bought exactly nothing, twice over.** Zero goals gained, zero runs saved. This is the
second independent measurement in this tree that a cross-environment prior does not move
identification: `BREADTH_BUYS_WHAT_REPETITION_CANNOT` measured the same saturation in statements
(4 → 2 → 2, the third machine removing zero). It is reported as a failure, not smoothed.

### L3 — the crossing, which is the point

A frame is learned on machine **A**. Only the frame crosses — no atom identifier, no literal, no
command, no value. On machine **B** the agent reads B, executes **each atom once** (a real, counted
cost), and picks the atom whose measured effect moves the carried frame. Then B's own reader
judges. Three columns, same goals, same budget:

| column | what it carries | reached | picked the atom that produces the outcome |
|---|---|---|---|
| **FRAME** | one relation + one slot kind | **189 / 192** | **189** |
| **BLIND** | *nothing* — act on whatever changed the reading | 167 / 192 | 166 |
| **EXEMPLAR** | the accepted end state, reproduced exactly | **0 / 192** | — |
| **REPLAY** | the atom identifier that worked on A | **0 / 192** | refused: `ATOM_IDENTIFIER_DOES_NOT_EXIST_ON_THIS_MACHINE` |

That is the sentence the owner asked for, measured: **the relation crosses and the trace does not.**
The exemplar control is the honest acid test — it is the strongest frame-free baseline, it needs no
vocabulary and no prior, and it fails on precisely what a frame throws away: identities that differ
between the machine that produced the exemplar and the machine answering now.

**And BLIND is not a straw man.** It reaches 167 of 192, only 22 behind. On most of these machines a
randomly chosen atom that changes anything happens to be the right atom, because the machines have
few atoms and one verb. **The frame's advantage here is 13 percentage points, not a chasm**, and it
would shrink to nothing on a machine with many interchangeable atoms. Said plainly because it is
true: at this scale, "carry the relation" and "carry nothing" are closer than the headline suggests.

### L4 — sufficient at depth 2, collided at depth 3, with a witness

A **frame-free** user goal ("`gamma_three` appears exactly twice") is carried by `CARD@WHOLE`,
chosen because it separates every judged run on the depth-2 pool (0 collisions). On the depth-3
pool, `CARD@WHOLE` merges two readings the user judges differently:

```
the user accepts:  3 commits, gamma_three appearing twice     <- add, then amend
the user rejects:  3 commits, gamma_three appearing twice     <- add, then amend the other way
and CARD@WHOLE gives both the same value: 3
```

**1 of 29 goals collided on the deeper pool, and the witness is stored.** That is F5 reproduced on a
real machine in a new unit: *a "sufficient" statistic is sufficient for the runs that exist.*

**This section was rebuilt.** Its first version asked "does the frame equal the value the frame
produced", which cannot collide with itself — 39 rows, zero collisions, measuring nothing. The
defect is now a test (`test_a_tautological_frame_can_never_collide_and_that_is_the_defect`) so it
cannot return quietly.

### L5 — the prior over actions, and where it went wrong

| depth | BLIND plans | PRUNE plans | ORDER plans | BLIND executions | PRUNE executions | ORDER executions |
|---|---|---|---|---|---|---|
| 2 | 7 | 4 | 7 | 298 | 214 | 346 |
| 3 | 7 | 5 | 7 | 2,538 | 1,011 | 2,586 |

`PRUNE` restricts the action set to atoms that move a frame the goal is stated on. It cut
executions 4.9× — and **lost 5 plans that unpruned search found**. The reason is structural: in a
conjunctive goal the second clause is often only reachable *after* the first action, so an atom that
moves no wanted frame at reset is still the atom step two needs. **Goal-directed pruning of the
action set is unsound for conjunctive goals.** The mechanism is kept in the instrument with that
sentence in its docstring and a test that asserts it is still there.

`ORDER` is the sound version: nothing is pruned, the preferred atoms are merely tried first. It
lost no plans and **saved nothing** (2,586 executions against 2,502). Its own cost — one execution
per atom to learn which frame each moves — is paid before the first plan is attempted, and at
branching factor 4–7 and depth 2–3 it does not repay. The `b^depth` argument says it should repay at
depth 6; **this instrument cannot reach depth 6, and does not claim it.**

### The blind spot, built on purpose

`chmod 600 → 755` is a real change to real state. Every one of the fifteen frames is blind to it,
and the instrument reports `the_vocabulary_can_state_it: false`. A vocabulary that answered here
would be guessing. Pixels, permission bits, scroll offsets and window focus are all outside this
grammar, which is why nothing in this document is GUI work.

## 4. What is real, what is false

**Real.**
* An effect is a computable object, and the object can be made **literal-free**. 189 of 192 goals
  answered on a machine sharing no name with the teacher, by a mechanism carrying 1 relation and 1
  slot kind.
* A stored trace does not cross (0/192, refused by name), and a stored end state does not cross
  (0/192). The difference between "experience the action once" and "carry the relation" is not
  philosophical; it is 189 against 0.
* A frame is identified from **one** judged run on most machines and **two** on the hardest.
* A labelling that is not unique is refused, not guessed.
* Sufficiency is relative to the run set: 1 of 29 frames collided at the next depth, with the pair
  of runs that proves it.

**False, and measured false here.**
1. **"The prior is the lever."** Two independent measurements, zero goals gained, twice.
2. **"Goal-directed pruning of the action set is safe."** It lost 5 of 14 plans. The sound version
   saves nothing at this scale.
3. **"Carrying the frame beats carrying nothing, decisively."** 189 against 167. On machines with
   few interchangeable atoms, acting on anything that changes helps almost as much.
4. **"This is goal-directed search."** The goal here is a *predicate* the instrument derives; the
   real front door is a sentence in English, and `BREADTH_BUYS...` priced the residual at
   `log₂(class)` questions no run can answer.
5. **"This is computer use."** Nine CLI/database machines, no display. `OSWorld 2.0`
   (arXiv 2606.29537) puts the frontier at 20.6% binary on 108 long-horizon desktop tasks and names
   hidden state and missing verification as the cause — the same law, a different substrate, and
   this instrument does not touch pixels, permissions or widget trees.

## 5. The answer to the owner's question, in one paragraph

**Carry the relation, not the experience, and carry it with slots instead of names.** That is what
generalization is, operationally: a template that names no literal instantiates on a machine that
shares no literal, and a template that remembers one refuses or means several things. **Be
goal-directed, not exhaustive** — not because reading everything is expensive but because 94% of
what you would read is prose no run can confirm (`THE_GUIDE_IS_A_TEST_SUITE`, 5.96% checkable).
**Save the frame and the refusal, never the trace, and never an unidentified reading.** And do not
expect a cross-machine prior to pay: twice measured, twice zero.

## 6. The bottleneck, restated with a number

> **The carried object was the bottleneck, and it is now one relation plus one slot kind.**
> What is left is the step before it: turning the user's sentence into the frame, and knowing when
> the frame you carry is not the frame the goal is about.

The second half is measured here: 189 of 192 works because the goal's frame was *given*. When it is
not given — a real user's sentence — the price is the class of frames consistent with the runs,
and `BREADTH_BUYS...` says exactly how many questions that is: `log₂(class)`, answerable by the
user, never by more runs.

## 7. Next, pre-registered so it can fail

Take one machine this instrument has never touched, a task stated as **one English sentence** and
nothing else, and measure three things that can each be false:

1. **frame extraction** — does the sentence plus the reading determine one frame, or a class?
   (pre-registered failure: a class larger than 2 for more than half the sentences)
2. **the crossing** — does the frame learned there answer a held-out goal on a machine the
   instrument has never seen, above the BLIND baseline by more than 13 points?
   (pre-registered failure: ≤ 13 points, i.e. no better than the measurement above)
3. **the refusals** — does every case where the carried frame is *wrong* produce
   `REFUSED__LABELLING_NOT_UNIQUE` or a named witness instead of a silent wrong answer?

Falsifiers of *this* round, stated before it ran and kept: a frame that is identified but does not
behave like the goal on the deeper pool; an `EXEMPLAR` column that reaches anything; a `BLIND`
column that beats `FRAME`; a `PRUNE` loss reported as a win; a collision count measured against a
statement about itself.

## 8. Accounting

| | |
|---|---|
| machines | 9 (4 reused as-is, 5 new), real tools, own readers, no shared literal |
| cells executed | 82 (every atom × 2 state classes × every machine) |
| runs executed | 864 (all distinct-atom sequences to depth 2, and to depth 3 for L4) |
| crossing rows | 216 (source × target × frame), 192 judgeable, 24 refused as not-a-task |
| tests | **16 new, all passing**; the repo's integrity guard: 17 rules, **0 violations** |
| model calls / stored parameters / network | **0 / 0 / 0** |
| wall clock | 152 s |

**Not claimed:** any capability registration, any family flip, any benchmark score, any independent
verification, any GUI result, any terminal credit. `truth.achieved` is untouched. This is a
producer-run sandbox measurement, and the two columns that lost are printed next to the one that won.
