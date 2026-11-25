# STORE THE PROCEDURE, NOT THE DESCRIPTION — portability 2.2% → 95.3%, and the first transfer that adds reach without error
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters · 0 network

> Binding requirements restated: own model, zero runtime model calls; no parameter may warehouse
> world facts; every parameter derived and justified; knowledge outside the weights and removable
> without retraining; project searched before the web; the real limiting factor named before choosing
> a solution; ideas killed before building; honest verified / unverified / failed; hardest real tests;
> never ask the user.
>
> §2 resolution stands: **forbidden** = weights as a lookup of memorised facts, or any runtime
> dependence on another model; **allowed** = an inspectable, editable store the system computes with,
> plus one-shot learning that writes to it, with weights holding only computed mechanism. This round
> made no model call and stored no parameter.

---

## 1. The wall, and the one sentence that dissolved it

Six rounds produced one durable positive (a law with two independent witnesses predicts held-out
behaviour with zero errors) and one exact wall:

> **A reason anchored in one environment's states cannot justify a claim about another's.**

`A_LAW_CARRIES_ITS_REASON` tested the obvious repair — export each law with its **contrast set**, the
projection keys it had to separate — and offered 272 laws across 72 machine pairs. **Six were admitted.**
The reason was precise: a projection key like `("0","1")` or `2` is a fact about *one machine's state
space*, so transfer depended on coincidence and there was none.

The reframing, and it is the whole of this round:

> A contrast does not have to be a **description of states**. It can be a **procedure** — the atoms and
> argument literals whose execution distinguished this law's effect from an alternative. Store the
> procedure. Run it anywhere. The keys are then whatever the new machine says they are.

## 2. The measurement

| | key-as-contrast (last round) | **experiment-as-contrast (this round)** |
|---|---|---|
| laws offered | 272 | 256 |
| reason re-ran on the student | 6 (2.2%) | **244 (95.3%)** |
| admitted after the experiment reproduced | 6 | 12 |
| held-out reach | 88 | **93** |
| held-out errors | 0 | **0** |

```
A  own laws only                        88 predictions,   0 wrong
B  experiment + effect reproduced       93 predictions,   0 wrong   <- the claim
C  experiment ran, conclusion unchecked 88 predictions,   0 wrong
D  blind inheritance                   312 predictions, 216 wrong   <- the refuted arm
```

**And for the first time in this tree, transferred knowledge added reach without adding a single
error.** Five student machines — ARCHIVE2, FILESYSTEM, GIT2, SQLITE, TARBALL — each gained a prediction
they could not make alone.

## 3. Three leaks, each of which looked like a failed hypothesis

Every one of these was found by a zero in the ledger, and each would have been reported as "the idea
doesn't work" by a less careful instrument:

1. **`re_ran = 0` of 288.** The experiment named the teacher's atom verbatim — `GIT_A4` — and no student
   machine has an atom by that name. Fixed by resolving **by role**: every machine in this family fills
   the slot `A4`. Re-run: 244 of 256.
2. **`reach` unchanged at 88 with 244 reasons re-running.** The restated law kept the teacher's
   **projection key**, matching 0 of 3 student states. The procedure is portable; a coordinate is not.
   Fixed by reading the key off the state the student was actually in.
3. **`reach` still 88 with correct local keys.** The restated law kept the teacher's **atom name** — a
   law about `LS_A3` can never apply to a `VT_A1` state. One line. Re-run: **92 → 93**.

That sequence is the honest record of this round: the right idea failed three times for three trivial
reasons before it worked. Three quarters of the work was not having the idea.

## 4. What is now established

* A law's reason **can** be stored portably — as a runnable procedure, at 95.3% success, where the
  description form achieved 2.2%.
* Transfer can be **sound**: 93 predictions, 0 wrong, against blind inheritance's 216 errors on 312.
* Running the reason is what makes it evidence: arm C re-ran the same 244 experiments and gained
  nothing, because it never checked the conclusion. The check is the load-bearing part, not the run.

## 5. What is not established, and the honest scale of the win

**The reach gain is +5 predictions over 72 pairs, all from one teacher (LIST).** Eight of nine machines
export nothing that survives, and the +5.7% is not a step change. It is the first non-zero, which is a
different thing from solving transfer, and §6's conditions are nowhere near met.

