# THE GUARD COVERS NOTHING — and the no-ops were never the missing evidence
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts;
> every parameter derived and justified; knowledge external and removable; project before web; the real
> limiting factor named; ideas killed before building; honest verified / unverified / failed; hardest
> real tests; never ask the user. §2 resolution unchanged. No model call, no stored parameter.

---

## 1. The premise, and one thing I found while testing it

Last round's work order: four atoms decline to fire, so the learner is missing a **guard** — a
precondition. I argued the evidence was already in the walk as no-ops, being discarded.

The premise about the evidence was right, and I found a second, independent reason it was being lost:

```python
walker.budgeted_walk(...)   # keeps only the FIRST observation of each (atom, before) pair
```

Deduplication is correct when a repeat carries no new information about the *effect*. It is fatal for
guards, because the second observation of a pair is the only place a blocked witness can appear when the
first was positive. Measurement and evidence collection are different jobs; `learn_the_guard_v1` collects
its own raw walk and found **386 blocked witnesses** in it.

I also had to fix two defects in my own tool before running it: a stub function referenced inside an
`if False` conditional, and a comment claiming a raw walk while still calling the deduplicating one. Both
would have made the instrument lie quietly.

## 2. The measurement

Six machines, 293 held-out transitions, 50 guard keys learned (37 with two witnesses):

| arm | predictions | wrong | accuracy | coverage |
|---|---|---|---|---|
| A — no guards | 227 | 42 | **0.8439** | 0.6985 |
| B — guards override laws | 227 | 65 | 0.7774 | 0.6985 |
| C — guards, two witnesses required | 227 | 46 | 0.8315 | 0.6985 |
| D — guards, **fallback only** | 227 | 42 | **0.8439** | 0.6985 |

`guards_raise_coverage: false`. `guards_do_not_trade_coverage_for_accuracy: false`.

**Arm D is bit-identical to arm A on every machine** — same predictions, same errors, same refusals. That
is not "guards didn't help". It is the structural answer:

> A refusal is a held-out state whose `(atom, key)` pair the walk never visited. A guard is learned from
> keys the walk *did* visit. Guard support is the same evidence requirement as law support, so a guard
> literally cannot speak about a state that has no witness — and the states that need covering are
> exactly the ones with no witness of either kind.

Guards and laws draw on the same evidence; guards therefore cannot extend reach, only contradict laws. And
when they contradict, they lose: `B` and `C` are strictly worse than `A` because a blocked witness at a key
is perfectly compatible with a positive witness at the same key. **The key does not determine firing**, so
a guard that overrides a law destroys a correct prediction. D is identical to A because I made guards
fallback-only — which is the only configuration in which they are harmless, and in which they do nothing.

## 3. What this kills, and what it leaves standing

**Killed:** the guard as a coverage mechanism. The four "guard atoms" from the last work order are real —
`GIT_A3`, `GIT_A4`, `G2_A4`, `LS_A1` do decline to fire — but knowing that buys nothing about states the
walk never saw. A precondition learned from observed keys is another way of describing the sample.

**Still standing, unchanged:** the lifting result. Coverage 0.6985 on six machines and 0.70 on the wider
312-transition set; accuracy 0.844 here (lower than the 0.976 on the five-pair subset, because this set
includes GIT and VAULT where the learner is genuinely wrong — 22 of 35 and 6 of 12).

**The honest shape of the wall, now measured three ways:** no stopping rule, no question, no guard and no
cross-machine transfer has moved coverage past ~0.70. Every one of those mechanisms consumes or re-reads
the same finite walk. Coverage is set by **what the walk saw**, and the only thing that has ever moved it
is a *representation* change (lifting: 0.126 → 0.70). That is now a consistent, thrice-replicated finding
rather than a one-off.

## 4. Verified / unverified / failed

**Verified by execution:** the four-arm table; D identical to A on every machine; 386 blocked witnesses
present in the raw walk; guards harmful when override is permitted.

**Failed, mine, six rounds running:** accuracy-gated stopping, the `0.41` scaling claim, un-lifted
transfer, lifted transfer, and now the guard. One clear win (lifting), one named wall.

**Unverified:** whether a guard learned with a *different, narrower* key could ever speak about an
unvisited state. I do not believe it can — the argument in §2 is about evidence, not representation — but
that is reasoning, not a measurement, and I am labelling it as such.

**Not publishable:** any benchmark row — `docker: command not found`, logged once.

**Audited (re-checked):** `92b6db85`, `d6c1661a`, `repo_component_and_cow_engine_v1`,
`instant_swe_skill_store_v1`, `UnifiedCrossModalPetriNet`, `learned_skill_id`, `click@ac0e297`,
"244 verified commits" — 2 files each, both mine; none is a commit or module here.

## 5. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 51.2 s · 6 machines
```

5 new tests, including one asserting arm D is *literally* identical to arm A rather than merely no better.
Guard PASS (17 rules).

## 6. Next

Three mechanisms have now failed to raise coverage past 0.70, and all three shared one property: they
re-read the existing walk. The untested axis is the one thing this project has never varied —
**how much the walk explores before the learner speaks**. The supply measurement says questions run out at
~14 probes on an enumerated space, which is why acquisition saturated. But `walk_steps` has always been a
fixed 120. Coverage as a function of walk length, at fixed everything else, would say whether the wall is
the walk's *size* or the representation's *reach* — and unlike the last three rounds, that experiment can
only produce an answer, not a reparameterisation of the same evidence.
