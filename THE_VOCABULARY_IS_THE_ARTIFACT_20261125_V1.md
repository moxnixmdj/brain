# THE VOCABULARY IS THE ARTIFACT

**What is real in "solve it once, keep it forever", what is false, and the one relation that decides
both coding and computer use.**

Date: 2026-11-25 · Authority: `NONE__PRODUCER_RUN_SANDBOX` · Branch `arena/9a026570-brain`
Receipt: `canonical/verification/THE_VOCABULARY_IS_THE_ARTIFACT_20261125_V1.json`
Tool: `canonical/tools/the_vocabulary_is_the_artifact_v1.py` · 0 parameters · 0 model calls

---

## 1. The claim, split into the three things it is actually saying

> Instant learning and instant learning in new environments are solved. So give the model the most
> advanced actions once, in every coding environment, and once for anything on a computer, and it
> learns them permanently. Therefore everything on a computer is solved.

| | proposition | status in this tree |
|---|---|---|
| **P1** | one verified experience in a *fixed* environment gives permanent, correct reuse | **partly true.** One verified repair becomes a reusable rule **only after the representation is told what does not matter**: 0 of 304 candidates survived the target's own examples without that, 4 of 384 with it. Retention is real; transfer is conditional. |
| **P2** | one experience per *new* environment is enough for competence in it | **true as a cost law, false as a victory.** Measured on four real machines with opaque atoms: adapting once (29 trials) beats learning each request by demonstration (34 trials) from the second or third request on; crossover **25.78 requests**. It is strictly *worse* for the first request, always. |
| **P3** | therefore every problem on a computer follows | **false**, and this round is the measurement that says why. |

Two more numbers from this tree, because they bound what any "learn it once" story can mean:

* **One demonstration is not identification.** After one demonstration the median surviving program in
  a real hypothesis space is **1037** (max 16480, 10.0 bits); **4 of 23** tasks identified; **7 of 23**
  still insufficient even after every example.
* **An action list cannot grow.** Handing over the "most advanced actions" as a list transferred
  **0 of 20** held-out bugs at any budget; an action *shape* learned from one demonstration fired on
  **1–2 of 20**. What did work was an expression **built from the failure**, because it has no
  precondition to match.

So the honest answer to "isn't this a revolutionary way to make agents learn faster": **yes, in one
specific currency, and no in the currency you need.** It replaces *requests* with *environments*
(measured crossover 25.78), and it does nothing at all for a request whose goal the agent cannot
represent. That second clause is this round.

## 2. What was built, and the five claims declared before it ran

Five real machines, each a real tool over real state, each with its own reader:

| machine | reader | why it is here |
|---|---|---|
| FILESYSTEM | the listing and the bytes | the ordinary case |
| GIT | `git log --format=%H%x09%s` | identity that is not a path |
| TARBALL | `tar -tf` + `tar -xOf` per member | identity inside a container |
| SQLITE | `SELECT id, value FROM t ORDER BY id` | identity that is a row |
| **SORT** | the file's lines, **in order** | the counter-example a real computer hands you: `sort` and `tac` change the file and leave its multiset of lines **exactly** unchanged |

The vocabulary is not a hand-written list of effect names. It is a set of **relations** over the
attested state, and an effect is exactly which relations moved:

```
CARD      how many entities exist
MULTISET  the multiset of contents        (CARD + MULTISET == PERSIST / REMOVE / REPLACE)
ORDER     the sequence of contents
IDENT     the sequence of identities
PAIRING   identity -> content
```

Three vocabularies compete on the same machines: **FIXED** `{CARD, MULTISET}` (what the previous path
could say), **FULL** (all five), and **GOAL_DIRECTED** (the goal's own relation plus the preservation
relation, invented when a request cannot be stated and never carried when it is not needed).

Declared before the run: (A1) ≥3 requests that are **unstateable** under FIXED are **solved** under
GOAL_DIRECTED on ≥3 machines, decided by the machine's own reader; (A2) nothing solved under FIXED is
lost; (A3) GOAL_DIRECTED is strictly smaller than FULL and at least one atom FIXED calls inert is seen
to move; (A4) every inert verdict is reproduced by a second full pass; (A5) 0 model calls, 0
parameters.

