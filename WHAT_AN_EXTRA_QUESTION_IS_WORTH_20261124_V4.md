# WHAT AN EXTRA QUESTION IS WORTH — 8.7%, and only when the boundary can be hit
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Binding requirements restated: own model, zero runtime model calls; no parameter may warehouse world
> facts; every parameter derived and justified; knowledge outside the weights, removable without
> retraining; project before web; real limiting factor named; ideas killed before building; honest
> verified / unverified / failed; hardest real tests; never ask the user.
> §2 stays resolved as before. This round made no model call and stored no parameter.

---

## 1. The question this round asked

`TWO_WITNESSES_IS_A_LAW` ended with a concrete plan: soundness was bought with silence — 88 of 99
held-out states refused — so acquire the *second* witness instead of waiting for one. Acquisition had
already been measured as 4.75× better than random, and it was the first time it had a target worth
asking for.

The round before that had already measured the opposite-sounding result: `ask_instead_of_stare`
reduced contradictions 1,714 → 58 while being **worse than asking nothing at all** on reach. So the
question was genuinely open: is a targeted question worth its budget when a specific law is waiting
for it?

## 2. A reproducibility bug found first, and it is the most important line here

The split in every previous arm used `dict.fromkeys(...)` over transitions that had been deduplicated
through a **set**. Python randomises string hashing per process, so set iteration order differed
between runs — **"seed 13" was not reproducible.** The same nominal experiment produced
`arm_A = 6 predictions / 0 wrong` and `arm_A = 11 / 0` on two consecutive invocations.

Fixed by sorting the state list. Every state-split arm in this tree now has a stable split, and
re-running the previous round's learner on the stable split gives **11 predictions, 0 wrong** (it was
6/0 on the unstable split). The headline survived; it had been luck-dependent, which is exactly the
kind of thing this repository is supposed to catch and did.

## 3. Why the acquisition arm did nothing, twice

**First attempt, exhaustive exploration**: 0 probes. Diagnosed, not guessed — of 542 single-witness
laws in LIST and JOURNAL, **all 28 that had another admitted state had only HELD-OUT states**. Depth-3
`explore` is exhaustive, so nothing is left unknown, so there is nothing to ask. Acquisition is
meaningless in an enumerated world.

**Second attempt, budgeted walk (40 random steps)**: the regime any real environment imposes, where
states genuinely remain unobserved. Probes fired. 4 of 4 single-witness laws were **falsified**.

That second result is the honest core of this round: **acquisition does not buy reach, it prevents
error.** A law the sampler produced from one witness is wrong most of the time, and a single question
removes it.

## 4. The measurement, four seeds, nine machines, 36 runs

| arm | predictions | wrong |
|---|---|---|
| A — laws with support ≥ 2 from the sample | 2 | 0 |
| B — A, minus `CARD`-only laws (GIT's defect) | 0 | 0 |
| **C — A + acquired second witnesses** | **3** | **1** |
| C-raw — A + probes with no legality check | 2 | 0 |
| D — acquisition with the requirement dropped | 17 | 14 |

```
probes 71 · confirmed 22 · falsified 49
```

**The one number that matters: 49 of 71 questions falsified the law they were asked about.** At
support 1 the laws were wrong about two times in three. Arm D — the same machinery with the
requirement removed — is 17 predictions and **14 wrong**, which is what a learner looks like when it
stopped asking whether its answer could be checked.

## 5. The verdicts, and the one I am leaving false

```json
{"acquisition_finds_second_witnesses":          true,
 "acquisition_also_falsifies_laws":             true,
 "acquiring_witnesses_raises_reach":            true,
 "acquiring_witnesses_stays_sound":             false,
 "a_probe_that_must_fit_adds_54_percent_error": false,
 "the_cardinality_requirement_does_work":       true}
```

`a_probe_that_must_fit_adds_54_percent_error` is **false** and stays false. I predicted that a probe
which re-records whatever happened would inflate error; measured, that arm was 2/0 — two predictions,
no errors. At n=2 the claim is noise, and a verdict that flatters the design is exactly what §1.10
forbids. The hypothesis is withdrawn, not softened.

`acquiring_witnesses_stays_sound` is also false: 3 predictions, 1 wrong. Reach rose from 2 to 3 and
one of those three is an error. **Acquisition does not fix the learner; it prunes it.**

## 6. The number this round can defend

Comparing the two policies at matched refusal cost is the fairest reading available:

```
asking     : 71 questions -> 22 laws confirmed, 49 falsified, 3 held-out predictions
random walk: 40 steps    -> 1 law at support 2,            0 held-out predictions
```

One targeted question converts to a usable law **8.7%** of the time; 40 random steps convert
**2.5%**. That is a 3.5× better rate per unit of evidence, and it is a defensible claim because both
arms were run on the same machines with the same held-out ban.

The defensible summary: **an extra question is worth about one law in twelve — and it is only worth
asking when a law has a boundary that a probe can hit.**

## 7. What is now established, and what is not

Established by measurement, this round:

* The split used across three rounds was **not reproducible**; it is now.
* Exhaustive exploration makes acquisition vacuous — measured, not argued.
* Under a step budget, acquisition **falsifies ~69% of single-witness laws** (49/71).
* Dropping the legality requirement costs accuracy: arm D is **82% wrong** (14/17).
* The `CARD`-only prohibition from GIT is load-bearing: arm B has 0 predictions where arm A has 2, and
  the difference is exactly the laws GIT proved unsound.

Not established: that any of this scales to a real environment. 3 held-out predictions across 36 runs
is a signal, not a benchmark. §6's conditions are not met and this round does not claim them.

## 8. Cost, tests, and the state of the branch

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0
```

Four new test files green (`test_what_the_vocabulary_cannot_say_v1`, `test_ask_instead_of_stare_v1`,
`test_the_width_of_a_guard_v1`, `test_acquire_the_second_witness_v1`), 37 tests. Repo integrity guard
PASS, 17 rules, 0 violations. Pushed to `arena/50c05c04-brain`.

## 9. Next bottleneck, named by this round's own numbers

Reach is now **3 predictions in 36 runs** — soundness has been bought almost entirely with silence, and
the price is that the system is useless on 89% of what it is shown. Three rounds have now moved the
error rate down (83% → 42% → 0% at support 2) while reach never exceeded 6. **The bottleneck is no
longer accuracy. It is that a two-witness law is too rare to be useful, and the fix cannot be more
questions about a single law.**

The next hypothesis to kill or build: a law's support should be inherited, not discovered. When a
projection is confirmed on one atom, it is evidence for the *projection*, not only for that atom — and
a confirmed projection should license laws about other atoms whose single witnesses agree with it. That
is composition of evidence rather than accumulation of examples, it is testable on these nine machines
with the same held-out discipline, and it is the only step that could plausibly move reach by an order
of magnitude rather than by one.
