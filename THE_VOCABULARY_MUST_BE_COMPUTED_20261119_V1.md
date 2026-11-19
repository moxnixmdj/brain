# The vocabulary must be computed, not written

*Round dated 2026-11-19. Receipt: `canonical/verification/THE_VOCABULARY_MUST_BE_COMPUTED_20261119_V1.json`.
Tool: `canonical/tools/the_vocabulary_must_be_computed_not_written_v1.py`. Tests: 11, all green. Five real
machines, 44 measured (atom, state class) cells, one probe per cell. No model, no weights, no parameters,
no network. 2.8 s.*

---

## 0. The answer on one page

The claim under test, again: *if the agent does each action once and keeps it permanently, plus the best
coding, do we get all of computer use — because after one try it learns everything forever?*

The last two rounds removed two reasons it fails: the decision (a free attempt decides it) and the last bit of
the goal (a proof decides it; 983 runs agreed and still left two functions). This round finds the next reason,
and it is the one that explains why the previous two had to be fixed at all:

**What the agent can learn and compose is bounded by what its vocabulary can name.**

The project's composer states its own limit in its docstring — *"`cp` … a shape outside the three-effect
vocabulary … the composer cannot use what the vocabulary cannot name"* — and the table it plans over is
hand-written, in four shapes:

```
(0,0,0) → INERT     (1,1,0) → PERSIST     (-1,0,1) → REMOVE     (0,1,1) → REPLACE
```

Measured on 44 real cells, atom by atom, on five machines:

| hand name | the two different things it stands for | atoms |
|---|---|---|
| **PERSIST** | writing a **new** content · **copying** an existing one | `FS_A1` · `FS_A4` |
| **INERT** | a command that **did nothing** · a command that **moved the world** | `FS_A2` · `FS_A3` |
| **REPLACE** | replacing a content in place · replacing it while the identity moves | `FS_A1` · `GIT_A3` |
| **REMOVE** | removing one content · removing a different one | `FS_A2` · `GIT_A2` |
| **UNCLASSIFIED** | two entirely different leftovers | `SRT_A3` · `TAR_A1` |

Every one of the five names merges **exactly two** distinct transitions. The purest case: `mv` — the command
that achieves the project's own `moved_judge` — is recorded as **INERT**, the same word as a command that
changed nothing. The project already computes `identity_changed` for every cell and then throws it away in the
naming.

So: the agent can perform ten different transitions and can distinguish five. It can succeed by luck and it
cannot *choose*. That is the whole difference between "it worked once" and "it knows what it did".

The fix is not a bigger vocabulary. It is that **the name should be the signature**:

```
ARRIVE[roles];DEPART[roles];CARD±k;IDS+p-q
```

Which gives, for the two cells above, `ARRIVE[ARG];…;IDS+1-0` versus `ARRIVE[OLD];…;IDS+1-0` — creation and
duplication, told apart — and `…;IDS+0-0` versus `…;IDS+1-1` — nothing and a move, told apart. The move's
derived name is `ARRIVE[-];DEPART[-];CARD+0;IDS+1-1`, it is an operator, one executed command satisfies
`moved_judge`, and the refinement cost **zero additional trials** because the fourth coordinate was already
measured and discarded.

> **A vocabulary is a map from transitions to names, and everything downstream — what can be stated, what can
> be planned, what can be learned — is bounded by that map's preimages. A hand-written map is neither
> injective nor consistent: it merges what the world distinguishes and distinguishes what it does not. The map
> must be computed from the transition that was already observed, and then the merges disappear for free.**

## 1. Why a merged name is not a cosmetic problem

Suppose the vocabulary merges `n` pairs of distinct transitions. Three consumers read it, and all three are
affected in the same way:

1. **The statement grammar** (identification). Last round's residual was two statements differing only on a
   step that adds *two* copies at once. `cp` is that step's atom — and the vocabulary names it the same as
   `write`. The ambiguity was not philosophical; it was a merged name.
2. **The planner** (composition). The composer builds operators from cells whose effect is in the vocabulary.
   A cell named INERT is not an operator, so a plan that needs a move has no move to choose. The planner is
   not weak; it is blind to an action the machine offers.
3. **The learner** (acquisition). One trial records one transition. If the recording maps it onto a name that
   already has a preimage, the trial added no information about *which* transition was seen — the same
   arithmetic as the previous round, one level down.