**All five met**, in 7.1 s.

## 3. The measurement that matters

| request | relation the user's goal is *about* | FIXED | GOAL_DIRECTED | what solved it |
|---|---|---|---|---|
| one more copy of the new content (FILESYSTEM) | MULTISET | stateable, **solved** | solved | `FS_A1` |
| **move the seed content to a new name** | **PAIRING** | **not stateable → 0** | **solved**, stable | `FS_A3` = `mv` |
| one more member with the new content (TARBALL) | MULTISET | stateable, **solved** | solved | `TAR_A1` |
| **the lines in ascending order** (SORT) | **ORDER** | **not stateable → 0** | **solved**, stable | `SRT_A1` = `sort` |
| **the seed row must hold the new value** (SQLITE) | **PAIRING** | **not stateable → 0** | **solved**, stable | `SQL_A3` = `UPDATE` |
| a new commit object with the same subjects (GIT) | IDENT | not stateable | **not solvable by any offered atom** | see §4 |

**Blindness is not a labelling quibble.** For two of the three recovered requests the atom that
actually does the job is *the atom the fixed vocabulary called inert*:

* `mv` preserves every content and every count → FIXED sees **nothing** → it is not a candidate → the
  rename can never be planned, no matter how many times the agent has "experienced" `mv`.
* `sort` preserves the multiset exactly → FIXED sees **nothing** → the same door, closed.

The third case is a second, different failure mode worth separating: `UPDATE` *is* visible to FIXED
(the multiset changes), but "the row with id 1 must hold this value" cannot be **stated** in a
vocabulary that has no identity→content binding. So there are two ways an insufficient vocabulary
kills a request: it hides the action, or it cannot express the goal. Both were measured here.

Measured distinguishability, the vocabulary's actual information:

| machine | atom pairs distinguishable under FIXED | under FULL |
|---|---|---|
| FILESYSTEM | 6 | 7 |
| SORT | 3 | 5 |
| GIT / TARBALL / SQLITE | 8 / 4 / 5 | 8 / 4 / 5 |

## 4. A negative finding, recorded rather than massaged

The GIT request — *a new commit object with the same subjects* — is **not reachable by any offered
atom**, and the tool proves it: `git commit --amend --allow-empty -m <the same message>` inside the
same second produces a **byte-identical commit** (`hash_before == hash_after`). Identity in git is a
function of tree, parent, message **and dates**, so "new object, same content" requires a metadata
change, not a content change. The row is excluded from A1 with that reason attached, not silently
counted as a vocabulary failure.

## 5. What the frontier actually measures, November 2026

Not "has it seen the action". The hardest open computer-use benchmark, **OSWorld 2.0** (108
long-horizon tasks, 31 self-hosted sites, ~27 scoring checkpoints each), reports best binary success
**20.6%**, and its authors' own diagnosis of where everyone fails is:

> "All current agents are weak at recovering and maintaining hidden state. The lowest-scoring
> phenomena are those that demand state the instruction does not provide."

That is the same wall this round measures on CLI machines, in the same words: *state the goal is
about*, not actions to be copied. On the coding side, the frontier's answer to that wall is
**predicate invention** — dynamic predicate invention with meta-interpretive learning (arXiv
2602.17217, Feb 2026), `TheoryCoder-2` growing a library of learned predicate classifiers (arXiv
2602.00929, Jan 2026), `ExoPredicator` inventing a predicate vocabulary from 1–2 demonstrations
(ICLR 2026) — and every one of those systems **proposes predicates with a language model** and then
selects among them.

This round does the same job with **no model at all**: the relations are computed from the machine's
own reader, and the vocabulary is admitted only where a goal needs it. That is the difference between
"a frontier system that guesses its abstractions" and a system whose abstractions are **calculated**,
which is the only kind this project is allowed to keep.

