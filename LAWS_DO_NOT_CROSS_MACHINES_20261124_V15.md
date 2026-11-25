# LAWS DO NOT CROSS MACHINES — and it is a naming problem, not an evidence problem
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts;
> every parameter derived and justified; knowledge external and removable; project before web; the real
> limiting factor named; ideas killed before building; honest verified / unverified / failed; hardest
> real tests; never ask the user. §2 resolution unchanged. No model call, no stored parameter.

---

## 1. The test the project had never run honestly

Last round ended by saying the next real test is transfer: laws learned in one machine applied to a
*different* machine, scored on that machine's held-out transitions, with the vocabulary drawn only from
the walk it actually took.

The obvious objection kills the obvious implementation first. Every machine names its atoms differently
— `GIT_A1`, `LS_A1`, `JN_A1`, `VAULT_A2` — so a literal mapping is a hand-written table of world facts,
which is exactly the forbidden parameter. The alignment therefore had to be **derived**. It is: each atom
is fingerprinted by `(rows_added, rows_deleted, rows_after, copies_existing_content)`, computed only from
observations, and atoms are matched greedily widest-agreement first. No pair is written down anywhere in
the code.

Four source:target pairs, arms A / B / null / C:

| arm | predictions | wrong | accuracy | coverage |
|---|---|---|---|---|
| A — target only | **58** | 6 | **0.906** | 0.136 |
| B — laws transferred | 5 | 2 | 0.714 | 0.023 |
| B′ — **shuffled** alignment | 3 | 0 | 1.000 | 0.014 |
| C — transferred, then refined | 42 | 6 | 0.875 | 0.196 |

`the_derived_alignment_beats_a_shuffled_one: false`. `transfer_plus_refinement_beats_target_only_on_reach:
false`. `laws_cross_machines_at_all: true` — five predictions, so the mechanism runs, and it is
worthless: the shuffled null predicts *more accurately* than the derived alignment, on three transitions,
which is the clearest possible statement that the alignment carries nothing.

## 2. Why — measured, not argued

For each source law I asked: does its **key** occur anywhere in the target's reachable states, and does
its **effect** name only rows the target could hold?

```
source laws        16
key misses         10     <- 10 of 16 laws have no counterpart key in the target at all
crossable           6
```

Even the six "crossable" ones mostly refuse, because a key that happens to coincide on `CARD` (a number)
or `CONTENT_COUNTS` (a multiset of contents) still has to survive `predict`'s rule that **every** admitting
law agrees — one imported law that disagrees with a target law turns the state into a refusal, not a
guess.

The mechanism is one sentence: **a law's key is a projection value over ground names, and ground names
are machine-local.** A law that says *"in every state with these row identities, write this content"*
cannot apply to a machine whose rows have other identities, no matter how similar the behaviour. The only
projections with machine-portable keys are the ones that collapse names away — `CARD` and
`CONTENT_COUNTS` (and `IDENT_CONTENT_COUNTS` when the identities coincide, which they do not).

## 3. What this means for the architecture

This is the sharpest negative result the project has produced, and it is sharper than "transfer didn't
work", because it names what would have to change:

> The store is not portable as it stands. The width machinery learns laws over **un-lifted** keys. A
> portable store needs laws whose keys are **lifted** — quantified over the atoms they name, so that
> `"write content already present in a sibling row"` is one law rather than one law per machine.

That is the difference between a table of facts and a rule, and it is the same distinction this project
has been enforcing everywhere else: soundness comes from falsifiability, portability comes from
quantification. The laws are falsifiable (0 false laws across the census) and unquantified.

`C — transferred then refined` is also worth reading carefully: **it equals the shuffled arm exactly**,
42 predictions and 6 wrong in both. Importing laws changed nothing about where the refinement loop went,
because the imported laws were either refused or irrelevant. The 42 predictions in arm C are entirely the
target's own work.

## 4. Verified / unverified / failed

**Verified by execution:** the four-arm table; the derived alignment is behaviourally identical to its
null; 10 of 16 source laws have no key in the target; arm C is exactly arm C′.

**Failed, mine, three rounds running:** the accuracy-gated stopping rule, the `0.41` scaling claim, and
now cross-machine transfer. Each is recorded as a loss.

**Unverified:** whether lifted keys would transfer. I have not built them and will not claim they work —
the measurement above only establishes that un-lifted keys do not, which is a necessary result before
lifting is attempted and not a promise that it succeeds.

**Method caveat, stated because it flatters arm A:** the target's walk is the same 120-step walk in all
arms, so arm A and arm B see the same evidence budget on the target. That is deliberate — it isolates the
one variable — but it means arm B is not "transfer with no target evidence", it is "transfer, scored on
laws the target's own evidence did not produce". Two of four pairs (SQLITE, TARBALL) were skipped outright
because the walk covered every reachable state, so only two pairs carry the result.

**Not publishable:** any benchmark row — `docker: command not found`, logged once.

**Audited (re-checked):** `92b6db85`, `d6c1661a`, `repo_component_and_cow_engine_v1`,
`instant_swe_skill_store_v1`, `UnifiedCrossModalPetriNet`, `learned_skill_id`, `click@ac0e297`,
"244 verified commits" — 2 files each, both mine; none is a commit or module here.

## 5. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 73.0 s · probes 34
```

5 new tests, including one that fails if the alignment is ever replaced by a written table, and one that
pins the derived alignment against its own shuffled null. Guard PASS (17 rules).

## 6. Next

The blocker is named and it is specific: **un-lifted keys**. The next round attempts lifting — take the
`CONTENT_COUNTS` and `CARD` laws, which already have portable keys, and quantify the *effect* over the
atoms it names (add "some row with content already present" rather than "add row `GIT_A3` with
`probe_seed_content`"). Then re-run this exact four-arm instrument, unchanged, and see whether the derived
alignment beats its shuffled null. If it does not, portability is not achievable by lifting either, and
that is worth knowing too.