With `k` steps, a planner that cannot distinguish `n` merged pairs is choosing among `2^k` worlds it cannot
tell apart, and every one of those choices is a real failure mode. The merge is not an abstraction *of* the
world; it is a loss of it.

**And it is not even a consistent abstraction.** Measured: 11 of the hand-level operators *do* carry an
identity change (FILESYSTEM 3, SQLITE 4, TARBALL 2, GIT 2), while the move that matters is named INERT. So the
identity coordinate is present in some cells and absent in others — for the same atom, in two state classes.
A coarse abstraction is at least a function of the state; this one is not a function of the transition at all.

Which makes the most dangerous object in this project's drawer **a sound proof about a wrong model**:

```
the hand model, exhaustively searched:   moved_judge is PROVEN UNREACHABLE
one real command:                        mv seed copy   →  moved_judge TRUE
```

The composer's own principle is *"a refusal is a proof, not a budget."* That principle is right, and this
round is its boundary condition: **a refusal is a proof about the model, and the model is only as good as its
naming.** The proof was valid. The action existed. The agent said no.

## 2. What the derived vocabulary is, and why it is not a bigger hand table

The derived name is the measured signature, printed:

```
ARRIVE[the roles that arrived];DEPART[the roles that departed];CARD±k;IDS+p-q
```

Nothing human chose it. It cannot be missing a coordinate, because the signature *is* the transition. It is
canonical (equal transitions get equal names, different transitions get different names), so the merge
disappears by construction rather than by care.

The refinement is free in the only currency this project counts:

| | before | after |
|---|---|---|
| probes executed | 44 | **44** |
| extra trials for the new vocabulary | — | **0** |
| parameters stored | 0 | **0** |
| information discarded | `identity_changed` computed, then thrown away by the naming | none |

That is the governing law applied exactly: **the best part is no part.** The effect vocabulary is not a
component to be designed and curated — it is a quotient of the measurements that were already taken. A
hand-written table is a part; a fold over the observation is not.

## 3. What the field is doing, and the one word it uses for this

**Abstraction refinement is standard, and the trigger is distortion.** A June 2026 treatment of adaptive
state-action abstractions states the principle directly — *"refine the abstraction as soon as the learning
error within it becomes comparable to the error induced by the abstraction itself"* — and lists the existing
triggers as transition-estimate distinguishability or verification counterexamples [1]. This round's trigger
is the sharpest possible version of the first: **a named cell whose preimage has more than one element is
distortion you can count**, before any learning error appears.

**Merging is sound exactly when the effects are identical — not similar, not same-shaped.** Operator-learning
work merges operators *"with identical effects"*, computing preconditions and effects from symbolic
transitions [2], and object-typing work merges two objects into one type precisely because *"they react
identically to the same actions"* [3]. Both are the same rule this round enforces mechanically: equality of
the *measured effect*, with every coordinate present. A hand-written shape table approximates that equality by
its first three coordinates and calls the approximation a name.

**And the equivalence frame is the same one the last round used.** Behavioural equivalence and behavioural
provability are different relations, and the inclusion between them is proper [4]; identity must factor
through the behavioural quotient under a declared observation model [5]. The effect vocabulary *is* such a
quotient — the quotient of transitions under the state reading — and the bug this round measures is that the
project's quotient was declared by hand instead of computed from the reading it already had.

None of this is holy. It converges on one arithmetic point that is checkable here: **if two transitions are
different and one name covers both, some consumer will be wrong, and no amount of trials repairs it.**

## 4. What this says about learning once, and about "understanding"

The user's question — *why can't we just let it experience each action once and keep it?* — has a precise
answer now, and it is not about memory or permanence:

> One trial records one transition. Whether that record is *usable* depends on whether the vocabulary
> distinguishes it from the other transitions. A learner with a coarse vocabulary learns a coarse world,
> permanently and confidently.

That is also the honest reading of the prompt's own objection that pattern matching is not understanding.
Pattern matching is a **coarse quotient**: many distinct situations, one response. Understanding, in the only
sense that is measurable here, is the *fineness* of the quotient — how many distinct behaviours the
representation separates — and fineness is a number: preimages per name, cells per transition, merges at zero.
This round moved that number from 5 names over 10 transitions to 10 names over 10, at no cost.

