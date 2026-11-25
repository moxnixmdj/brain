# THE PLAN IS A PARTIAL ORDER

**Date** 2026-11-24 · **Branch** `arena/50c05c04-brain` · **Schema** `BRAIN_THE_PLAN_IS_A_PARTIAL_ORDER_V1`
**Receipt** `canonical/verification/THE_PLAN_IS_A_PARTIAL_ORDER_20261124_V1.json`
**Kernel** `canonical/swe_kernel/partial_order_planner_v1.py` · **Instrument** `canonical/tools/the_plan_is_a_partial_order_v1.py`
**Tests** `canonical/tests/test_the_plan_is_a_partial_order_v1.py` — 13 passed
**Cost** 0 model calls, 0 stored parameters, 0 network at run time, 61 s, 9 machines, 16 problems, 1,571 executions

---

## §0 What was asked, and what this answers

The request was rich, and most of it is **not** what this round built. That has to be said first,
because a report that quietly answers a smaller question than the one asked is a form of
overclaiming.

**Built and measured here:** one organ — a planner that searches backwards over *measured*
operators, constructs a partial order rather than a sequence, and refuses to report a plan it has
not watched happen.

**Not built here, and named so it is not mistaken for done:** backward *program* regression over
traces, typed skill algebra, adversarial self-play over the failure corpus, and the
"epistemic scan/acquire/compress" loop. Two of those were named in the request as files
(`typed_invention_v1.py`, `epistemic_scan_acquire_compress_v1.py`) that **do not exist in this
repository**; no attempt was made to invent them.

The reason for choosing this one organ is in §3: it is the only one of the four ideas that
attacks a defect *this repository measured against itself two rounds ago*.

---

## §1 The defect this closes

The previous round (`THE_FRAME_CROSSES_THE_MACHINE_20261124_V1`) recorded its own idea failing:

| mode | plans found | executions |
|---|---|---|
| BLIND | 14 | 2,836 |
| PRUNE (restrict actions to those moving a goal frame) | 9 | 1,225 |
| ORDER (sound re-ordering) | 14 | 2,932 |

`plans_lost_by_pruning 5`. The conclusion written down was: **goal-directed pruning of the action
set is unsound, and sound ordering saves nothing.**

That conclusion is correct about forward search and wrong about the idea behind it. The idea —
*let the goal tell you which actions matter* — is the reason backward search exists, and the reason
it works is that it does not give up completeness: it commits to nothing it is not forced to
commit to. Sacerdoti's linear planning, which *does* commit greedily, is the version that fails on
Sussman's anomaly. The repository had implemented the greedy version and concluded the idea was bad.

**The branching factor saving is real, and it requires a different search space, not a filter.**

---

## §2 What was built

### 2.1 A partial-order planner (`partial_order_planner_v1.py`)

Textbook POP, written down because the details are the findings:

* goals and step-preconditions are both *open conditions*, until a causal link establishes them;
* a relevant operator must **add** the open condition (AIMA's definition, and the whole source of
  the saving);
* each link is protected against steps that would **delete** its condition; a threat is resolved by
  **promotion** (threatener after the consumer) or **demotion** (before the producer), and both are
  tried with backtracking;
* an existing step may be **reused** to satisfy a new open condition;
* the deliverable is a **partial order**; the execution order is one topological sort of it and is
  reported as a choice, not as the proof.

### 2.2 Operators are induced, not written (`induce_conditional_operators`)

An operator here is a measurement: `pre` (a guard, a conjunction of frame-tests), `add`, `delete`.
Nothing in the file knows what `git`, `tar`, `sort`, or a block is; every atom is `G2_A3`-shaped
opaque text.

Effects on these machines are **state-dependent** — appending to a two-row journal and appending to
a three-row journal are one atom with two effects. Static STRIPS add/delete cannot express that, so
the guard is recovered by **splitting the transitions on the condition vocabulary until every leaf
has exactly one observed effect**. That is the narrow, checkable form of "differential state
tomography": the effect is a function of the state, and the split recovers the function from paired
readings.

---

## §3 The single plan, and the ideas that were rejected

**Requirements confirmed.** Zero model calls, zero stored parameters, no invented measurement,
every claim executed and judged by the machine's own reader, refusals name their cause, and the
repository's own enforcement (`repo_integrity_guard_v1`: 17 rules, 0 violations) passes.

