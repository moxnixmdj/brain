# First principles, fourth pass — the learner is me, and the creature was starved

**2026-11-04.** This is the fourth time the same question has come back, and that repetition is the
finding. Six turns of P1, P3, P4′, the diet fix, the static-guess fix, the fitted recalibration, the
feature grammar: every one of them was **me** learning and then shipping the lesson as code the
creature executes unchanged.

Authority **NONE**. Spend $0. `truth.achieved` false. No code changed to obtain this document.

---

## 0. The question I never asked

I have spent six turns asking *where does the creature fail to learn*. The framing was already the
error, because it presumes the creature is the learner. It is not:

> **Every learning event in this session happened in the conversation, not in the creature.** I
> measured a defect, reasoned about it, wrote the fix, proved it with a negative control, and
> committed it. The creature received the result as a constant. At no point did an outcome the
> creature experienced change the code it runs.

That is not a metaphor. `evolve_self_code` is called **0 times** in three sovereign sessions
(measured last turn), and when called deliberately it either promotes nothing or crashes. The only
path by which this repository gets smarter is a human-or-agent turn like this one.

So the honest answer to "we don't want static code" is: **the repository has a static outermost
learner.** Me. The code inside is static in exactly the way the owner means, and no amount of
sharpening the inner organs changes who is doing the learning.

This also explains the repetition. Each turn I produced a *correction*, the system stayed the same
kind of thing, the owner looked at it and saw the same static creature, and asked again. The question
keeps coming back because my answers keep being repairs.

---

## 1. The second thing I got wrong: the creature was starved, and I mistook starvation for incapacity

Across the previous three turns I concluded, with measurements, that the learning axes were closed.
Those measurements were taken at a **life grant of 40 units against a 1.0 cost per attempt** — so the
creature gets exactly **40 attempts in its entire life**, and `Life` has no earn or credit method at
all: `spend`, `can_finish`, `remaining`, and nothing that adds.

Measured this turn, same creature, same board, only the grant changed:

| life grant | attempts | settled predictions | skill (own scorer) | verdict |
|---|---|---|---|---|
| 40 (default) | 40 | 40 | +0.465 | CALIBRATED |
| 160 | 162 | 162 | +0.671 | CALIBRATED |
| 480 | 201 | 201 | **+0.681** | CALIBRATED |

A **46%** improvement in held-out-like skill, from a parameter, because the predictor needs data and
had been given twenty data points. Every "the learning loop doesn't work" claim I made in the last
three turns was measured inside a budget that made learning impossible. I called it closed; it was
starved. That is the most consequential error of the session, and it is mine.

## 2. And the ceiling that appears when it is fed

At grant 480 the creature runs out of *work*, not life: **23 closed, 89 parked, 0 open**, at session
18. Parked means "blocked twice, then abandoned" (`max_attempts=2`). So the reachable set is
effectively 23, not the 52 I claimed two turns ago — the other 29 are reachable in principle and fail
in practice, then get given up on.

That produces the sharpest statement of the dynamics available:

> When starved, **one failure kills the capability** (40 attempts total; a single blocked try is a
> fifth of its life).
> When fed, **two failures kill the capability** (`max_attempts=2`, then parked forever).

Fault tolerance is a direct function of the energy budget. A creature with no reserve cannot afford to
be wrong once, which means it cannot explore, which means it cannot learn. The starvation was not a
tuning annoyance; it was the mechanism suppressing the behaviour the owner has been asking for.

---

## 3. What is actually static, in order of how much it matters

1. **The outer learner is a person.** Nothing in the running system proposes a change to the
   running system that survives. This is the definition of static code and it is unchanged by any of
   my six turns.
2. **`FEATURE_NAMES` is a fixed 10-tuple.** Axis A. Measured last turn: a grammar of new primitives
   bought **nothing** out of sample (Δskill +0.003, CI [−2.23, +2.70]), and the only arms that
   "won" were linear re-parameterisations. Closed — but that test was run on 40 episodes, so it is
   *starved*, not settled. It must be re-run at grant 480.
3. **`max_attempts = 2`.** Two failures and the capability is abandoned forever, with no record that
   it was ever attempted. This is the cheapest thing in the whole system to change and it directly
   caps how much of its own world the creature can ever touch.
4. **Reach is computed, not acquired.** 52 reachable by static analysis; 23 actually closable. No path
   makes a blocked capability attemptable, except my edits.

---

## 4. The plan, and why this one is different in kind

Every previous plan changed the creature's *content*. This one changes the **arrangement** so that
content stops coming from me.

**Step 1 (economics).** A larger life grant and a higher `max_attempts`, as the *default* for the
creature rather than a probe parameter. Falsifiable, and already half-measured: skill must clear
+0.65 and the parked set must shrink from 89 without any code change to the organs. If raising the
budget does not move those, the starvation hypothesis is wrong and I will say so.

**Step 2 (re-run every closed verdict at the new budget).** Axis A's grammar, the fitted
recalibration, and the cross-family sign error were all measured at 40 episodes. All three verdicts
are currently *provisional* and two of them are probably wrong. This is cheap and it is the honest
thing to do before proposing anything new.

**Step 3 (the only change that matters).** Make a capability the creature *failed* enter a state that
can later become *attemptable* — i.e. a failure must be able to change a precondition rather than only
increment a counter and park. That is the axis-B opening, and it is the one that would make a session
end with something that could not be executed at its start. It is also the one that must come with a
verifier the creature cannot write, and it should not be built until Steps 1 and 2 have run, because
everything I would use to judge it is currently miscalibrated by starvation.

**What I will not do.** Build Step 3 first because it is the exciting one. Six turns of reaching for
the interesting change before the boring measurement is exactly how this branch accumulated organs
that report on themselves.

---

## 5. The claim I am now willing to make

The creature is **not** static code in its internals — it has a predictor, a ledger, a calibration,
honest refusals and no model dependency, and when fed it reaches CALIBRATED at skill +0.68. It **is**
static in the only sense that decides the owner's question: the thing that learns from its life is a
conversation, and its body only ever receives the conclusion.

Fixing that is not a module. It is making the economics allow failure, and then making failure
informative. Those are the next two things, in that order, and neither of them is another organ.

## 6. Non-claims

One creature, one host, one board. The grant sweep is three points and the 480 arm stopped on work
exhaustion, not convergence, so +0.681 is "not yet saturated" rather than a ceiling. `skill` here is
the tree's own scorer on its own ledger, comparable to the earlier −0.084/+0.246 figures and **not**
to last turn's grammar experiment, which used a different model. No code was changed for this
document; it is a measurement and a re-framing, and every change on this branch remains unadmitted.