And it says what belongs in our weights. Not facts, not names: **the computation that forms the quotient from
an observation, and the choice of what to observe so the quotient is fine enough.** Both are computations over
a problem. The vocabulary itself is a fold over data we already have, which is why it needs no parameters at
all. The best part is no part.

## 5. The bottleneck, sharpened again

Last round: *the gap between consistency and equivalence.* This round: **the naming is the gate on both.**

```
observation → naming (the quotient) → statements, operators, trials
```

A defect anywhere to the right is bounded by the left. Coarse naming makes identification ambiguous (two
statements agree forever), composition blind (a move is INERT), and acquisition uninformative (a trial adds no
bit). So the ordering of work in this project changes: **before more learning, more environments or more proof,
measure the preimages of the vocabulary.** It is 44 probes and 2.8 seconds. Every one of the five names had
two preimages; every one of them is now split.

What is left is the honest part of the original claim. With a computed vocabulary, a judge, and a proof:

- **identification** is closed by arithmetic over a complete quotient;
- **composition** is search over operators that are now distinguishable;
- **acquisition** is one trial per cell, and the cell is now a real cell.

What remains is depth: planning over a long horizon where interference between steps, not naming, is the
constraint — the frame problem, which the composer already measures (`relaxed_plans_that_break_the_frame: 15`)
and which no vocabulary fixes.

## 6. What is real, what is not, and the limits

**Real.** Five hand names, each with exactly two preimages, measured on 44 cells of five machines. The move
that achieves `moved_judge` is named INERT and its signature is `…IDS+1-1`. The derived vocabulary names all
44 distinctly, makes the move an operator, and one executed command satisfies the judge. Zero extra trials,
zero parameters.

**Not real.** "The vocabulary is a design choice we can curate." "A refusal is always a proof about the world."
"One trial teaches the action." Each of these is true only up to the naming, and the naming was measured to be
neither injective nor consistent.

**Limits.** Five CLI machines and their own readers; the derived vocabulary is the quotient of *these*
transitions under *these* readings, not a universal effect algebra. The four coordinates (arrived roles,
departed roles, cardinality, identity) are the coordinates the state reading exposes — a surface that hides
more would need a finer reading, and that is a different measurement, not a different naming. The planner is
not re-planned here; this round measures what a vocabulary can *name*, and the composer's own receipt measures
what it can *plan*. Long-horizon interference is untouched.

## 7. Next step, pre-registered

**Give one machine a surface whose reading drops a coordinate the world has** — e.g. a store where two distinct
entities are readable but their identity is not (content only, like a deduplicating store that reports the
multiset and nothing else) — and check three things that can fail:

1. the derived vocabulary for that surface has **fewer** coordinates than the transitions have, so two distinct
   transitions share a name *by construction* — and the receipt should say so, naming the missing coordinate
   rather than hiding it;
2. a goal that needs the hidden coordinate is **not reachable by any plan** in that vocabulary, and the refusal
   is correct *for that surface* and wrong *for the machine*, which is the difference the previous round's
   `dm-log-writes` step is to durability;
3. adding the coordinate back — a richer reader, one more field, no new trials beyond re-reading — collapses the
   merge and the plan appears.

Falsifiers: if a coarser reading does not merge anything, then the reading was not coarser and the claim about
naming is empty; if the merge does not block a plan, then composition does not depend on the vocabulary and
this round is only bookkeeping; if re-reading does not collapse it, the quotient account is wrong.

---

## Sources

1. *Adaptive state-action abstractions via rate-distortion* (arXiv 2606.06123, June 2026) — refine when the
   error inside the abstraction reaches the error the abstraction induces; existing triggers are transition
   distinguishability or verification counterexamples.
2. *Curiosity-driven imagination: discovering plan operators* (2025) — lifted operators as preconditions plus
   effects learned from symbolic transitions; operators merged when their **effects are identical**.
3. *Autonomous learning of object-centric abstractions* (2022) — objects merged into one type when they react
   **identically** to the same actions; lifting cut 30 operators to 6.
4. Leavens & Pigozzi — behavioural equivalence versus behavioural provability; the inclusion is proper.
5. *Cross-substrate execution identity* (Zenodo, June 2026) — identity must factor through the behavioural
   quotient under a declared observation model.
