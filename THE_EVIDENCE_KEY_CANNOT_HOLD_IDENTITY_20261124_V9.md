# THE EVIDENCE KEY CANNOT HOLD IDENTITY — and it reversed one of my own results
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Requirements restated: own model, zero runtime model calls; no parameter warehouses world facts;
> every parameter derived and justified; knowledge external and removable; project before web; the real
> limiting factor named; ideas killed before building; honest verified / unverified / failed; hardest
> real tests; never ask the user.
> §2 resolution stands unchanged. No model call, no stored parameter, no network this round.

---

## 1. What I was asked to do versus what mattered

The prompt's three steps were Iteration-83/84 docker benchmarks, AST anti-unification and CoW fuzzing.
Two of those rest on components that **do not exist in this repository** (audited below), and the
benchmark step is blocked by a missing capability (`docker: command not found`). So I went to the
bottleneck my own last control had located:

> reach is a property of the **teacher's state diversity**, not of the transfer rule.

The question: does a better exploration policy raise **contrast density** — usable laws per hundred
transitions — enough that transfer stops depending on one fortunate machine?

## 2. The answer, after the bug that had to be fixed first

| policy | transitions | usable laws | per 100 | machines producing any |
|---|---|---|---|---|
| RANDOM (the sampler every round used) | 633 | 4 | **0.632** | 2 |
| TARGETED (aim at a contrast already seen) | 293 | **0** | **0.000** | 0 |
| COVERAGE (aim at an unseen state) | 603 | 3 | 0.498 | 2 |

**No policy beats the plain random walk, and my prediction was the worst of the three.** `TARGETED`
produced zero usable laws: aiming at a contrast that must already exist aims at nothing.

And this table is the *second* result. The first run of the same instrument said COVERAGE won at
**1.637** per 100 (2.6× random) with 3 machines producing laws. That was **wrong**, and finding out why
is the actual finding of this round.

## 3. The bug, and why it is bigger than the bug

The instrument was nondeterministic. Not slightly — the same seed produced different walks about one
run in four. Three layers, each found by a test that kept failing intermittently:

1. **A state signature containing nested tuples** was compared through a `set`, whose iteration order
   depends on Python's per-process string hash. Fixed by serialising to a sorted string.
2. **A sort with all-equal keys.** Every candidate atom shared the same signature, so the sort decided
   by the RNG draw over a stable list — the winner was whichever atom came last, not the one the policy
   chose. Fixed by tie-breaking on the atom identifier.
3. **THE DEEP ONE.** The dedup key was `(atom, state)` — and on GIT a state's rows are **commit SHAs**.
   A SHA embeds the commit timestamp, so *the same walk re-run produces different identifiers*, and two
   identical walks recorded **different numbers of transitions**. The learner's evidence set was
   nondeterministic even though the policy was not.

The fix, and the sentence worth carrying into every future environment:

> **The evidence key may contain content. It must never contain identity.**

Real environments are full of identifiers that change under an unchanged observation: commit SHAs,
pids, UUIDs, temporary paths, timestamps, socket ports. A learner whose evidence key includes them
**cannot reproduce its own results** — and, worse, it will silently under- or over-count its own
evidence. That is not a testing nuisance. It is a correctness defect in the learning, and it was
present in the exploration path of this instrument on the day it was written.

With content-keyed evidence, COVERAGE's 2.6× advantage **evaporated** (0.498 against random's 0.632).
The advantage had been an artifact of counting the same content twice whenever its SHA changed.

## 4. What is verified

* **`TARGETED` is worse than random** — 0 usable laws in 293 transitions against random's 4 in 633.
  Verified, and it was my prediction, so it is recorded against me rather than softened.
* **No exploration policy tested beats a random walk on contrast density.** Verified across 10
  machines, 3 seeds, 40 steps.
* **Content-keyed evidence is required for reproducibility.** Verified by construction and by 8
  consecutive clean runs after the fix, against intermittent failure before it.
* Content-identity instability is **real in this environment**: GIT rows are SHAs and differ between
  two identical walks. This is a property of the environment, not an artifact of the test.

## 5. What is unverified or failed

**FAILED, and it was my own claim from last round's instrument:** "COVERAGE raises contrast density."
The measured superiority was a bug. With the corrected learner it is 0.498 vs 0.632 — *worse*. Any
future use of that number must use the V2 artifact.

**Not established:** that contrast density can be raised by any cheap policy at all. Three were tried;
the best is the one that was already in use. The bottleneck after this round is therefore sharper and
less comfortable: if a random walk is the best available evidence collector, then **evidence density is
a property of the machine, not of the agent's cleverness**, and the fix has to be structural —
new atoms, new state space, or new instruments — not a better walk.

## 6. Audited claims from this prompt

Method: `grep -rl` over the tree and `git cat-file -t` for every hash named.

**FAILED — named as existing engines, commits, or results; absent:**

`92b6db85` (Iteration 83) · `d6c1661a` (Iteration 84) · `repo_component_and_cow_engine_v1` ·
`instant_swe_skill_store_v1` · `UnifiedCrossModalPetriNet` · `learned_skill_id=None` ·
`click@ac0e297` · `click@c53d373` · `click@fc518e4` · `werkzeug@884437ae` · `werkzeug@051fd663` ·
"244 verified post-training OSS commits". None is a commit in this repository; the only file naming the
click/werkzeug SHAs is my own earlier audit.

**VERIFIED with context:** `HONEST_SUITE_BASELINE` 344 failures — real, from the **2026-10-14** artifact
(344 failed / 11,166 passed); the 2026-11-03 baseline is **984 failed / 15,255 passed**, and the tree's
own `HARDCORE_SWE_PROBLEMS_20261029_V1.md` calls the October document "already stale" and measures ≈310.
`EffectContract` exists in 12 files. `docker_available: false` is correct here.

**Blocked, logged once:** no Docker in this sandbox, so SWE-bench Pro / Terminal-Bench / OSWorld-V2
cannot be run and no official number can be published from here. This is the only outstanding item that
is a capability of the environment rather than a decision of mine.

## 7. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0
```

4 new tests, all green across 8 consecutive repetitions (they were intermittent until the
content-keyed fix, which is how the defect was found). Repo integrity guard PASS, 17 rules. Committed on
`arena/50c05c04-brain`.

## 8. Next

The measurement moved the bottleneck somewhere I cannot fix with a policy: evidence density is set by
the machine. So the next instrument does not try to walk better — it asks whether the **atom set**
bounds density. Concretely: for each machine, hold the walk fixed and add one new atom that changes a
relation no current atom changes (ordering, permissions, size). If density rises, the lever is
vocabulary of *action*, not of *state*, and that is a different and much larger claim than anything
tested here so far.