**Research findings that shaped the design.**

* **Partial-order planning** is complete with a branching factor set by *relevant* actions, and
  greedy backward chaining is not — Sussman's anomaly is the counterexample, and the SPLIT between
  "commit to an order" and "commit only to a link" is the whole content of the idea.
* **Backward search has its own branching factor**: many ground instances of a relevant operator,
  most of whose preconditions are unreachable. That is why the refusals here are informative rather
  than embarrassing.
* **Regression over incomplete information** (LMCS 2006) needs a state-based regression function
  with a soundness proof against progression — out of reach here, and named as such.
* **MDP homomorphism / quotient work** (Ravindran; MDP Homomorphic Networks; groupoid symmetries)
  is the *other* way to cut a search space, by quotienting symmetric states. Not used: these
  machines are only partially symmetric, and the previous round already found the partition
  literature absent from this tree.

**The one plan chosen:** *build the smallest organ that turns "the goal says which actions matter"
from an unsound filter into a sound search, over operators that were measured rather than written,
on the nine real machines already in the tree.*

**Rejected, with reasons:**

| rejected | why |
|---|---|
| Re-run PRUNE with a better relevance test | The defect is not the test, it is the restriction. Any root-level filter loses plans whose second clause needs an atom that moves no goal frame. Kept as a control, not a candidate. |
| A learned action prior / heuristic from the frame | The previous round measured ORDER saving nothing (2,932 vs 2,836 executions). A heuristic over the same space cannot beat the space. |
| Typed skill algebra | Would be a new vocabulary with no measured defect behind it. The typology it needs (`plans_compose_v1`, `compose_a_host_never_seen_v1`) already exists and is not failing. |
| Adversarial self-play over the failure corpus | Interesting and unmeasured here; with 16 problems and no held-out split it would be a demo, not a measurement. Named as future work. |
| Backward *program* regression over traces | The traces do not carry preconditions; that is exactly why operators had to be induced first. This round is its prerequisite. |
| Symbolic regression of a `CUMentalWorldModel` | Not referenced by anything in this tree and not needed by the organ that was built. |

---

## §4 Results

### 4.1 The induction (9 machines)

| machine | atoms | conditions admitted | pure leaves | impure leaves | dropped pre | states seen |
|---|---|---|---|---|---|---|
| ARCHIVE2 | 4 | 54 | 8 | 0 | 0 | 4 |
| FILESYSTEM | 5 | 34 | 1 | 4 | 0 | 4 |
| GIT | 5 | 208 | 12 | 13 | 0 | 41 |
| GIT2 | 4 | 148 | 12 | 10 | 6 | 25 |
| JOURNAL | 4 | 128 | 22 | 0 | 0 | 15 |
| LIST | 7 | 1061 | 45 | 26 | 16 | 136 |
| SQLITE | 4 | 42 | 6 | 0 | 0 | 4 |
| TARBALL | 4 | 42 | 8 | 0 | 0 | 4 |
| VAULT | 4 | 22 | 1 | 3 | 0 | 4 |

**Impure leaves are reported, never smoothed.** An impure leaf means this vocabulary cannot express
the effect's precondition; it is a statement about the vocabulary, and it is why FILESYSTEM and
VAULT yield one citable operator each.

### 4.2 The four-way race (16 conjunctive problems)

| planner | plans found | executions | note |
|---|---|---|---|
| **POP** | **4** | **45** | every plan executed and judged |
| FORWARD | 8 | 1,120 | the reference for completeness |
| PRUNE | 4 | 346 | same count as POP at 7.7× the executions |
| BACKWARD (greedy) | **0** | 60 | 2 attempts *undone by a later step* |

`POP_lost_where_FORWARD_found 4` · `FORWARD_lost_where_POP_found 0`.

**Greedy backward chaining solves nothing here, and twice it built a plan that a later step undid.**
That is Sussman's anomaly reproduced on `git`, `tar`, `sort` and `journal` — not asserted from the
textbook, measured.

**Where POP loses, and it is not a mystery:**
* 4 problems: `OPEN__NO_PARTIAL_ORDER_FOUND`. On GIT the goals are commit *hashes* — an unbounded
  value space, so no induced operator can cite the exact identifier as an add-effect. On GIT2 the
  precondition that matters was dropped as unestablishable (6 drops).
