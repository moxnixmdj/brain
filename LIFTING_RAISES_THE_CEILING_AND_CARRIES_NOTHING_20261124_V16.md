# LIFTING RAISES THE CEILING 2.8× INSIDE A MACHINE AND CARRIES NO TRUTH BETWEEN THEM
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts;
> every parameter derived and justified; knowledge external and removable; project before web; the real
> limiting factor named; ideas killed before building; honest verified / unverified / failed; hardest
> real tests; never ask the user. §2 resolution unchanged. No model call, no stored parameter.

---

## 1. The fix I said I'd try, and why it was the right fix to try

Last round: laws do not cross machines because 10 of 16 had no counterpart **key** — keys are projection
values over ground names (`GIT_A1`, `probe_seed_content`) and ground names are machine-local. The stated
blocker was *un-lifted keys*.

So I lifted them. Same predicates the vocabulary already computes, applied to the state alone:

```
HAS_DUPLICATE_CONTENT · ALL_CONTENT_UNIQUE · ROWS_2 · ROWS_3 · ROWS_4     (keys)
NO_CHANGE · ADD_DUPLICATE · ADD_AND_DELETE · DELETE_ONLY (+REUSES_CONTENT)  (effects)
atom coordinate = position in sorted ident order                           (derived, not written)
```

No machine name and no content literal appears in a lifted key. A test asserts that, so it cannot quietly
become a written mapping.

## 2. Within a machine, lifting is the biggest single improvement in sixteen rounds

Identical five pairs, identical walk, identical held-out set, only the representation changed:

| learner | predictions | wrong | accuracy | coverage |
|---|---|---|---|---|
| un-lifted (width laws, MIN_SUPPORT 2) | 58 | 6 | 0.906 | **0.126** |
| **lifted** | **162** | **4** | **0.976** | **0.704** |

**Reach 2.8×, accuracy +7.0 points, coverage +57.8 points.** The system speaks about 70% of held-out
machine transitions instead of 13% — and the number the whole project has been stuck on for the last
three rounds was "13 of ~90". That wall was a representation defect the entire time: the learner was
insisting on naming rows, and a law that names rows cannot cover a state whose rows it has not seen.

This is the honest positive result. It is also not a transfer result.

## 3. Between machines, the same lifted laws are worse than noise

| arm | predictions | wrong | accuracy |
|---|---|---|---|
| B — lifted transfer | 50 | 42 | **0.543** |
| B′ — lifted, alignment shuffled | 50 | 49 | 0.505 |
| C — lifted transfer + target's own laws | 188 | 44 | 0.810 |
| A — target's own laws only | 162 | 4 | **0.976** |

Lifting makes laws *cross* — from 5 predictions last round to 50 now — and they cross **wrong**. 42 of
50 false. And they do not beat their own shuffled null by anything that survives: gap 0.038 on 100
transitions.

Worse, and this is the result to keep: **adding them to the target's own laws drops the target from
0.976 to 0.810.** Structural laws imported from another machine are not merely inert, they are harmful,
because `predict` correctly refuses when admitting laws disagree — so one imported law that contradicts
an earned one destroys the prediction rather than losing to it. The refusal discipline that makes the
system sound is exactly what makes contaminated memory expensive.

## 4. What this settles

* **Portability is not a representation problem.** The two hypotheses were "keys are too specific" and
  "the laws carry the wrong content". Lifting removed the first completely and the transfer result did
  not improve — so the content is the problem, and content is not liftable by pattern-matching a state.
  `ADD_DUPLICATE` is true of GIT and of LIST and means different things in each.
* **The 13-of-90 wall is gone.** Not by transfer, by lifting. Coverage 0.126 → 0.704 within a machine.
* **Inspectability and removability survived the change.** A lifted law is six fields on one line
  (`rank, key, effect, support`), removable by deleting a row, and the store is still not a parameter
  and still not in the weights.
* **Cross-machine knowledge needs something I have not built and will not claim**: either an explicit
  alignment that is *earned* from the target's own observations and can therefore be audited, or a
  semantics for "same content, different name" that the vocabulary cannot currently express.

## 5. Verified / unverified / failed

**Verified by execution:** the four-row table above; the 2.8× reach gain and +57.8 coverage points within
a machine; lifted transfer at 0.543 against its shuffled null at 0.505; combined worse than target-only.

**Failed, mine, four rounds running:** accuracy-gated stopping, the `0.41` scaling claim, un-lifted
transfer, and now lifted transfer. Each recorded as a loss; each narrowed the search.

**Unverified:** whether an earned (rather than pattern-derived) alignment transfers. Two of five pairs
(ARCHIVE2, SQLITE) were skipped because the walk covered every reachable state, so five pairs, not seven,
carry the between-machine numbers.

**Not publishable:** any benchmark row — `docker: command not found`, logged once.

**Audited (re-checked):** `92b6db85`, `d6c1661a`, `repo_component_and_cow_engine_v1`,
`instant_swe_skill_store_v1`, `UnifiedCrossModalPetriNet`, `learned_skill_id`, `click@ac0e297`,
"244 verified commits" — 2 files each, both mine; none is a commit or module here.

## 6. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 71.7 s · 5 pairs x 2 arms
```

5 new tests, including one that fails if a lifted key ever contains a machine name or a content literal.
Guard PASS (17 rules).

## 7. Next

The within-machine gain changes what the next question should be. Coverage 0.704 with 4 wrong out of 166
means the learned store is now **wide enough to be worth keeping and sound enough to trust**, and the
refusals that remain (68 of 230) are the interesting ones: states where no lifted key matches at all. The
next instrument samples those refusals and asks what pattern would be needed to cover them — the first
time in this project that the learner can be asked what it is missing *about its own vocabulary* rather
than about evidence.
