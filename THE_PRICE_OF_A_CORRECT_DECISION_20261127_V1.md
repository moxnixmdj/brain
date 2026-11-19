# The price of a correct decision: 1.0 accuracy for 160 executions, or 0.925 for 52 — and the 7.5 points lost are exactly where the world cannot be seen

*2026-11-27. The question, taken whole: instant learning and instant learning in new environments are solved,
so give the model each action once and it owns any computer use permanently, and we have a sentient
creature. Is this true, what is wrong, what is real, and what is the smartest thing to do?*

## What the tree had already settled, and therefore what this round does not re-argue

Retention is solved: a demonstrated action replays exactly, 30 of 30, on a real machine
(`THE_DEMONSTRATION_CARRIES_THE_ACTION`, last round). Identification is not: a demonstration identifies **no**
condition — 0 of 10 real actions at k = 1, 2, 4 — and contrasts buy a condition only where the deciding fact
is observable (0.9464) and cannot where it is not (0.5833). On code the same law was measured earlier (0 of
200 requirements from successes; the first failure changes the answer; 5 observations buy a scope).

So the interesting question is no longer *accuracy*. It is **price**:

> To decide one real action correctly, what must the agent spend, how often, and when does the spending stop?

That is the question an owner means by "solved", and it is the question 2026's own literature has arrived at
from the other side: EnvProbe (arXiv 2606.31422) frames a pre-action query as *a budgeted decision* that
"costs one interaction step"; WEVA (EMNLP 2026) reports verified lookahead cutting executed actions to 33% of
ReAct's; NSPI's neuro-symbolic computer use puts a pre-action verifier in front of every state-mutating step.
None of them measures the exchange rate on a machine, with a real learner, against the wall where no sensor
can see. That is what this round does.

## The three ways to decide, all run on real processes

The machine is the one built last round and reused here, not rebuilt: real `git`, `tar`, `gzip`, `patch`;
**160 real states** created by running real commands; each program's own exit status as the oracle.

| policy | what it does | accuracy | executions |
|---|---|---|---|
| **guess** | answer the majority class | 0.5000 | 0 |
| **one demonstration** | act on the rule a single success licenses | 0.6125 | 10 (one per action) |
| **trial every decision** | run the action in a *copy* of the state, read the exit status | **1.0000** | **160** |
| **trial, then keep the lesson** | same, and feed every trial into `applicability_v1`; stop trialling on states where the surviving requirements agree | **0.9250** | **52** |
| **trial, but choosing which state to try** | as above, but the next trial is *chosen* by `contrast_selection_v1` | covers 7 of 10 actions in **37** | **37** |

A copy of one state costs **14 ms** and one process execution. That is the whole price of certainty, and it is
the same price for every action, on every machine, with no sensor, no model and no weights — which is why it
works on the three actions whose condition no sensor can see.

## Finding 1: all of computer use is *decidable*, and none of it is thereby *known*

`trial every decision` scores 1.0 — by construction, and that construction is the point: an action is a
program, a program has an exit status, and a copy of the world can be thrown away. Any action on any computer
is therefore decidable at 14 ms plus one execution, including `tar -xzf` on a file that may not be an archive,
`gzip -d` on a file that may not be compressed, and `patch` on a diff that may not apply — the three where
every cheap sensor is blind.

This is the honest answer to "can we do anything on a computer": **yes, by trying, in a copy, and reading the
status.** It is not learning, it does not persist, and it must be paid again next time. It is also the floor
under everything else in this document, and it needs nothing that this project does not already have.

## Finding 2: the lesson is free, and it is not sound

The trials an agent must make anyway are labelled states, and labelled states are exactly what the learner
needs. Feeding every trial back and stopping the trial wherever the surviving requirements agree cuts the
price from **160 executions to 52** — 108 of 160 decisions then cost nothing — with no extra experiment.

That is the "learning by doing" claim, and it is true. It also costs **7.5 accuracy points**, and the
distribution of those points is the whole finding:

| action | trial-then-learn accuracy | deciding fact observable? |
|---|---|---|
| stash, merge, rebase, checkout, branch delete, untrack, chmod | **1.0000 each** | yes |
| `tar -xzf` | **0.7500** | no |
| `gzip -d` | **0.6875** | no |
| `patch` | **0.8125** | no |

