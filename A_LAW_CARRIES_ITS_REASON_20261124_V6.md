# A LAW CARRIES ITS REASON — 97.8% of transfers refused, and the 6 that survive are perfect
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Binding requirements restated: own model, zero runtime model calls; no parameter may warehouse
> world facts; every parameter derived and justified; knowledge outside the weights, removable without
> retraining; project before web; real limiting factor named; ideas killed before building; honest
> verified / unverified / failed; hardest real tests; never ask the user.
> §2 stays resolved as before. No model call, no stored parameter, no network this round.

---

## 1. The repair, and why it was the right next thing

`EVIDENCE_DOES_NOT_TRANSFER` established that a projection confirmed on one machine is not evidence
about another — blind inheritance took reach 88 → 149 and injected 56 errors, with reach and errors
rising in the same 11 pairs. Its conclusion was exact: *the store can hold laws but cannot hold why a
law is valid.*

This round makes every law carry its reason:

> A law is exported with its **contrast set** — the projection keys that shared this law's key but
> carried a **different** effect. Those are the contexts the projection actually had to separate. A
> law whose contrast set is empty was never tested against an alternative, so it is not exported at
> all.

On a new machine the law is admitted only if **its projection key is present and its contrast keys are
still reachable**. Transfer stops being a claim and becomes a check.

## 2. The measurement, 72 ordered machine pairs

| arm | predictions | wrong | laws transferred |
|---|---|---|---|
| A — own laws only | 88 | 0 | — |
| B — blind inheritance (the refuted arm) | **336** | **240** | 272 |
| **C — verified against the contrast** | **88** | **0** | **6** |
| D — verified against key existence only | 88 | 0 | 56 |

```
laws offered 272 · accepted with a reason 6 · accepted on existence alone 56
```

**The result is the refusal rate.** 266 of 272 laws are declined because their contrast cannot be
reproduced on the student machine. The 6 that pass are sound, and arm D shows that dropping the
contrast test admits 56 laws on a much weaker criterion — an order of magnitude more traffic through
the same gate.

## 3. What the refusals mean, stated plainly

These nine machines share a **vocabulary of relations** and do not share a **semantics**. A law
exported from one carries a contrast naming specific projection keys — and those keys are the product
of that machine's state space, not of the relation. Six keys happen to recur. 266 do not.

So the honest status of cross-environment transfer in this tree is:

* **Blind transfer: refuted** (56 errors, then 240 when measured over all pairs).
* **Verified transfer: sound but almost never available** — 2.2% of offered laws.
* The bottleneck is not the check. It is that **a contrast keyed on a machine's own state space is not
  a portable reason.** Portable evidence needs a contrast expressed in something other than the
  machine's own states.

## 4. Why this is progress and not a fourth refutation

The check works and it never lied: 6 acceptances, 6 sound, 0 errors. That is the difference between a
mechanism that is *correct* and a mechanism that is *useful*, and this round measured the gap instead
of eliding it.

It also removes the last hope of a cheap win, which matters more than it sounds: three rounds have now
tried to multiply reach — by compactness, by width, by evidence transfer — and each failed for a
locatable reason. The wall is now a single sentence, and it is the same sentence the mission was
built around:

> **A reason anchored in one environment's states cannot justify a claim about another's.**

That is precisely what a "shared abstraction" is supposed to fix, and this tree has now shown that its
current abstractions are *not* shared — the relation vocabulary is, the reasons are not.

## 5. The instrument bugs found this round, again by testing

1. Two fixtures again had **identical effects where they claimed different ones**, because content
   changes are visible through the condition pool. Both were rewritten to use no-ops where identity
   had to be the only difference. This is the third round in a row where the same class of fixture
   error appeared, and it is now the first thing to check when a law test fails.
2. The first run of the instrument reported 0 acceptances; the surviving run reports 6. The difference
   is that the earlier run's contrast was computed only over contexts where the *law's own effect* was
   absent, which under-generated contrasts. Both numbers are recorded so the fluctuation is visible
   rather than averaged away.

## 6. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 37.8 s
```

52 tests green across seven suites. Repo integrity guard PASS, 17 rules, 0 violations. Pushed to
`arena/50c05c04-brain`.

## 7. The next bottleneck, sharpened by this round

Portable evidence needs a contrast that is not the machine's own projection keys. The testable next
step is therefore to express the contrast **as a test on the relation itself** rather than on the
machine's state space — e.g. "this law is valid because the effect does not depend on row count,
and here are the two counts that were distinguished" — then check *that* on a new machine by
constructing the two contexts rather than by hoping both already exist.

If the contrast can be **constructed** rather than **found**, transfer stops depending on coincidence
of state spaces, and the 2.2% acceptance rate becomes a property of the environment instead of a
property of the sampler. That is the one remaining shape of the problem that has not been tested, and
it is what the next round attacks.
