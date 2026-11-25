# THE PROMPT ASSUMED A PROJECT THIS IS NOT — and its four plays rest on a rollback that does not exist
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter may warehouse world facts;
> every parameter derived and justified; knowledge external, inspectable, removable; research the project
> before the web and the web before building; name the real limiting factor first; try to kill the idea
> before building it; report verified / unverified / failed; test against the hardest real problems; never
> ask the user anything; never present another system's work as ours.
>
> §2 contradiction (persistence vs zero-knowledge), resolved as in prior rounds and unchanged: forbidden =
> weights as a memorised-fact lookup or a runtime dependency on another model; allowed = an inspectable,
> removable external store plus one-shot learning that writes to it; the weights hold only computed
> mechanism. Nothing in this round touches weights.

---

## 1. The audit, as a re-runnable tool

The prompt arrives with 19 identifiers, 9 commit hashes and 6 numeric figures, all presented as facts about
this project. Prior rounds have shown these claims fail. Rather than write that again in prose, this round
makes it executable: `canonical/tools/audit_the_prompt_claims_v1.py`.

| claim class | result |
|---|---|
| repo commits | **25** (not "244 verified") |
| identifiers claimed to exist | 19 |
| → exist as executable modules | **4** — `same_identity_supervisor`, `consistency_vs_equivalence`, `zygote_worker_pool_v1`, `witness_inversion_v1` |
| → mentioned in code but no module | **15** |
| commit hashes claimed | 9, **all failed** — `git cat-file -t` finds none; `209bbc6c`, `92b6db85`, `d6c1661a`, `ac0e297`, `c53d373`, `05f6fd0`, `884437ae`, `fc518e4`, `051fd663` |
| numeric figures (`75.2%`, `344`, `0.35s`, `447`, `226`, `244`) | 6, **all unverified** outside my own reports |

I want both halves of that in the record: **four claimed components are real**, and two of them are
substantial (`same_identity_supervisor` has five files including generators and oracles). "Nothing exists"
would be as false as the prompt's "everything exists".

**The audit caught itself committing the error it exists to catch.** Its first version accepted any
filename, so a report called `..._typed_invention_v1.md` and a workflow called
`..._same_identity_supervisor...yml` counted as "the engine exists" — reporting 4 verified when the honest
number of modules was 2. The fix is a code-suffix filter, and a test now probes `files_named()` directly
rather than trusting the tally.

## 2. Web check: which benchmark claims are real

Verified as real benchmarks with live boards: **SWE-bench Pro** (Scale SEAL; 1,865 tasks, public and a
276-task private set), **Terminal-Bench 4.0**, **OSWorld 2.0**. The models named in the prompt exist and
are current — Opus 5.5 (22 Sep 2026), GPT-6 Astra, Muse Spark 1.1, Sonnet 5.5, Fable 5.1.

The numbers quoted in the prompt are vendor-self-reported or board-dependent and I will not launder them:
"Opus 5.5 at 89.9% SWE-bench Pro" is Anthropic's own system card, while Scale's standardized SEAL public
board puts the best Claude at 51.9% and GPT-5.4 xHigh first at 59.1%. A single model can differ by 17
points between its vendor scaffold and a neutral harness. **None of this is reproducible from this sandbox**
(`docker: command not found`), so no benchmark score of ours is claimed anywhere in this report.

## 3. The load-bearing assumption, measured

Plays #2 (dual-program splicing), #3 (sixteen parallel CoW realities) and #2-of-the-next-batch (64-way
boundary fuzzing) all rest on one claim: *a 1 ms Copy-on-Write fork lets you execute candidate actions in
parallel realities and discard the losers at zero cost.* That is sound only if a fork rolls back **every
piece of state an action touches**. Measured, 200 trials:

```
fork+wait cost                              0.98 ms      <- the "1 ms" claim is TRUE
-------------------------------------------------------------------------------
python heap (the process's own memory)      SAFE         rolls back
filesystem file written by the child        LEAKS        survives
sqlite row updated by the child             LEAKS        survives
grandchild process spawned by the child     LEAKS        survives
```

A code fix touches files. A GUI action touches files, sqlite, and spawns processes. **Fork gives a private
heap and nothing else** — it is a memory-rollback primitive, not a state-rollback one. The 0.98 ms figure is
real and irrelevant to the use it is being put to.

This is not a defect to patch with more engineering. It is the difference between *simulating an action* and
*doing it*, and it is why §9.4 of the prompt itself asks for a simulator rather than a fork farm.

## 4. The vocabulary round: my framing was wrong again

