# THE MISSING OBJECT IS A GUARD, NOT A PREDICATE
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts;
> every parameter derived and justified; knowledge external and removable; project before web; the real
> limiting factor named; ideas killed before building; honest verified / unverified / failed; hardest
> real tests; never ask the user. §2 resolution unchanged. No model call, no stored parameter.

---

## 1. Now that it speaks, ask it what it cannot say

Lifting took coverage from 0.126 to 0.704 on five pairs. On the full set — six machines with a non-trivial
held-out set, 312 held-out transitions — coverage holds at **0.7019: 219 covered, 93 refused**. The gain
was not an artefact of five chosen pairs.

So the refusals are now the object worth studying. For every refused state I recorded the atom applied,
the lifted key of the state, and the effect produced — and asked two questions: how many refusals would a
*merely narrower* law have covered, and how many atoms show **different effects in the same key**?

```
refusals                                          93
a narrower law would already cover                63   (68%)
context-dependent atoms                            6
  of which a GUARD (one effect, plus NO_CHANGE)     4
  of which genuinely two effects, both firing       2
separable by the existing keys                      1
```

## 2. The distinction that changes the next question

I nearly reported "six atoms have context-dependent effects, so the vocabulary needs more state
predicates". Reading the two effects per atom shows that is wrong for four of the six. The pattern is:

```
GIT_A3   ADD_AND_DELETE+REUSES_CONTENT   or   NO_CHANGE
GIT_A4   ADD_AND_DELETE+REUSES_CONTENT   or   NO_CHANGE
G2_A4    ADD_AND_DELETE+REUSES_CONTENT   or   NO_CHANGE
LS_A1    ADD_AND_DELETE+REUSES_CONTENT   or   NO_CHANGE
```

`NO_CHANGE` is not a second behaviour. It is the atom **declining to fire**. The atom has one effect and
a *precondition*, and the vocabulary — which describes what an atom does, conditioned on the state it
does it in — has no way to say *when it may do it*.

Only two atoms genuinely have two firing behaviours (`GIT_A1`, `G2_A1`: add-and-delete versus
add-duplicate, both real changes), and one of the six is already separable by the existing keys.

**So the missing object is a guard.** Not a wider state predicate. A precondition with its own
learnability, its own falsification test, and its own refusal semantics — the same shape as the law but
quantified over *when* rather than *what*.

This is worth stating plainly because it is the fourth time in this project that the intuitive reading of a
measurement was the wrong one: "context-dependent effect" sounds like "needs richer state description",
and 4 of 6 do not.

## 3. The remaining 68% are cheap, and that is the encouraging part

63 of 93 refusals are states where the atom has one effect in this machine and simply is not covered —
the law is too narrow, not missing. Those are recoverable by the mechanism already built, given a
narrower key. Only 6 atoms (in 4 + 2 states-apiece groups) need something new.

So the store's current state, honestly:

| quantity | value |
|---|---|
| held-out transitions it speaks about | 219 / 312 (0.7019) |
| refusals recoverable with a narrower law | 63 |
| refusals needing a new object (guard) | 4 atoms, ~21 states |
| refusals needing a richer state vocabulary | ~2 atoms, 9 states |
| false laws across the whole census | 0 |

## 4. Verified / unverified / failed

**Verified by execution:** coverage 0.7019 on six machines / 312 transitions; the 63 / 4 / 2 split;
`GIT_A1` and `G2_A1` have two firing effects; four atoms are guards by the `NO_CHANGE` test; one atom is
separable with existing keys.

**Unverified:** that guards are learnable by the same witness machinery. The shape is promising — a guard
is "atom fires only when P", which is falsifiable from a single observation of it not firing — but I have
not built it and will not claim it works. Also unverified: whether 63 "narrower key" refusals really are
recoverable; the count comes from a proxy (same atom, single effect, no admitting law), not from running a
narrower learner.

**Failed, mine, five rounds running:** accuracy-gated stopping, the `0.41` scaling claim, un-lifted
transfer, lifted transfer. Four losses, one clear win (lifting), and now a named work order.

**Not publishable:** any benchmark row — `docker: command not found`, logged once. This is the only item
in the project I cannot move from here, and it means every number above is an internal measurement.

**Audited (re-checked):** `92b6db85`, `d6c1661a`, `repo_component_and_cow_engine_v1`,
`instant_swe_skill_store_v1`, `UnifiedCrossModalPetriNet`, `learned_skill_id`, `click@ac0e297`,
"244 verified commits" — 2 files each, both mine; none is a commit or module in this repo.

## 5. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 50.3 s · 6 machines
```

4 new tests pinning the 63/4/2 split, the guard classification, and that the work order names atoms
rather than machines. Guard PASS (17 rules).

## 6. Next

Build the guard. A guard is `(atom, key, precondition-pattern, effect)` learned from observations where
the atom was applied and nothing changed — evidence the current learner *discards*, treating a no-op as
a non-event. The test is the same instrument: does adding guards raise coverage above 0.70 **without**
costing accuracy, and does it cover the 4 guard atoms specifically? If a no-op is a negative witness and
the learner has been throwing them away, that is the cheapest available improvement in the whole system:
the evidence was already in the walk.
