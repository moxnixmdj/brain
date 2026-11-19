# The pre-state is the missing part

*Round dated 2026-11-16. Receipt: `canonical/verification/THE_PRE_STATE_IS_THE_MISSING_PART_20261116_V1.json`.
Tool: `canonical/tools/the_pre_state_is_the_missing_part_v1.py`. Tests: 13, all green, 36.5 s. No model, no
weights, no parameters, no network at run time. The systems under test are GNU tar, GNU coreutils and
SQLite, executed; nothing here is a model of them.*

---

## 0. The answer on one page

The previous round ended with a residual it called irreducible: two sentences of the goal that no run of
three machines could tell apart,

```
created_once[probe_new_content]          vs          monotone[probe_new_content] ∧ final:count==1
```

priced at `log2(2) = 1` question of the user, with "runs that could pay it: 0". That was reported as a
fact about the world. It is not. It is a fact about **the first state of every run this project has ever
executed**, which was always the machine's reset state.

Start from reset, let the probe count begin at zero, let every atom change it by at most one — both
measured here, not assumed — and the two sentences are the same sentence:

```
created_once  ⟺  exactly one increase and no decrease  ⟺  monotone and final count = 0 + 1 = 1
```

No depth, no number of runs, no fourth environment and no fifth relation can separate them, because
arithmetic has already decided the answer. The residual was the experimenter's convention.

Put the first state back where it belongs — wherever the machine already is — and the pair comes apart in
**two real actions**:

```
write the probe content to `seed`   →   copy `seed` to `copy`
count 1                                    count 2
created_once = true                       monotone ∧ count==1 = false
```

Eight substantive witnesses on two machines, all accepted by the tool, zero questions of the user. On the
widened suite the user's goal stops being a class of two sentences and becomes one: the **conjunction**
`created_once ∧ final:count==1`. The world answered the question the last round said only words could
answer. That is the whole round.

## 1. What the last round actually measured

Three premises made the equivalence unavoidable, and all three are now in the receipt as measurements:

1. **The first state.** `runs.traces_for` resets the machine and executes from there. Every one of the
   previous rounds' 555, 231, 196 and 128 runs began in the same state, so every trace's first count was 0.
2. **Unit steps.** From every reachable pre-state, every atom of every machine moves the probe count by
   −1, 0 or +1 — `{TARBALL: [-1,0,1], FILESYSTEM: [-1,0,1], SQLITE: [0,1]}` over 80 real experiments.
3. **No decrease ⇒ final = start + increases.** With the count starting at 0 and exactly one increase, the
   final count is 1. `created_once` therefore *implies* `monotone ∧ count==1`; and the converse is the same
   arithmetic read backwards.

On a fresh standard suite of 203 runs (87 tarball, 68 filesystem, 48 SQLite, at depths 4/3/3) the pair
disagrees on **zero**. That is not evidence about tar, coreutils or SQLite. It is the theorem being
confirmed where it is forced to hold.

The fidelity pin matters for comparability: `walks` keeps the *sequences* that `traces_for` throws away, and
its traces are byte-identical to `traces_for`'s on all three machines, so the previous rounds' numbers and
these are the same runs.

## 2. What is real, and what is false

| Claim | Verdict |
|---|---|
| The previous receipt's pair could not be separated by any run of three machines | **False as stated.** It could not be separated by any run *beginning at reset*. One action from a real pre-state separates it. |
| `log2(2) = 1` question of the user is the price of the residual | **False.** The price is 0 questions and 2 actions — one to reach the state, one to act in it. |
| The residual is information only language can supply | **False.** It was information the suite threw away by fixing its first state. |
| The user's goal is identified by experience | **True on the widened suite**: the class falls from 2 statements to 1, and the survivor is the conjunction. Identified over the supplied grammar, on these runs. |
| Widening the suite is free | **False.** Behaviours go from 429 to 649; every added behaviour has to be pinned by its own statement. The pair's class falls; the accounting grows. |
| A machine's reader is part of the vocabulary | **True, again, measured**: on TARBALL a second copy of the same bytes is *unobservable* (§6). |
| This is coding capability | **False.** No edit is composed here. This says what an edit would have to satisfy. |

## 3. The witness, and what it cost