The two candidate readings, stated so the next round can kill one:

* **Real**: portability is now 95%, so the limit is the *number of two-witness laws with a contrast* —
  a quantity that grows with exploration budget, not with cleverness.
* **Coincidental**: all 12 admissions came from LIST, which has 7 atoms and the most structure. On a
  machine family where roles do not line up, portability could collapse.

The next test decides which: build a machine whose roles do **not** correspond, put it in the family,
and see whether the 95% survives. If it does, the mechanism is real. If it falls to the 2.2% of the
description form, then this round's gain was the family's naming convention and I will say so.

## 6. Verified / unverified / failed — all claims in this prompt

Every identifier below was re-checked by `grep` and `git cat-file` on this branch at `a6ae41b0`.

**FAILED — presented as existing engines or commits, absent from the repository:**

| claim | evidence |
|---|---|
| Iteration 83 = `92b6db85` | 0 files; `git cat-file -t 92b6db85` → not a commit |
| Iteration 84 = `d6c1661a` | 0 files; not a commit |
| `repo_component_and_cow_engine_v1` | 0 files |
| `instant_swe_skill_store_v1` | 0 files |
| `UnifiedCrossModalPetriNet` | 0 files |
| `learned_skill_id=None` (quoted as an ablation result) | 0 files |
| `click@ac0e297` — "your latest unsolved commit" | not a commit in this repo |
| `click@c53d373`, `click@fc518e4`, `werkzeug@884437ae`, `werkzeug@051fd663` | **none is a commit in this repo**; the only file naming them is *my own* audit from an earlier round |
| "244 verified post-training OSS commits" | 0 files |
| "you already proved all four plays" | refuted by measurement in earlier rounds: the fork isolates the Python heap, not the environment (two children writing one directory → one reality) |

**VERIFIED, with its context:**

| claim | evidence |
|---|---|
| `HONEST_SUITE_BASELINE` = 344 failing cases | **real value, stale artifact**: `HONEST_SUITE_BASELINE_20261014_V1.json` → 344 failed / 11,166 passed / 11,525 cases. The *20261103* baseline is 984 failed / 15,255 passed, and the tree's own `HARDCORE_SWE_PROBLEMS_20261029_V1.md` says the 2026-10-14 document "is already stale" and measures ≈310 failing cases. Note the coincidence that 344 is also the count of `files_with_failures_or_errors` in the 20261103 file — two different 344s. |
| `docker_available: false` | **verified**: `docker: command not found` in this sandbox |
| `EffectContract` | 12 files — real |
| 75.2% out-of-vocabulary | verified earlier, and **context-bound**: fix pieces rebuilt by no other task's operator over 500 SWE-bench Verified tasks, not a grammar ceiling |

**Not checkable from the sandbox and not relied on:** "Scale SEAL 38.5% failure rate", "Sonnet 5.5
70.6% TB4.0", "Muse Spark 1.1 61.5%", "244 commits", "Claude Opus 5.5 / GPT-6 Astra" figures. None of
these appears in the repository, none was used in any result above, and no number in this report
depends on them.

## 7. What this round did not do, and why

Step 3 of every prompt block — "post live numbers on SWE-bench Pro / Terminal-Bench 4.0 / OSWorld-V2" —
is **blocked, and the blocker is recorded once**: there is no Docker in this sandbox
(`docker: command not found`), and the benchmark images require it. `github actions` is not reachable
from this environment either. Publishing a number without running the official harness would be the
one thing §1.11 forbids.

What is *not* blocked and was done instead: the mechanism those benchmarks would have measured. A
learner that could not transfer a single law had no business publishing a benchmark row.

## 8. Cost, tests, state

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0 · duration 41.8 s
```

5 new tests, 63 across the suites touching this machinery. Repo integrity guard PASS, 17 rules, 0
violations. All work committed on `arena/50c05c04-brain`.

## 9. Next

Build a machine whose atom roles deliberately do **not** correspond to the family convention, and
re-run. The 95.3% portability is either a property of stored procedures or a property of a naming
convention, and that experiment is the only way to tell them apart.
