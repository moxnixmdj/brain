# The demonstration carries the action, never the condition — measured on a machine that is not a code repository

*2026-11-26. The question, in the owner's words and taken whole: instant learning and instant learning in
arbitrary new environments are solved, so all that is left is to give the model each action once in each
new environment and it will own it permanently — therefore any computer use, and the most advanced
software engineering, is solved by demonstration plus a verifier. We were trying to make a sentient
creature. Is this true, what is wrong, what is real, and what is the smartest thing to do?*

## What this tree had already settled, so that this round does not re-argue it

Two rounds ago the same question was answered on *code*: retention is exact and solved (replay held
legality in 228 of 228 compositions), and transfer is not (`A_SINGLE_TRACE_DOES_NOT_PIN_THE_RULE`). The
scope of a lesson costs observations, and three successes buy nothing while the first failure changes the
answer (`A_SKILL_LEARNS_WHERE_IT_APPLIES`, 5 observations, `required=('baseline.violates_own_spec',)`).
Successes alone identify 0 of 200 requirements (`applicability_v1`).

Every one of those numbers is about Python and a test suite. The owner's claim is not about Python. It is
about **any computer**. A law that only holds inside a code repository is not the law he is asking about,
so this round runs it somewhere else: a real machine, real processes, real states — `git`, `tar`, `gzip`,
`patch`, and a real repository's real history. The oracle is each program's own exit status. There is no
annotation anywhere in the instrument saying which state *should* accept which action; the programs say
it. Nothing here is a fixture built to make a point: 160 states were created by running real commands, and
a failure whose stderr names an infrastructure cause (network, permissions, disk) is classified
`AMBIGUOUS` and dropped rather than counted as evidence — 0 arose.

## The three arms

1. **Successes only.** One demonstration of an action is one state where it worked. The strongest rule
   that evidence licenses is the intersection of the demonstrated states' facts — the literal "do it when
   the world looks like this". k = 1, 2, 4 demonstrations of the *same* action, judged on held-out real
   states the demonstrations never saw.
2. **Contrasts.** The first failure is added, then the tree's own `contrast_selection_v1` chooses which of
   the reachable states to try next — a question, asked of the machine, chosen for how evenly it splits the
   surviving requirements.
3. **Vocabulary.** For each action, whether a requirement equivalent to its applicability exists in the
   cheap sensor vocabulary at all is *decided by search over the observed table*, not assumed.

## The measurement

10 actions, 160 real states (8 where the action applies and 8 where it does not, per action), 38
executions, 18.1 s, **0 parameters, 0 model calls**.

| | |
|---|---|
| retention — replay of a demonstrated action in a fresh copy of its state | **30 / 30** |
| successes only, accuracy on held-out states at k = 1 / 2 / 4 | **0.5625 / 0.7125 / 0.8625** |
| successes only, requirements *identified* at any k | **0** |
| successes only, rules equal to the action's actual precondition | **0** |
| contrasts, accuracy on the 7 actions whose deciding fact is observable | **0.9464** |
| contrasts, accuracy on the 3 actions whose deciding fact is **not** observable | **0.5833** |
| contrasts, requirements identified by name | **0** |
| residuals where the selector proved no reachable state can split the survivors | **9 of 10** |
| facts that never take a second value anywhere in a family (dead sensors) | **8.5 of 12.8 — 66%** |

The two halves of the owner's sentence come apart cleanly, and both are numbers:

**The half that is true.** An action is a program, and a program replayed is exact: 30 of 30 replays of a
demonstrated action in a fresh copy of the same state exited 0. Nothing decays, nothing is forgotten,
nothing needs weights. Retention is solved, and it is cheap, and it is permanent.

**The half that is false.** Competence is not the action; it is the *condition*. "Do it once and it is
learned" is true of the first and silent about the second, and the measurement shows the second does not
follow: at k = 1, 2, 4 demonstrations the learner identifies **no** requirement, and the rule it is forced
to use never once equals the action's actual precondition. Its *accuracy* climbs — 0.56, 0.71, 0.86 —
for a reason that looks like learning and is not: the intersection of more successful states is a
**smaller** set of facts, so the rule gets broader, and broader rules are right more often on a balanced
set. It is converging to the base rate from below, not to the truth. That is the arithmetic of
`A_FAILURE_IS_WORTH_TWO_TO_THE_KEYS_KEPT`: a success can only ever remove a fact from the requirement,
never add one.

**Where the demonstration does look right, it is right by accident.** On 5 of the 10 actions the
intersection at k = 4 reaches 1.0 on held-out states. In every one of those the demonstrations happened to
vary everything *except* the deciding fact — the extras were drawn at random, so a few draws produced an
accidental contrast set. The system cannot tell that from the other case, because with successes only it
has no failure to refute anything. This is identifiability, in the smallest instance I can build: one
trace fits every rule that agrees with it, and the demonstration contains no information about which of
them is the boundary.

## The three actions that cannot be learned by any amount of trying