Eighty experiments: every distinct pre-state reachable in at most two real actions (5 tarball, 8 filesystem,
7 SQLite, 5 exercised), times every atom of its machine. Each experiment resets, replays a real prefix,
**reads the machine and refuses the experiment unless the recorded pre-state was reproduced exactly**, then
executes exactly one real atom and reads the result. Nothing was fabricated: `not_reproduced = 0`.

- **25 of 80 experiments separate the pair.**
- **8 are substantive** — the action changed the count. All eight are `created_once` without the single-copy
  sentence, all on FILESYSTEM or SQLITE, all exit 0.
- The first one, in the declared order, is one action from reset plus one action: FILESYSTEM `FS_A1`
  (write the probe content to `seed`), then `FS_A4` (`cp seed copy`). Count 1 → 2. `created_once` true,
  `monotone ∧ count==1` false.

Two actions. Not one question. And the previous round's "0 runs could pay it" was true only inside its own
suite.

## 4. The asymmetry, and why it is not a gap

The other direction — the single-copy sentence true while `created_once` is false — **cannot be substantive**,
and this is provable from the same premises: on a run with no decrease and unit steps, `count(final) =
count(start) + increases`; the sentence requires `count(final) = 1` and not exactly-one-increase, so
`increases = 0` and `count(start) = 1`. Nothing may change. There is no missing experiment; the direction is
structurally a do-nothing run.

The world supplies those too, and the receipt counts them: 17 degenerate separations, of which **15 are
no-ops the tool accepted** — writes over identical content, a copy whose source is unchanged, a plain
listing — and 2 are refusals (`mv` of a name that is not there, `tar --delete` of a member that is absent).
So the second branch of the residual is refuted by a run in which **nothing happens**, typically by a read.
That is exactly why it could not be refuted from reset: from reset there is no state holding one copy to do
nothing in.

This is the sharpest form of the finding. The previous round's "irreducible" ambiguity was not deep. It was
one `ls` away from a state nobody had ever been in.

## 5. The goal is decided, and the accounting is honest

Over the same 189-term grammar the previous round used (17 955 hypotheses, term set held fixed so the
comparison is not a change of vocabulary):

| | standard suite | widened suite |
|---|---|---|
| runs | 203 | 283 |
| behaviours | 429 | 649 |
| the goal's minimal statements | **2** | **1** |
| the goal's minimal text | `created_once` · `monotone ∧ count==1` | `created_once ∧ final:count==1` |

Neither branch alone survives: `created_once` is refuted by a real duplication (true where the goal is
false), and `monotone ∧ count==1` is refuted by a read from a one-copy state (true where the goal is false).
What survives is their conjunction, and it is the only minimal statement with the goal's behaviour on these
runs.

Two honest limits. First, "identified" means: on this suite, over this grammar, the goal's behaviour has one
minimal statement. It is not a proof about all runs. Second, adding runs *cannot* add statements to a class —
consistency is monotone — so the fall from 2 to 1 is not a fluke of the accounting; the rise from 429 to 649
behaviours is the real cost, and it is stated in the same table.

## 6. On the tarball, the second copy does not exist

TARBALL offers no substantive witness, and the reason is worth more than the witness. From a state holding
one copy, no atom of that machine increases the count (`{TAR_A1: −1, TAR_A2: −1, TAR_A3: 0, TAR_A4: 0}`).
Asked directly: delete the seed member, append the probe bytes as `seed`, append them again as `seed` — two
members, same name, same bytes, both exits 0. The reader then reports

```
seed2 | probe_second_content
seed  | probe_new_contentprobe_new_content
seed  | probe_new_contentprobe_new_content
```

— the same as it reports one member, doubled. **The count goes from 1 to 0, not to 2.** On this machine a
second copy of the same bytes is not observable at all, so no statement can be about it. This is the earlier
round's law returning at a finer grain: the vocabulary is not the atoms, it is the atoms *and the reader*.

## 7. What this does to "give it the actions once"

Three ceilings have now been announced by this project and then withdrawn:

1. *the vocabulary* — five hand-written relations were the world's language (withdrawn when the machines'
   own readers were used);
2. *the machines* — three environments were the world (withdrawn when breadth saturates at 2 statements);
3. *the initial state* — reset was the world (withdrawn here).