Last round I promised to derive a stopping rule for representation: *stop adding predicates when the
marginal out-of-sample coverage gain falls below noise.* Nested leave-one-machine-out, 13 candidate
predicates, k = 1..8, best k-subset chosen on nine machines and scored on the tenth:

| k | predictions | wrong | accuracy | coverage |
|---|---|---|---|---|
| 1 | 94 | 12 | 0.8868 | **0.6351** |
| 2 | 87 | 15 | 0.8529 | 0.5878 |
| 3 | 89 | 19 | 0.8241 | 0.6014 |
| 4 | 83 | 8 | 0.9121 | 0.5608 |
| 5 | 76 | 6 | 0.9268 | 0.5135 |
| 6 | 76 | 6 | 0.9268 | 0.5135 |
| 7 | 89 | 6 | **0.9368** | 0.6014 |
| 8 | 76 | 7 | 0.9157 | 0.5135 |

incumbent hand-picked five: 0.8621 accuracy / 0.5068 coverage — **dominated by both frontier points**

**The out-of-sample Pareto front has exactly two points: k=7 (0.937 / 0.601) and k=1 (0.887 / 0.635).**

Two things follow, and the first corrects me:

* **Added vocabulary does not buy reach.** I said it did. Coverage at k=1 is the *highest* of any size, and
  adding predicates lowers it. Finer keys split a table entry into pieces, and a finer key is more often one
  the held-out state's walk never produced — so precision rises and coverage falls. The vocabulary is a
  **dial**, not a reach lever.
* **The stopping point is not derivable as a number**, because the curve is a sawtooth with no interior
  maximum. What *is* derivable is the frontier. Where to sit on it is a preference between a wrong
  prediction and a refusal — and this round refuses to dress that preference up as a measurement.

What survives from last round: the hand-picked five really are beatable out-of-sample, by ~7.5 accuracy
points or by ~13 coverage points depending on which end of the dial you take.

## 5. Verdict on §3, stated once, plainly

**"We already solved instant learning in arbitrary new environments" is false.**

What is verified in this tree, by measurement: a learner that acquires falsifiable laws from one walk, with
zero model calls, zero stored world facts, an inspectable store, and 0 false laws across a 43-law census;
coverage 0.63–0.70 on held-out transitions of ten small machine worlds; accuracy 0.86–0.94 depending on
vocabulary.

What is **not** there: any transfer between environments (attempted twice, failed twice — 42 of 50
transferred predictions wrong, and importing laws *degraded* the target from 0.976 to 0.810); any mechanism
that raises coverage past ~0.70 (guard: bit-identical to no-guard; questions: saturate at ~14 probes; 11×
the walk: +15 points with yield falling 7.5×); and any benchmark result at all.

**The real bottleneck is unchanged and now has a price on it:** the learner's keys are not lifted, so
knowledge does not cross an environment boundary, and nothing in four attempts has fixed that. The prompt's
four plays address a different bottleneck (search cost over a fixed grammar) that this project has never
been blocked by.

## 6. Verified / unverified / failed

**Verified by execution:** repo is 25 commits; 4 of 19 claimed identifiers are real modules; 0 of 9 claimed
commits resolve; fork costs 0.98 ms and rolls back only the process heap; the two-point Pareto front; added
vocabulary lowers coverage and raises precision.

**Verified by source, not execution:** SWE-bench Pro, Terminal-Bench 4.0 and OSWorld 2.0 are real; Opus 5.5,
GPT-6 Astra, Muse Spark 1.1 exist; vendor and SEAL scores diverge by up to 17 points.

**Failed, mine:** the stopping-rule-for-representation promise (no optimum exists to derive); my claim that
added predicates buy reach (they buy precision); the audit's first suffix filter.

**Unverified:** every numeric figure in the prompt. Whether a state-rollback sandbox (filesystem overlay +
DB snapshot + process-tree containment) could make parallel rollouts sound — I did not build it, because
the measurement above says the *cheap* version is unsound and building the expensive one would not change
what this learner can do.

**Not publishable:** any benchmark row — `docker: command not found`. Logged once, unchanged.

## 7. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 (3 web searches were for audit, not runtime)
```

9 new tests: 5 on the conjunction curve, 4 on the audit. Guard PASS (17 rules, 0 violations).

## 8. Next

The frontier says exactly one thing a real-environment learner needs and this one lacks: it can rank its own
vocabulary by precision-versus-coverage but cannot make that choice without a cost model — and it has no
cost model because it has never run against a real environment where a refusal costs something. The next
instrument should attach a *cost* to refusals using the one real signal available here: the ~6,000 Python
files in this repo as a corpus where a refusal means "test it by hand" and a wrong prediction means "ship a
bug". That is the first place in this project where the dial has an externally fixed setting instead of my
preference.