On the three, the surviving requirements *agree* — so the agent is decisive, confident, and **wrong**, because
the facts it can see are identical for a valid and an invalid archive. Decisiveness is not soundness. An agent
that stops testing wherever its knowledge agrees will be silently wrong exactly where the world cannot be
observed, and nothing in its own state will tell it.

And the requirement is **never named**: 0 of 10 actions, after 52 real executions, name the condition. The
agent acts at 1.0 on seven actions with **512 to 7168** candidate requirements still standing. Operational
understanding here is not "having the rule"; it is "the rules you still cannot choose between give the same
answer here". That is a sharper and more useful notion than identification, and it is the one the price list
is built on.

## Finding 3: choosing the question is worth 29%, and cannot beat a wall

Given the same learner and the same states, letting the agent *choose* which state to trial next
(37 executions) instead of taking the stream in order (52) saves **15 executions, 29%**, and it covers
**7 of 10** actions completely — every decision on those actions then costs nothing.

On the other three it covers **nothing at all**: the selector stops with
`EVERY_REACHABLE_STATE_GIVES_THE_SAME_ANSWER_FOR_ALL_SURVIVORS`, because no state the agent can reach reveals
whether the archive is valid. A chooser cannot out-ask the world. Its competence is bounded by which questions
the machine is able to answer, which is a property of the machine and not of the chooser.

## What is real, what is not, and where the bottleneck now sits

**Real.** One demonstration adds an action permanently (30/30). A trial in a copy decides any action correctly
at 14 ms and one execution (1.0 on all ten, including the three no sensor can see). Learning from the trials
you were going to make anyway is free and cuts the price by two thirds (160 → 52). Choosing the next question
is worth another 29% (52 → 37) *where the question is answerable*.

**Not real.** That this adds up to "solved, permanently". Permanence is available exactly where the deciding
fact is observable — seven actions, where the trial stops and the accuracy stays at 1.0. On the other three
the price is recurring forever, and the agent that tries to stop paying it becomes wrong without knowing.

**The single bottleneck, now stated as a property of the world rather than of the learner:** *the deciding
fact must be observable somewhere the agent can reach.* Everything this project has built — the learner, the
selector, the oracle, the price — is downstream of that one property. Where it holds, competence is bought for
a handful of executions and then costs nothing. Where it fails, no budget, no depth, no model and no
architecture can buy it, because the information is not in the world the agent can see. This is the
insufficiency certificate, arriving at the end of the arc as a *price list* instead of a prohibition.

**On the sentient creature.** A system that can always test is a tester: correct, and permanently ignorant.
A system that chooses which test to run is the beginning of something else — this round measures its value at
29% of all executions, and measures its limit just as exactly at zero on the three actions the world will not
answer. A creature, in the only operational sense this project can defend, is *the generator of the next
question and the judge of whether it was answerable* — not the store of everything it has seen once. The
parameters worth having are the ones that pick questions, and their training signal is already free and exact:
did the surviving set shrink, and did the answer change.

## The smartest things to do, in order

1. **Make the trial the default decision procedure, at 14 ms.** Not as a fallback — as the floor. It is the
   only method measured here that is correct on 10 of 10 actions with no sensor and no model.
2. **Never let the trial stop on agreement alone.** Stop it only where either the requirement is named or the
   surviving requirements were *tested* — a disagreement that was resolved. Otherwise the agent is the three
   actions above: confident and 25–31% wrong.
3. **Spend the executions on questions, not on demonstrations.** Choosing the state to trial saved 29% and
   covered seven actions completely; the same budget spent on more demonstrations bought 0.6125.
4. **Make the deciding fact observable where you can.** This is the only move that converts a recurring price
   into a one-time one; everything else in this document is a way of paying it.
5. **Then, and only then, learn the chooser.** It is the one component whose value is measured, whose limit is
   measured, and whose labels are produced for free by the work itself.

## Cost

One real clone, 160 real states built by real commands, 52 + 37 executions across the policies, 14 ms per
copied state measured over three samples, 0 parameters stored, 0 model calls, 0 borrowed weights, 0 ambiguous
oracles. The instrument defect that this round found in itself is recorded rather than hidden: the first
version switched from trial to knowledge on `boundary.identified`, which never happens on a real vocabulary,
so it trialled 160 of 160 decisions and would have "shown" that learning from work is impossible. The switch
that is actually correct is per state — do all surviving requirements agree here? — and the difference between
those two switches is the entire result above.
