# One try learns a domain, not an environment

*Measured on a real repository, 2026-11-16. Receipt: `canonical/verification/ONE_DEMONSTRATION_BASIN_20261116_V1.json`.
Instrument: `canonical/swe_kernel/one_demonstration_basin_v1.py`. Reproduce with one command (§7).*

## 1. The claim, stated so it can be checked

"Let the model try a task in a new environment, do it once, and it has learned it permanently; do that
everywhere and computer use and advanced software engineering are solved."

A demonstration is an action sequence. Its *domain* is the set of starting states from which that
sequence reaches the goal — a fact, not an opinion. So the claim is a claim about a domain: how big it
is, whether the agent can tell when it is inside it, and whether what it cannot tell can be learned by
trying again. All three are measurable, and none of them needs a model to be believed.

## 2. How it was measured

A real `git` repository in a throw-away directory, ten real actions (write two files, write an ignored
file, stage two files, commit, delete a file, branch, hard reset), a real index, real refs, real
refusal to commit when nothing changed. Commits run on a fixed clock and the index is compared by its
staged content, so an action from a state returns to that state: without that the model is unbounded
and the measurement would be meaningless.

Then every action was executed from every reachable state: **168 semantic states, 1,680 real
transitions, nothing truncated**. That is the honest price of knowing the answer — the same
|S| × |A| that `systematic_exploration_v1` charges, which is exactly why nobody pays it in a GUI.

Three tasks on that one environment:

| task | goal |
|---|---|
| A | work committed as `c1`, tree clean, `a.txt` still present |
| B | A, and `a.txt` commits as `two` (needs one file's content) |
| C | A, and `b.txt` is *still* `one` — a premise the demonstration never sets |

Task C is the real shape of work, and of SWE: the plan writes one thing, and whether it is correct
depends on something else that was already true or already false before the plan ran.

## 3. The demonstration is not the environment

The most charitable single demonstration that exists — the shortest plan from the start state, found
on the true model — reaches the goal from **112 of 168 states for task A and B, 56 of 168 for task C**.
One success therefore licenses, at most, two thirds of the environment and, for a task with a premise,
one third of it. Nothing about permanence changes that: the plan is stored perfectly and still does
not apply to two thirds of the states the environment actually offers.

## 4. What the agent can *tell* — the part that decides everything

A plan that works is not the same as a plan the agent is entitled to run. Every state was grouped by
what the agent perceives, and each group was checked against the plan's exact domain:

* **licensed** — the whole group is inside the domain: the agent may trust the plan;
* **lucky** — inside the domain, but the same look also occurs outside it: a coin that already landed;
* **silent failure** — outside the domain, while looking exactly like a state where it works;
* **clear outside** — outside, and visibly so: another plan is needed, and the need is visible.

Task C, under four sense vocabularies and one control:

| sense | looks | licensed | lucky | silent failure | clear outside | undecidable |
|---|---|---|---|---|---|---|
| status | 64 | 48 | 8 | **16** | 96 | **24 (14.3%)** |
| status + content(`a.txt`) | 80 | 48 | 8 | 8 | 104 | **16 (9.5%)** |
| status + content(all files) | 168 | **56** | 0 | 0 | 112 | **0** |
| status + content(all) + staged blobs | 168 | 56 | 0 | 0 | 112 | 0 |
| **command output only** (control) | **3** | **0** | 56 | **112** | 0 | **168 (100%)** |

Read the third row and the first row together. **The knowledge did not change — the senses did.** The
same demonstration, on the same states, is licensed on its whole domain once the sense carries the
fact the goal depends on, and it is undecidable on 14.3% of the environment when it does not. Reading
only `a.txt` (row two) removes a third of that doubt and no more: the residue is precisely the part
of the goal that lives in the file nobody opened.

The control is the important one for anyone who thinks the agent's feedback rescues it. A real agent
also reads `git`'s output — exit codes and messages from the three commands it just ran. Measured as
an observable, that collapses 168 states into **3** classes, and **no class is entirely inside the
plan's domain**: 112 states run the demonstration, watch it succeed, and are wrong. Command output
says what the tool did, not whether the goal is true. It is coarser than the state, not finer.

Licensing the whole environment takes **4 demonstrations** for task A and **1** for task C, with
**4 groups no demonstration can license at all** under the status sense — the same 4 that make up the
undecidable set. The environment has 9 decision classes for task C and 14 for task B by the tree's own
`k6` quotient, so "one demonstration per environment" is short by an order of magnitude even when
every demonstration is perfect.

## 5. What this settles

**Real.** A demonstration identifies a *sequence* and, with it, a domain — and the domain is a property
of the environment, checkable by execution. That part is solid, and it is what makes memory useful:
it tells you where to try first.

**False.** That a demonstration teaches the environment. It teaches one trajectory through it. The
environment is the 168 states and the transitions between them; the demonstration is 3 of those
transitions. Nothing about storing it, in weights or elsewhere, converts 3 transitions into 168.

**False, and this is the sharper one.** That more attempts close the gap. The undecidable set is
invariant to experience: if two states produce the same perception and need different actions, no
policy keyed on the perception can be right on both, however many times you visit them. Trying again
teaches the agent *which* perceptions are undecidable, which is valuable — but it is a different
lesson from the one the claim asserts.

**The single bottleneck: the premise.** Not the store, not the parameters, not the plan, not the
speed of replay. Whether the fact the plan depends on is *observable at the moment of acting*. Every
number in §4 moves with that one thing and with nothing else. This is the same bottleneck the drift
receipt reached from the other side — 31.1% of replays were silently corrupt because the plan's
premise had moved without a signal — now measured on a closed environment where the ground truth is
fully known: 14.3% of states are undecidable at the status sense, 0% when the sense carries the
premise, and the plan's true domain never changes.

## 6. What follows for the architecture

1. **A demonstration yields a guarded plan, never a rule.** The guard is the premise, checked on the
   live state before the first action; the postcondition is the goal, checked after the last. A plan
   with no checkable premise is not reused, it is gambled.
2. **Spend on senses, not on demonstrations.** Adding the file-content sense moved the licensed set
   from 48 to 56 and the undecidable set from 24 to 0 with no new experience at all. Adding a tenth
   demonstration moves nothing. Whenever a state is undecidable, the cheapest correct repair is to
   make the decisive fact observable — that is what a test *is*.
3. **Where neither is possible, refuse.** The 4 groups no demonstration can license are not a
   training problem; they are the places where acting on memory is a bet, and the only honest move is
   to abstain or to instrument.

## 7. Reproduce

```
python3 canonical/swe_kernel/one_demonstration_basin_v1.py --max-states 400 \
  --json canonical/verification/ONE_DEMONSTRATION_BASIN_20261116_V1.json     # ~65 s
python3 -m pytest canonical/tests/test_one_demonstration_basin_v1.py -q      # 6 passed, ~59 s
```

## 8. What this does not claim

No capability credit, no benchmark rank, no terminal credit, no independent verification. The
environment is `git`, not a GUI; the three tasks are goals on one environment, not three
environments; the states are those reachable by a ten-action hand. What it claims is narrow and
reproducible: on this environment, with the best single demonstration that exists, this much of the
task is licensed, this much is luck, this much fails while looking like success, and this much no
further demonstration can decide — and here is exactly what one more sense is worth, on the same
states.