`tar -xzf bundle.tgz`, `gzip -d payload.gz`, `patch -i change.patch`: for these the deciding fact —
*is this file actually a valid archive / gzip stream / applicable patch* — is **not in the sensor
vocabulary at all**. The agent can see that the file exists and is non-empty; both classes look identical.
So no observation can refute the wrong requirement, the version space never collapses, and the contrast
arm plateaus at **0.5833** — barely above the base rate of 0.5 — while the seven observable actions reach
**0.9464** in about four executions each.

This is the insufficiency certificate (`INSUFFICIENCY_CERTIFICATE_20261113_V1`) re-measured on a computer
instead of on code, and it has a practical face: on a real machine you often *cannot* observe whether an
action applies. You can only attempt it — which is why the attempt must be made in a copy, and why the
verifier is not a sensor. Competence on those actions is not knowledge of a condition; it is the
willingness to run a trial and read the exit status.

## The dead-sensor census, which is the round's new quantity

Per family of 16 real states, **8.5 of 12.8 fact groups never take a second value** — two thirds of the
vocabulary is constant. A fact that is true in every reachable state cannot be refuted by any observation,
so it survives inside every consistent requirement, and the learner's survivor count stays at 768–7936
even after the contrasts. That is not a defect in the learner; it is the arithmetic. The tree's own
selector then does something worth naming: on **9 of 10** actions it terminates with
`EVERY_REACHABLE_STATE_GIVES_THE_SAME_ANSWER_FOR_ALL_SURVIVORS` — it *proves* that the residual ambiguity
cannot be resolved by anything this machine can do.

So the behaviour is pinned (0.9464) while the requirement cannot be named. An agent can act correctly
without being able to say why, and the part it cannot say is exactly the part no reachable state varies.

This gives the "best part is no part" law a number it did not have: **a sensor that no reachable state can
change is not free — it costs 2^k hypotheses.** Two thirds of this vocabulary is that kind of weight. A
sensor should be admitted by what it can *vary*, not by what it can see.

## What is real, what is not

**Real.** One demonstration adds an action permanently, exactly and for free (30/30). A verifier built
from a program's own exit status is honest and needs no annotation (0 ambiguous outcomes, 0 accusations).
A question chosen to split the surviving requirements buys the condition in about four executions where
the condition is observable at all (0.9464 vs 0.5625).

**Not real, and this is the whole answer to the question as asked.** That this adds up to "any computer
use, once, permanently". Learning an action gives you an *action*; using it requires the *condition*, and
the condition is not in the demonstration — not in code (0 of 200 requirements, measured two rounds ago)
and not on a machine (0 of 10 actions at any k, measured here). Where the condition is observable, it must
be *bought with a failure*; where it is not observable, it cannot be bought at all and must be *tried*.

**The single bottleneck, unchanged in name, now measured in a second environment class: the demand.** In
coding it appears as "which relation does this failing run violate"; here it appears as "which states
accept this action". Both are the same missing object — the condition under which something is true —
and both are invisible to demonstration, because a demonstration is an *instance* and a condition is a
*quantifier*.

**On the creature.** A system that has stored every action and every condition is still a lookup table,
and this measurement says why: its competence is bounded by the states it has been shown or can reach,
and it has no reason to prefer one unreached state over another. What the receipts show, precisely, is
that the only thing in this whole apparatus that *asks* is the selector — it chooses which of the
reachable states to try next, and its choice is not in any demonstration. 38 of those choices were made in
this round. A creature is not the system that has seen everything once; it is the system that decides what
to look at next, and that organ is not a learner — it is a chooser. The claim "do it once and it is
permanent" is a statement about memory. Sentience is a statement about *which question comes next*.

## The smartest thing to do next, in order

1. **Store the action as a conditional, never as a program.** The unit is `(program, condition)`, and a
   condition is a set of states with a boundary — not a count of successes.
2. **Buy conditions with designed contrasts, and count them.** Four executions per action bought 0.9464
   where observation could decide; that is the cheapest capability purchase this tree has measured.
3. **Prefer actions whose conditions are observable; for the rest, make the trial the condition.** Three
   of ten real actions have no observable condition. For those the agent's competence is a *budget for
   experiments in copies*, and the correct engineering is a sandbox, not a sensor.
4. **Prune the vocabulary by variance.** Two thirds of the facts in these families are dead weight that
   inflates the hypothesis space by 2^k. A sensor earns its place by changing somewhere reachable.
5. **Then, and only then, learn the chooser.** The measured gap between 0.9464 (with contrasts) and what a
   passive store can do is entirely bought by *choosing which state to try*. That chooser is the one
   component worth parameters — and its training signal is already here, exact and free: whether the
   survivors after the execution are fewer than before.

## Cost

160 real states built by real commands, 10 real actions, 38 executions, 18.1 s wall, 30 retention replays,
0 parameters stored, 0 model calls, 0 borrowed weights, 0 ambiguous oracles. Everything the receipt claims
is a row in `canonical/verification/THE_PRECONDITION_IS_NOT_IN_THE_TRACE_20261126_V1.json`, and the four
instrument defects found while building it (a `feature` branch pre-created in the base, an interactive
`patch` prompt, a "conflict" marker that matched a *filename*, and a stash step that swept the shipped
patch into the stash) were each fixed and the whole sweep re-run before any number above was written.
