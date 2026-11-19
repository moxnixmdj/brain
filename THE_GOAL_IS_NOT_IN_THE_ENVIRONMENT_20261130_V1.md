# The goal is not in the environment

**2026-11-30 · branch `arena/19801aff-brain` · receipt `canonical/verification/THE_GOAL_IS_NOT_IN_THE_ENVIRONMENT_20261130_V1.json`**

---

## 1. The claim, and the thing every earlier round quietly supplied

*Instant learning is perfect. Instant learning in a new environment is perfect. So give the model the
smartest actions once, let it experience each once, and every task on a computer is solved — permanently.
Is that right?*

Four rounds answered parts of it: the goal is a quotient of the trace (k cells); its refinement costs one
counterexample and one question; a conflation is not an error; and the table learned at depth 3 answers
every decided run at depth 5. Read alone, that chain is nearly the user's claim.

But every one of those rounds **handed the goal to the agent**. `portable_judge` is a predicate I wrote,
and the measurement then asked how cheaply a *statistic of that predicate* could be found. The user's
claim is not about a statistic. It is about the goal: *the agent learns what to do.* So this round removes
the handed-in goal and asks what experience can say about the objective itself.

The answer is exact, and it is not the one the claim needs.

## 2. What is false

1. **False: that experience identifies the goal.** On TARBALL's reachable set — 231 real runs, all
   sequence lengths up to five — the goal grammar holds **11 935 hypotheses** and they express only
   **353 distinct behaviours**. Judgment is a function of the *behaviour*, so 11 935 hypotheses collapse
   to 353 answers and no experiment can do better. The user's own goal is stated exactly by **79
   different statements**; they are one behaviour, and nothing this machine can do separates them.
2. **False: that what is learned stays true "permanently", in a new environment.** Four genuinely
   different intentions — *the seed content is never absent*, *its count never falls*, *exactly one copy
   at the end*, *that identity holds it* — are **the same statement on all 231 TARBALL runs**. On the
   next machine they disagree on **32 of 196 runs**, the first of them the run where the content is
   copied twice and one copy is replaced. The class did not just get refined: it split, exactly where the
   first environment never went.
3. **False: that asking more fixes it.** Asking is genuinely cheap and near-optimal — 8 judgments carry
   **8.46 bits**, the information-theoretic maximum for 353 behaviours — but no number of judgments
   separates two statements the environment cannot distinguish. The ceiling is a fact about the world,
   not about the learner, and no policy reaches past it.
4. **False — and this is my own error, made four rounds running: that I was measuring the goal.** I was
   measuring a supplied predicate. The receipt now makes the supply visible in a number:
   `user_goal_stated_exactly_count = 79`. Seventy-nine statements, all equally consistent with everything
   the user ever said, because the user never said anything — I wrote the predicate.
5. **False: that any of this is sentience, intention, or understanding.** What the agent ends with is a
   behavioural class. Understanding an intention is a different object with a different price, and this
   round's contribution is to *separate* the two rather than blur them.

## 3. The measurement

The grammar is the one already in this repository (`run_terms`): terms over the whole trace — *never
removed*, *monotone*, *created once*, *two copies*, *never together*, *precedence*, *present then absent*
— plus terms that may read only the final state, closed under conjunctions of two. Every hypothesis is a
bitmask over the runs the environment can produce, so two hypotheses are indistinguishable **exactly**
when their masks are equal. That is not "unidentified today"; it is "unidentifiable here, forever".

On top of that, three things are measured:

* **the resolving power** — how many distinct behaviours the environment can exhibit, and how many
  statements carry each one;
* **the price of asking** — judge the run whose judgment splits the surviving behaviours most evenly,
  refit, repeat to one behaviour, against judging runs in the order the environment offers them;
* **the transfer** — take a pair that is identical on every reachable run and evaluate it on the other
  machine, which is the only test of "permanently" that can fail.

The environment control is a **previously registered prediction**: last round pre-registered that any
verdict error at depth 5 kills "the table travels". It is reported, not re-declared.

## 4. Results

| | TARBALL | FILESYSTEM |
|---|---|---|
| reachable runs (deepest affordable) | 231 at depth 5 | 196 at depth 4 |
| terms / hypotheses | 154 / 11 935 | 43 / 946 |
| **distinct behaviours** | **353** (8.46 bits) | **129** (7.01 bits) |
| statements stating the user's goal exactly | 79 | 11 |
| behaviours after every run is judged | 1 | 1 |
| active judgments to one behaviour | **8** | **6** |
| behaviours left after 8 judgments in the environment's order | **20** (323 survivors) | 11 (32 survivors) |

The active sequence on TARBALL is `353 → 176 → 89 → 29 → 14 → 7 → 5 → 2 → 1`: eight questions for
8.46 bits, within one question of the bound. The environment's own order — the first eight runs it
happens to offer — takes the same 8 judgments and ends at **4.32 bits**. Same budget, half the knowledge.

**The ceiling, concretely.** Four statements, one behaviour, on all 231 runs:

```
never_removed[probe_seed_content]        the content is in every state of the run
monotone[probe_seed_content]             its count never falls
final:count[probe_seed_content]==1       exactly one copy at the end
final:has[seed]=probe_seed_content       that identity holds it
```

All four accept the same 5 runs of 231 and reject the other 226. TARBALL cannot duplicate-then-reduce a
content, so *never absent* and *never falling* are the same sentence there. FILESYSTEM can, and they
differ on **32 of 196** runs.

**The environment is known exactly.** The depth-3 statistic and its table, applied to 231 runs never
measured on: **229 decided, 0 false accepts, 0 false rejects, 2 abstentions**. The machine is learned once
and stays learned. The goal is not, and the difference between those two sentences is this round.

## 5. The criteria, as declared before the run

| | |
|---|---|
| G1 the grammar can state the user's goal exactly | **MET** — 79 statements on TARBALL, 11 on FILESYSTEM |
| G2 two different statements, one behaviour, on every reachable run | **MET** — a class of 4, non-trivial, in vocabulary both machines share |
| G3 that pair separates on the other machine | **MET** — 32 of 196 runs |
| G4 active questions isolate one behaviour in ≤ 8 judgments, ordered needs more | **MET** — 8 vs 20 behaviours left at the same budget |
| G5 zero model calls, zero parameters | **MET** |
| environment control (registered last round) | **MET** — 229/231 decided, 0 errors, 2 abstentions |

The witness filter was **declared before the run**, because the first witness the code produced was
trivial — two statements false on every run, "indistinguishable" for no reason. A competing intent must
be non-trivial (true somewhere, false somewhere) and stated in vocabulary both machines share. Both
conditions are in the docstring and in the receipt; without them this round would have proved nothing.

## 6. The law

> **Experience identifies a behaviour, not an intention.**
>
> An environment has a finite resolving power — here 353 behaviours over 11 935 hypotheses — and that
> number is the ceiling of everything any amount of experience can buy inside it. Active questions reach
> the ceiling in its own logarithm (8 questions for 8.46 bits) while the environment's own order reaches
> half of it for the same price. What the questions leave is a class of statements with one behaviour, and
> that class is exactly what a *new* environment splits: the pair that is one sentence on 231 runs of one
> machine is two sentences on 32 runs of the next. So "learn it once, permanently" is true of the
> behaviour and false of the goal, and the difference is not a detail of the learner — it is the
> environment's reach.

## 7. What is real and what is not

**Real.** The machine model: 229 of 231 decided correctly at a depth it was never measured on, zero
errors. The resolving power of an environment is computable, and small. Asking is near-optimal: 8
questions for 8.46 bits, with the surviving set shrinking 353 → 176 → 89 → 29 → 14 → 7 → 5 → 2 → 1.
The ceiling is not rhetoric: four named intentions, one behaviour, executable and re-derivable.

**Not real.** "Give it the action once and it has the goal." It has a behaviour class. "Permanently, in
any environment." The class splits in the next environment, at 32 of 196 runs, and the split is exactly
the boundary of the first environment's reach. "Just ask more." Asking is optimal already; the ceiling is
not a budget problem. "We solved instant learning of the goal." We solved instant learning of a supplied
predicate's statistic — four rounds of it — and the receipt now says so in a count.

**On sentience, plainly.** Nothing here is sentience and nothing here needs it. The missing object is not
a mechanism inside the learner; it is the user's preference, which is not a function of the runs the
machine can produce. That is why the honest name for what was built is an *identification machine*, and
why "we were trying to make it sentient" and "we were trying to learn the goal from experience" are the
same sentence about a limit that lives in the environment, not in the model.

## 8. The single bottleneck

**The goal's equivalence class on the reachable set — that is, the environment's resolving power.**

Not the weights (zero), not the statistic (3 cells), not the questions (8, and near-optimal), not the
vocabulary of terms (154 terms, and the user's goal is among them). What is left is a class of statements
that the world cannot separate, and the class shrinks only in one way: **by breadth of experience, not by
repetition of it.** Repetition adds runs to a set that is already saturated — 231 runs, 353 behaviours,
and the 231st run teaches nothing the 200th did not. A *third machine*, or a deeper one, is the only thing
that removes a coincidence. That is the whole prescription, and it is a fact about the world rather than
about the learner.

## 9. Next step, pre-registered

**Intersect the classes across environments.** The pair that is one sentence on TARBALL is two sentences
on FILESYSTEM; so intersecting the statements consistent with *every* run of *every* machine is the
honest measure of how much of the goal breadth of experience can buy. Pre-registered falsifiers:
(i) if the intersection, up to behaviour, is a single statement, then "experience in many environments
identifies the goal" is TRUE and the user's claim survives in its strong form;
(ii) if it is more than one, the residual is the part only the user can say, and its size is the price of
asking *them* rather than the machine;
(iii) if adding the third machine removes fewer statements than the second did, breadth is saturating and
the residual is structural.

Corpus, stated plainly: **this is not SWE-bench.** Two CLI machines, executed here, 158 s, no network at
run time, no model, no parameters. Depth 5 is the deepest this sandbox affords (231 runs in 76 s); depth 6
is named as out of reach, not simulated.
