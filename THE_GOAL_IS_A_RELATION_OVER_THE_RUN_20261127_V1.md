# The goal is a relation over the run

**2026-11-27 · branch `arena/58fe5965-brain` · receipt `canonical/verification/THE_GOAL_IS_A_RELATION_OVER_THE_RUN_20261127_V1.json`**

---

## 1. What was asked

The standing claim, again, in the user's words: *instant learning is perfect, and instant learning in a
new environment is perfect; therefore give the model the most advanced coding actions once, let it
learn them permanently, and everything on a computer — including the most advanced software
engineering — is solved.* And: *what is real, what is false, and what is the single bottleneck that, if
fixed, unlocks the most capability?*

Four rounds answered the identification half: the goal is a relation over the reader (not an effect
name), it can be inferred from judgments instead of handed in, and ambiguity is settled by asking the
question that splits the survivors and acting on their intersection. Every one of those rounds read the
goal off **one state**. This round asks the question that construction leaves open:

> If two runs end in exactly the same state, can any goal over states tell them apart?

No. Not "not well". **No conjunction of anything you can read off the final state can separate them**,
because they are the same input to it. So the goal has to be a relation over the run.

## 2. What is false in the claim

1. **False: that the action is the unit of learning.** The unit is the relation the goal is about. An
   action demonstrated once carries its *state* transition; the user's goal usually also contains the
   *history* — that the backup came before the move, that the member was written once and not deleted
   and re-written. That part is invisible to every state-level account, including ours of the last four
   rounds.
2. **False: that "learn the action once and keep it" is a well-posed unit.** Measured here: 323 real
   action sequences collapse to 136 distinct traces, and 9 final states are reached by runs the user
   judges oppositely. A learned action that only knows its end state is not a weaker version of the
   right thing; it is a thing that cannot represent the right thing.
3. **False: that more experience or more questions fix it.** The end-state vocabulary is *empty* on
   these judgment sets — not wrong, empty — and it stays empty with all 136 judgments. There is no
   sequence of questions about final states that recovers the goal, because the answer is not a
   function of the final state.
4. **False: that any of this is software engineering capability.** Three CLI machines, three actions
   deep, a judge that this tool wrote. It is the *structure* of the goal that is being fixed, not the
   frontier.
5. **False (and this one is about us): that agreement is proof.** The end-state grammar reached
   agreement in 4, 7 and 2 questions and agreed on a goal that is wrong 18 %, 21 % and 5 % of the time.
   A stopping rule that says "all survivors agree" is only as sound as the grammar's completeness, and
   that completeness is exactly what the final-state vocabulary lacks.

## 3. The experiment

Three real machines from the existing tool (`instant_learning_in_a_new_environment_v1`): FILESYSTEM,
SQLITE, TARBALL. Real `sh`, `mv`, `cp`, `rm`, `sqlite3`, `tar`; the machine's own reader is the only
observable. Every action sequence of length one to three was executed from a fresh reset, the reader
was sampled **after every step**, and sequences whose reading is identical at every step were merged
into one run (two action sequences that read identically are one observable). 323 sequences → 136 runs.

Three goals, never shown to the agent, judged by a predicate over the whole trace:

| machine | goal the user means |
|---|---|
| FILESYSTEM | *copy it before you move it*: the original content existed in two places at once |
| SQLITE | *replace the row in place*: the old value and the new value never coexisted |
| TARBALL | *add the member once and keep it*: exactly one write, never removed |

Two grammars over the same runs:

- **final-state only** — every term that can read `trace[-1]`: cardinality, per-content counts, and
  which identity holds which content. This is the entire vocabulary of the previous four rounds.
- **over the run** — `never_removed[c]`, `at_least_once[c]`, `created_once[c]`, `monotone[c]`,
  `two_copies[c]`, `never_together[a;b]`, `present_then_absent[i]`, `precedence[X;Y]`, `no_decrease`,
  plus the final-state terms.

A hypothesis is a conjunction of up to two terms. **The version space is every consistent conjunction**,
not the smallest ones — see §6 for why that distinction was a real defect.

Scoring, declared before the run:

- **B1** on at least two machines, a final state is reached by real runs with opposite judgments;
- **B2** no final-state term moves inside such a group, so the final-state grammar has *no* consistent
  hypothesis, and where it does speak, leave-one-run-out produces at least one false accept;
- **B3** the run grammar keeps a consistent hypothesis for every goal, separates every group, and has
  **zero** false accepts **and zero false rejects** under leave-one-run-out;
- **B4** the run grammar reaches agreement in k questions with an exactly right goal; the final-state
  grammar reaches agreement on a wrong one; both k counted;
- **B5** zero model calls, zero stored parameters, every run a real execution.

## 4. Results

| | FILESYSTEM | SQLITE | TARBALL |
|---|---|---|---|
| sequences executed → distinct runs | 155 → 68 | 84 → 48 | 84 → 20 |
| runs the user accepts | 18 | 16 | 6 |
| final states reached with **opposite** judgments | **4** | **4** | **1** |
| terms: over the run / final-state only | 28 / 15 | 44 / 18 | 45 / 17 |
| final-state terms that disagree inside a group | **0** | **0** | **0** |
| final-state grammar: hypotheses consistent with all judgments | **0** | **0** | **0** |
| final-state grammar: leave-one-run-out | 68 undecided | 48 undecided | 19 undecided, **1 false accept** |
| run grammar: hypotheses consistent with all judgments | 7 (1 behaviour) | 1 | 24 (1 behaviour) |
| run grammar: leave-one-run-out | 67/68, **0 false accepts**, 1 false reject | 48/48 | 20/20 |
| run grammar: questions to agreement, accuracy of the agreed goal | 5, **1.00** | 6, **1.00** | 5, **1.00** |
| final-state grammar: questions to agreement, accuracy | 4, 0.82 | 7, 0.79 | 2, 0.95 |