## 6. What is real, what is false

**Real.**
* Learning an environment's atoms once is a genuine, measured win over learning each request by
  demonstration — from the second or third request onward, at 0 parameters, with the machine's own
  reader as the only judge.
* An effect *is* a computable object: it is the set of relations that moved between two readings.
* A vocabulary can be **grown on demand** from the reader, and it then converts requests that were
  impossible into requests that are routine.

**False.**
1. **"Give it the action once and it has the capability."** `mv` was experienced in every cell of the
   probe table, twice, and the agent still could not take the rename request — because the effect it
   produces is invisible to the vocabulary it carries. Experience without a relation is not experience
   of anything.
2. **"Repetition fixes it."** It cannot. A thousand observations of an invisible change are a thousand
   observations of nothing. This is exactly the insufficiency certificate, now measured on five real
   machines.
3. **"So everything on a computer follows."** The vocabulary is a **grammar, not the world**. A state
   difference outside `{CARD, MULTISET, ORDER, IDENT, PAIRING}` — permissions, ownership, pixels,
   widget trees, scroll offsets — is invisible to all three vocabularies here, including the induced
   one. OSWorld 2.0's hardest phenomena are precisely the ones that need relations nobody wrote down.
4. **"One demonstration identifies the rule."** Median 1037 surviving programs after one demonstration;
   4 of 23 tasks identified. What one demonstration gives is a *consistent* hypothesis, not an
   identified one; that is what the counterfactual verifier is for, and it is why the demand has to be
   a relation that can be intervened on.

**On sentience.** A creature is not the mechanism. What the measurements keep pointing at is a
**model of state that the agent maintains and can intervene on**: which relations the world has, which
one the goal is about, and which action moves it. Nothing in these receipts needs a feeling; everything
in them needs a relation. If there is a defensible meaning of "sentient" for this project it is that
the system keeps a *live, falsifiable* model of the world rather than a store of demonstrations — and
that is a property you can test, which is the only kind worth claiming.

## 7. The single bottleneck, in one sentence

> **The set of relations the system can state about a running system.** Identifiability is downstream
> of it (you can only identify a hypothesis over observables you have), and the
> synthesis–verification asymmetry is downstream of it (you can only verify a relation you can state).
> Every other limit this tree has cleared — vocabulary size, search cost, oracle exactness, stored
> parameters — was cheap by comparison.

## 8. The next crossing, named so it can be falsified

Today the goal arrives *with* its relation ("the lines must be ordered"). The remaining step is
**goal-directed relation invention**: when a request cannot be stated in the current vocabulary, search
the relation grammar for the **separator** between states a user accepts and states a user rejects, add
exactly that relation, and then plan. Concretely, on the same five machines: pairs of accepted/rejected
states (real ones, produced by real tools), a grammar of relations over the reader's output, and the
acceptance that the invented relation must (i) separate every given pair, (ii) be the *smallest* such
relation, and (iii) turn at least one previously unstateable request into a solved one — with 0
parameters and the reader as the only judge. That is the point where the vocabulary stops being a
design decision and becomes something the machine computes.

## 9. Accounting

| | |
|---|---|
| machines | 5, all real tools (`mv`, `git`, `tar`, `sqlite3`, `sort`), each with its own reader |
| adaptation | every atom in 4 cells (2 state classes × 2 argument bindings), **twice**, so "inert" is never one run old |
| requests | 6 declared, 5 counted, 1 excluded with its measured reason (git identity) |
| A1 | 3 requests unstateable under FIXED, **solved** under GOAL_DIRECTED, on 3 machines, stable on a second read |
| A2 | nothing lost |
| A3 | GOAL_DIRECTED uses 3 of 5 relations; **3 atoms** FIXED calls inert are seen to move |
| parameters / model calls | **0 / 0** |
| wall clock | 7.1 s |
| tests | 4 new, all passing; the three prior suites still green (39) |
| declared acceptance | **all five met** — and the one claim that could not be met (git) is excluded and explained, not counted |