Each withdrawal has the same shape: **a limit that looked like a property of the world was a convention of
the experiment.** Every one of them was found by asking what the experiment held fixed, not by running more.

The claim under test — *hand it the most advanced actions once, learn them permanently, and computer use
follows* — is therefore neither confirmed nor refuted; it is **unpriced**, and each price we publish turns
out to be a convention. What is now measured is the direction of the next price: an action does not have one
meaning. It has a meaning **per pre-state**, and a suite that fixes the pre-state has thrown that meaning
away before it starts.

The classical mechanism for exactly this is preconditions — QuickCheck's and PropEr's state machines require
each command to declare the states in which it is legal, precisely because a command's effect is a function
of the state it is applied to. Our atom model has `Atom(ident, steps)` and no precondition. That is the part
that is missing, and "the best part is no part" says the fix is not more atoms, more machines or more runs:
it is the pre-state, one field, already implicit in every real command.

The 2026 evidence outside this sandbox points the same way. Benchmark analyses this year separate *task
difficulty* from *world richness* and observe that almost all software-engineering evaluation sits in
"controlled workbenches": a fixed objective, a fixed initial state, a verifier, a reset. Stateful and
continual-learning benchmarks (CL-Bench, STATE-Bench) exist because stateless resets hide whether anything
was learned at all. Every SWE-bench-style harness rebuilds the repo at a base commit before the agent runs —
our `reset()` with a git remote. If the pre-state carries the meaning of an action, then a benchmark that
fixes the pre-state cannot measure the part of capability that consists of acting from a state you did not
choose, which is the state every real machine is in.

## 8. The single bottleneck

Not the number of runs: the previous round ran 555 and this one separates its residual with 2 actions. Not
the size of the vocabulary: 189 terms were enough, and the limiting vocabulary turned out to be a *reader*.
Not the number of environments: the third bought nothing.

**The bottleneck is that every experiment this system runs starts from a state it chose.** Reset, clone,
`git checkout`, fresh container — the same move each time, and it is the move that deletes the pre-state.
Capability that is not being bought is the capability to act from an arbitrary state, which requires
(i) experiments parameterised by a real pre-state, (ii) statements whose truth is judged against the run that
starts there, and (iii) an edit composed and repaired against execution *from that state* rather than from a
clean checkout.

One sentence: **the runs are not the scarce thing; the states you are allowed to start from are.**

## 9. Named limits

1. Pre-states are those reachable in at most two real actions, capped per machine. The closure of the state
   space is not enumerated, and states unreachable within two actions are not tested.
2. The theorem's premise is measured on the states exercised, not proved for every state of every machine.
3. The goal's identification is relative to a supplied 189-term grammar; a goal outside it is refused.
4. The conjunction's equality with the goal's behaviour is measured on 283 runs, not proved.
5. The degenerate direction is *necessarily* degenerate under unit steps; a machine with an atom that creates
   two copies in one action would change that, and the receipt names it as the falsifier.
6. TARBALL's reader conflates same-name members; that is a property of GNU tar's extraction, and it limits
   what any statement about that machine can say.
7. **No edit is composed.** This is still the pricing of coding capability, not coding capability.

## 10. Pre-registered next step

The next round must move from "a state the experimenter chose" to "a state the repo is in", and it must be
falsifiable in advance:

- Take a real repository task whose goal is judged by real tests. Pre-state = the working tree as it is,
  including uncommitted changes and a failed prior edit; the prefix that reaches it is `git stash`/`apply` or
  the reflog, executed, not simulated.
- **Prediction:** at least one pair of goal statements that no clean-checkout run can separate becomes
  separable by a run beginning from a dirty tree, at a price of at most three real actions and zero questions.
- **Falsifier:** if, on the first real repo, every residual pair is separated by the clean-checkout suite
  alone, then this law is local to file-and-archive machines and must be withdrawn. If the dirty-tree suite
  separates the pair only by *refusing* to run (non-zero exits), it counts as nothing.

The tests for the next round are the repository's own: real, unmodified, and run only by this system.

---

*Authority: NONE. Producer-run sandbox measurement, 36.6 s, 13 green tests, 0 model calls, 0 stored
parameters, 0 network calls at run time. Every number above is a field of the receipt, and the receipt
recomputes to itself.*