B1 **MET** · B2 **MET** · **B3 NOT MET** · B4 **MET** · B5 **MET**. 18.1 s, 0 parameters, 0 model calls.

The two things worth reading twice:

- **The final-state grammar is empty, not wrong.** On every goal that has a group, no conjunction over
  the final state is consistent with the user's judgments — 0 survivors. It cannot be fixed by adding
  terms, because every term in it is constant inside a group. Where it did speak (TARBALL, one
  held-out run) it produced the accusation class: a false accept.
- **The run grammar is exact where it is asked.** 5 to 6 well-chosen questions, an agreed goal that is
  right on all 136 runs, and under leave-one-out 135 of 136 correct with **zero false accepts**.

## 5. The criterion that failed, kept as it failed

B3 declared **zero false rejects**. It produced one: run 44 of the FILESYSTEM pool, a real three-action
run that the user accepts and the inferred goal rejects.

The mechanism is not vagueness; it is the price of not asking. With run 44 held out, seven hypotheses
survive and they agree on all 67 other runs — but an eighth survives too,
`monotone[probe_new_content] ∧ two_copies[probe_seed_content]`, which is consistent with every other
run and rejects 44. Acting on the *intersection* of all survivors is therefore **sound** (0 false
accepts, the class that matters) and **not complete** (1 run lost of 136). Full-data agreement in the
same pool is 7 survivors in 1 behavioural class; drop one run and a new behavioural class appears. That
is the sharpest statement this project has produced of why *agreement is never a proof and only a
contrast set is*: the 68th run was the only thing that could kill the eighth hypothesis.

This is reported as a failure, it is asserted as a failure in the suite
(`test_the_declared_failure_is_kept_and_its_cause_is_reproducible`), and the mechanism is reproduced
there rather than described.

## 6. A defect this round found in the last round's solver

`the_goal_is_a_discriminator_v1.minimal_discriminators` returns only the **smallest** conjunctions
consistent with the data. That is right for "what is the shortest rule", and it is wrong for
"is the goal identified". The first run of this round used it that way and the result was a lie: a
single surviving term rejected thirty-two runs the user accepted, and the stopping rule called it
identified. The fix is not a tweak — the version space is every consistent conjunction up to size two,
terms are evaluated once into bitmasks over runs, and identification is a distinct-mask count. The last
round's file is untouched; the correction is here, with its numbers.

## 7. The law

> **A goal is a relation over the run, and a run-level goal cannot be represented by any function of
> the final state. Identification is cheap and sound when the agent may ask and may act on the
> intersection, and its price is completeness: the intersection never falsely accepts a run, and can
> refuse one it should accept until a contrast exists that separates the survivors.**

Two corollaries the numbers give directly:

1. **Soundness is free; completeness costs questions.** Zero false accepts at every k; one false
   reject at k = all-but-one; zero false rejects at k = 5–6 chosen questions.
2. **Agreement is a stopping rule, not a truth.** The end-state grammar agrees on a goal that is wrong
   by 5–21 % of the runs, and it does so *early* (2–7 questions). An agent that treats convergence as
   certainty converges on the wrong thing faster than one that keeps asking.

## 8. What is real and what is not

**Real (producer-run, this sandbox):** the 9 groups, the 0 disagreements, the empty final-state version
space, the 135/136 with 0 false accepts, the 5/6/5 questions, the 18.1 s and the zeros.

**Not real / not claimed:** three CLI machines are not computer use; three actions deep is not a
trajectory; the judge is this tool's own predicate, not a human's sense of "the right way"; the run
grammar is a *grammar* and a goal outside it is refused (`undecided`), never approximated — tested;
runs are deduplicated by trace, so two action sequences that read identically are one run and a goal
that distinguishes them is outside the observable by construction; GIT is not in the three (its reset
costs five git invocations per run, and the structure is already carried by the other three); and
nothing here synthesises a program.

## 9. The single bottleneck

The honest answer changes with this round's result, so state it exactly.

Identification is **solved as a cost, not assumed**: 5–6 questions, sound, on any machine that can be
executed. What remains is the supply of **contrasts**: a run on which the surviving hypotheses disagree.
Here the machine could produce them within three actions (9 groups found by brute force). At the
frontier it cannot — you cannot execute every edit sequence on a real codebase, and 97.8 % of SWE-bench
Verified is not even replayable (the earlier measurement: ~2.2 % is replay). So:

> **The single bottleneck is the reachable contrast set at the frontier — the ability to produce a run
> that a hypothesis can be tested against. Identification is now cheap; the world is not.**

That is the synthesis–verification asymmetry with its premise measured instead of asserted: verifying a
run against a relation is free, asking a question is cheap, and *making the run* is the whole remaining
problem. Everything this project has built is on the cheap side of that line, and this round moves one
more object — the goal's history — onto it.

## 10. Next step, and what would falsify this

Next: the same mechanism where the run is genuinely long — take a real multi-step task from the
project's own hardest open material and ask whether the run-level goal can be identified when the
trace is 20–60 steps and only a handful of runs can be executed, i.e. whether the cost stays at
5–6 questions when contrasts are expensive. Pre-registered before that run: zero false accepts on
held-out runs, the question count, and the reachable-contrast count actually available.

Falsifiers of this round: an action taken while no reachable run satisfies every survivor; a false
accept reported as zero without the leave-one-run-out check; B3 reported as met; the blocker
hypothesis described but not reproduced; a goal outside the grammar approximated instead of refused.
