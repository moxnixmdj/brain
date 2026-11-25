# THE FAMILY WAS AN ILLUSION — a contrast earned on one function does not transfer to another
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts; every
> parameter derived and justified; knowledge external, inspectable, removable; project then web; name the
> real limiting factor; kill the idea before building it; verified / unverified / failed; hardest real
> tests; never ask the user. No model call, no stored parameter.

---

## 1. Why this experiment, and what it kills

Three rounds built a store of behaviour earned by execution:

- **V26** — 49 entries, each a real contrast with two witnesses (`'' → None`, `'a' → 0`).
- **V27** — flipping two of those witnesses broke **six real tests**, with a clean identity control.
- **V28** — a contrast cannot *predict* which one will matter; sensitivity 0.00.

The one hope left was **transfer**: if two functions in different modules agree about what a contrast does,
the effect is a property of a *family* of code and single experience carries across modules. That is exactly
the §6 requirement — learn from one experience, apply it to an unseen environment.

**It does not exist.** 417 functions in 55 import-safe modules, every one probed with the **same** witness
pair, 7,522 cross-module function pairs:

| quantity | value |
|---|---|
| observed cross-module agreement | **0.6304** |
| permuted null (labels shuffled within each module) | **0.6253 ± 0.0087** |
| gap over null | **+0.0051** |
| gap in null standard deviations | **0.59** |
| raised rate (rare class) | 0.1127 |

A gap of **0.59σ**. The 63% agreement that looks like a shared law is the label mix: most functions return a
value and never raise, so any two of them agree two times in three without sharing anything. Once the
association between a label and the function that produced it is destroyed, the agreement is unchanged.

## 2. The line, complete

| step | claim | verdict |
|---|---|---|
| V26 | entries can be earned by execution | **verified** — 49 entries, 22 raise-contrasts, replayable |
| V27 | entries bind to real test outcomes under intervention | **verified** — 2 of 4 move 6 tests, control moves 0 |
| V28 | entries predict which held-out contrast matters | **failed** — sensitivity 0.00, majority-class tie |
| V30 | entries transfer to an unseen function | **failed** — +0.0051, 0.59σ |

This is now a closed and honest account of what behavioural knowledge earned from execution can and cannot
do here. It can be true, it can bind, and it cannot generalise. Anyone who tells you a handful of observed
input/output contrasts makes a model of code is describing the V26/V27 half and skipping the V28/V30 half.

## 3. Four instrument failures found by running it, each of which would have produced a confident wrong answer

The guard from V29 polices *receipts*. It does not police *harnesses*, and this round produced four:

1. **The 12 largest modules** were all refused for lacking a `__main__` guard — correct isolation, wrong
   population. The run silently computed a "verdict" from **one** module and five functions.
2. **Holding the other arguments at `None`** measured which functions crash on `None`, not what the witness
   does. Labels were `AttributeError → AttributeError`; the contrast was invisible.
3. **Probing `main`** passed `''` as an argv list to a module-level `ArgumentParser`, whose `exit(2)` is a
   `BaseException` and escaped a probe that only caught `Exception`. The whole run died mid-flight.
4. **A module-level `ArgumentParser`** reads the *probe's* `sys.argv`. A `__main__` guard does not stop it;
   the module printed its usage and exited while passing `is_import_safe()`.

Each was found by a number that looked wrong, not by a test. Once found, each became a test: the sample size
is asserted (≥400 functions), entry points are asserted absent from the artifact, and the gap over the null
is asserted small — so if transfer ever *does* appear, this suite fails rather than silently agreeing.

## 4. Verified / unverified / failed

**Verified by execution:** 55 modules, 417 functions, 7,522 pairs, observed 0.6304, null 0.6253 ± 0.0087,
gap 0.0051 (0.59σ), raised rate 0.1127; every module passed `is_import_safe`; `main` excluded everywhere;
all labels in `{NONE, VALUE, RAISED}`. 5 new tests; 15 pass with the V28/V29 suites; measurement-hygiene
guard exits 0.

**Failed, mine, this round:** four harness defects (§3), including one that reduced the population to a
single module while still printing a verdict.

**Unverified:** whether a *within-module* family exists. Cross-module agreement is dead; the same-statements
case inside one module is not measured here and I am not going to assume it in either direction.

**Not producible:** any benchmark row. Still `docker: command not found`. No claim about SWE-bench Pro,
Terminal-Bench 4.0, OSWorld 2.0, or any frontier model is made.

## 5. Cost

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 5.7 s (55 subprocess probes)
```

## 6. Where the work actually stands, thirty rounds in

Everything this project has ever found that survived measurement falls into one sentence: **changes to what
the learner can SAY transfer; everything about what it can PREDICT does not.** Vocabulary choice, lifting,
syntactic transfer — all real. Syntax-as-outcome-predictor, guards, cross-machine laws, contrast prediction,
contrast transfer — all dead.

The honest consequence for §6: single-experience transfer of *behavioural* knowledge does not exist in this
system as built, and no amount of growing the store will produce it. The next attempt must change what the
learner abstracts over, not how many experiences it collects. That is a design decision, not a measurement,
and it is the only door left open that does not require Docker.
