# First principles, third pass — every growth axis is closed

**2026-11-04.** Third time this question has been asked. The first two answers were "here is a
refutation, and here is one more repair." Repairs are not first principles, and the question keeps
coming back because I kept answering the wrong layer. This one names the layer.

Authority **NONE**. Spend $0. `truth.achieved` false.

---

## 0. What I got wrong in the last two answers

Both times I asked *"is this change correct and honest?"* — and it was, twice. Last turn I widened
the creature's reach from 33 to 52 of 155 capabilities by finding a false static refusal. That is a
real gain. It is also **the world getting bigger around a fixed creature**, and I presented it as
progress toward a creature.

The question is not whether my changes are correct. It is:

> **Which axis, if opened, would let this system be different at the end of a run than at the start —
> not its beliefs, not its reach, but *itself*?**

---

## 1. Measured: every axis is closed

I looked for the four places a system can grow, and tested each one instead of assuming.

### Axis A — new concepts its predictor can think with: **closed**

`sentient_cognitive_core_v1.FEATURE_NAMES` is a fixed, hand-written 10-tuple:

```
bias, host_ready, grounding_complete, causal_precond_met, memory_reflex_hit, strong_verifier,
missing_dep_or_env_block, nested_cost_or_timeout_risk, family_empirical_pass_centered,
family_observation_confidence
```

It *can* invent **conjunctions** of those ten (`_maybe_invent_conjunctive_features`, selected by
empirical mutual information). It cannot invent an eleventh primitive. Every judgement it will ever
make is a function of a vocabulary I chose in advance. That is the definition of static code wearing
a self-model.

### Axis B — new capabilities: **closed**

155 registered, 52 reachable after last turn's fix. Onboarding re-labels what is already reachable,
and `sovereign_perform` refuses anything whose preconditions are unmet — so the set of things it can
do cannot grow through its own loop. Measured across six sessions: reach 33 before, constant, every
session, while 18 capabilities onboarded.

To open this axis the creature would have to **write its own adapter and have an outside verdict
accept it**. Nothing in the loop does that.

### Axis C — rewriting its own code: **exists, never invoked, and crashes**

This is the one that actually matters for "not static code", and it is the worst of the three.

`sentient_cognitive_core.evolve_self_code` → `RecursiveSelfArchitect.run_self_improvement_cycle` is a
full organ: introspect hotspots, cluster failures, synthesise patches, Ring-0 verify, promote only
winners. It is wired into the creature as `Creature.self_architect_step`.

**Measured over three consecutive sovereign sessions: 0 calls.** The board never schedules it. The
only call sites are explicit operator entry points.

**Measured when invoked deliberately**, on the creature's own organs:

| Ring-1 target | result |
|---|---|
| `rule_scope_learning_v1.py` | `NO_SELF_PATCH_PROMOTED` |
| `sentient_cognitive_core_v1.py` | `NO_SELF_PATCH_PROMOTED` |
| `creature_runtime_v1.py` | **CRASH** — `ValueError: Unexpected node inside JoinedStr, <ast.Call>` |

So the creature cannot rewrite one of its own two central organs at all, and when it can run it
produces nothing. I could not pin the exact construct: `ast.unparse` round-trips the file fine,
`copy.deepcopy` of the module AST round-trips fine, unparse of a directly-constructed
`JoinedStr`+`Call` is fine, and the line-number bisect I ran is confounded (truncating a file at
arbitrary lines changes which functions are complete, so the "first crashing prefix" it reports is an
artifact of the truncation, not a culprit). **The crash is real, reproducible, and undiagnosed** —
and that is the honest state of it.

### Axis D — its self-model, fitted to outcomes: **open, and I built it and it lost**

Last turn: α = 0.334 fitted shrink. +0.01 where blocked, **−0.15 where it worked**. Deleted.

---

## 2. The structural verdict

> Three of the four growth axes are closed and the fourth was measured net-negative. A system with
> closed growth axes is **static code with a self-model**, however good the self-model is.

That is why the question keeps returning. Nothing I have done in five turns touches it: P1, P3, P4′,
the diet fix, the static-guess fix all made the *existing* system more honest and more capable. None
of them lets it become something it was not.

And this is the precise sense in which the owner is right and my plans were wrong: I kept optimising
a **measurement apparatus** and calling the optimisation progress toward a **creature**.

---

## 3. What the smartest thing actually is

Not another repair. Not another organ (axis C already exists as an organ; a second one adds nothing).
The smartest thing is to **open exactly one growth axis, with the experiment designed before the
result is known** — and to pick the axis whose failures are cheap.

Ranked, with the reason:

**1. Axis A — let it invent a primitive.** Cheapest to build, smallest blast radius, and it changes
its judgements everywhere rather than one code path. Today it can only recombine ten hand-chosen
features. The experiment: give the predictor a **grammar of new features it can propose** (arithmetic
and comparison over existing ones), and let the *outcome ledger* decide which survive.

The protocol matters more than the mechanism, and it must be pre-committed:

- **Sealed held-out.** Predictions are scored on outcomes drawn *after* the feature was adopted. A
  feature admitted on the same data it was found in proves nothing — that is the overfitting trap
  this tree has a name for.
- **Falsifier, stated now:** if held-out skill does not improve over the fixed-10 baseline, the axis
  is *not* the limit and I report that instead of shipping the mechanism. Given α=0.334 last turn,
  my prior is that it will not improve, and I would rather find that out cheaply.
- **No relaxation of anything.** The vocabulary grows; every gate, threshold and refusal stays.

**2. Axis C — fix the crash, then schedule it.** Required eventually, but it is one undiagnosed crash
inside a patch-synthesis pipeline that produces nothing even when it runs. Fixing it yields
`NO_SELF_PATCH_PROMOTED`, which is not a step toward anything. It should be done *after* there is
something worth self-patching, and the honest sequence is A then C, not C first.

**3. Axis B — not yet.** It needs the creature to author an adapter and an outside verdict to accept
it. That is the largest payoff and by far the largest risk of the creature widening its own
acceptance. It should come last, and only with a verifier it cannot write.

---

## 4. The one thing I will not do

Propose a fourth plan document, a fifth repair, or another "smartest approach" that turns out to be
one more honest improvement to a closed system. Five turns of that is enough evidence about my own
behaviour.

If axis A is opened, it is opened with the falsifier above written down first, and if it fails I say
so and stop reaching for the word *creature* until something on this table actually moves.

---

## 5. Non-claims

Axis C's zero-call measurement is from three sessions of `run_sovereign_board` at 12 cycles; a
longer run might schedule it, and if it does it will hit the same crash on `creature_runtime_v1.py`.
The crash diagnosis is incomplete on purpose rather than guessed — one line-number bisect is reported
as confounded rather than presented as a finding. Nothing here is independent verification, and every
change on this branch remains unadmitted.