* 8 problems: `PLAN_EXECUTED_GOAL_NOT_OBSERVED`. On LIST and GIT2 the induced guards were **wrong**
  — measured on observed states, incomplete as descriptions of all states. POP believes its table;
  forward search merely executes and checks. This is the honest limit of inducing operators from a
  finite sweep, and it is why certification (§4.3) exists.

### 4.3 The claim discipline

Two checks, and the second was added because the first was insufficient:

* **`certify()`** — every state on the plan was observed during measurement.
* **`replay_on_observed_transitions()`** — from the concrete state the plan is actually in, was this
  exact `(atom, state) → next` transition observed?

The second exists because **one plan passed the first and still failed.** A state can be observed
once, in a context where the following atom behaves differently from what its guard predicted; the
guard is a conjunction, and two different states can satisfy one conjunction. State-level coverage
is not step-level coverage.

**`claims with every step observed and TRUE: 4`, and `PLAN_FOUND` with an unobserved step: 0.**
No plan in this receipt is asserted without its every step having been a record rather than a
prediction.

---

## §5 The seven defects found by running it

Each is pinned by a test, so none can return quietly.

1. **Goals were never opened.** The root plan pre-linked each goal to itself, so every goal counted
   as supported and the planner returned **a zero-step plan for an unsatisfied goal**.
2. **Transcribe vs. operator.** One table per atom made `add` the union of every effect ever seen —
   fifty-six conditions for a three-line append. Not an operator; a transcript.
3. **No step reuse.** Minting a fresh instance per open condition "solved" a two-application goal
   with **seven copies** of one atom. It then failed on execution.
4. **Unestablishable preconditions.** Guards no operator adds and the initial state lacks make an
   operator permanently inapplicable; the planner reported `OPEN` where breadth-first found a
   3-step plan. Closure now drops them and **counts** the drops.
5. **Self-enabling guard.** A guard that the operator itself establishes — `append` requiring
   `CARD[IDENT=3] equals 1` in order to add `CARD[IDENT=3] equals 1`. A backward search can never
   start from it; a forward search never notices. **This asymmetry is why the defect survived until
   the two were raced.**
6. **Ambiguous context read as unconditional.** An operator whose context was not identified and
   whose precondition was empty was treated as applying everywhere — the fiction that produced a
   plan execution refuted.
7. **Two bugs in the splitter itself.** It *minimised* impurity (preferring a condition that
   separated nothing, yielding an empty child leaf reported as "pure, no guard"), and it compared
   distinct-label *counts*, which rates a perfect binary split as no improvement. Both fixed; both
   are now tests.

There was also a defect in the instrument, not the kernel: it **sampled operators from enumerated
prefixes and searched reachability with a separate sweep**, so the transitions it learned from were
missed ones. Replaced by a single BFS that yields states *and* transitions — cheaper and richer.

---

## §6 What this does not show

* **Not a benchmark score.** 16 problems on 9 sandboxed machines, no held-out set.
* **Not independent verification.** The producer ran its own instrument.
* **Not cross-machine transfer.** Operators are measured per machine; wiring the frame module's
  carried vocabulary into the induction is the obvious next step and is **not done**.
* **Not a win over forward search in completeness.** POP found 4/8 of what FORWARD found. The
  claim is narrower and stronger: where it plans, it plans from operators measured on the machine,
  it constructs an order rather than guessing one, and it never asserts a plan whose steps were not
  observed.
* **No GUI, no browser measurement.** The sandbox has no browser and none was claimed.

---

## §7 Next, in order

1. **Wire the frame across machines into induction** — carry the condition vocabulary from machine A
   and induce only the guards on machine B. That is the composition the previous round named and
   this one did not do.
2. **Repair wrong guards rather than refusing them**: when `PLAN_EXECUTED_GOAL_NOT_OBSERVED` fires,
   the refuted plan is a *new observation*, and re-inducing with it is the natural loop. This is the
   honest form of "adversarial self-play over failures" — one's own refuted plans as the adversary.
3. **Deeper exploration before induction** (depth 4–5 on the machines that admit it) to see whether
   impure leaves fall or whether the vocabulary is the limit.
