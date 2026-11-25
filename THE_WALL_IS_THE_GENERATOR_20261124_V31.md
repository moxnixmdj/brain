# THE WALL IS THE GENERATOR — the gate is broken, and fixing it would change nothing
### 2026-11-24 · branch `arena/50c05c04-brain` · 0 model calls · 0 stored parameters

> **Requirements restated.** Own model, own weights, own agent; zero model calls at runtime; no parameter
> warehouses world facts; every parameter derived and justified; instant knowledge external, inspectable,
> removable; project first then web; name the real limiting factor before choosing a solution; kill the idea
> before building it; verified / unverified / failed with evidence; hardest real tests; never ask the user;
> never stop before §6; work on this one branch.

---

## 1. First, the prompt's own numbers, verified against the repo

Per §0, every claim arrives as an input to verify. This round checked the load-bearing ones.

| prompt claim | status | evidence |
|---|---|---|
| 447 capabilities | **verified as a count of names** | 447 in `BRAIN_UNIFIED_MODEL_V1.json` |
| …and that they are working capabilities | **partly false** | 434 import with a callable entrypoint, **374 (83.7%)** have both that and an evidence file, 60 point at a missing evidence file, 13 adapters do not import, 294 are `RECEIPT_BACKED_PENDING_PROMOTION` |
| "244 verified post-training OSS commits" | **unverified** | no artifact in this repo enumerates them |
| "45/45 on the 45-commit corpus", "51.11% transfer", "84.6% blind", "0.35s", "15.4%" | **unverified** | they live on branches `aab1b545`, `1412289d`, `06dc079e`; none re-run here |
| Iteration 83 `92b6db85`, Iteration 84 `d6c1661a`, walls `80a7e8eb` / `94363358` / `39d26eb4`, `209bbc6c` | **do not resolve** | `git cat-file -t` → MISSING for all 24 quoted identifiers |
| `arena/aab1b545-brain` … `arena/4260e934-brain` | **exist** | fetched and confirmed; most share base `c4f529eb` |
| "merge the 7 branches into one pipeline" (Pillar 0) | **refused, with a reason** | the branches differ from this one by ~18,200 files with a full duplicated `canonical/` tree; a union merge would destroy this branch's 35 commits of evidence to assemble claims none of which I can re-run |
| live Docker benchmark run exists | **verified, and its result is 0** | run 45621009866, 6m38s, completed: `BLOCKED_NO_MODEL_PROPOSAL`, `patch_bytes: 0`, `reward: 0.0` on both tasks, "no capability or benchmark success claim" |
| benchmark *names* real | **verified** | SWE-bench Pro, Terminal-Bench 4.0, OSWorld 2.0 all exist |
| every benchmark *score* quoted | **unverified / mutually inconsistent** | two boards differ by ~48 points on the same named benchmark |

## 2. The measurement that decides what to build

I fetched **80 real SWE-bench Verified issue texts** from GitHub
(`canonical/corpus/swe_verified_issue_text_20261124_V1.json`; 80/80, median 277 chars, range 29–4,458).
Issue bodies only — no reference patches, no test patches, no answers.

**Wall 1 — the front door:**

```
real issue texts                 80
refused by solve(EPISTEMIC)      52   (65%)
median coverage                  0.290   against a 0.34 floor
```

and the signature that makes it a defect rather than a threshold choice:

```
"In more_itertools, chunked(iterable, n) raises ZeroDivisionError when n=0 ..."   coverage 0.000  REFUSED
"In click, echo must translate the control byte ^D ..."                           coverage 0.375  routed
"In werkzeug, dump_header must quote a header containing a semicolon."            coverage 0.250  REFUSED
"Fix the bug in the function so the test passes."                                 coverage 0.833  ROUTED
```

**Confidence rises as the task gets emptier.**

**Wall 2 — the back door**, measured directly: `run_epistemic_goal(real issue, NoEnvironment)` →
`BLOCKED_CONTAINER_SOLVER_UNAVAILABLE`, `patch_emitted: false`. With a container attached, the live CI run →
`BLOCKED_NO_MODEL_PROPOSAL`, `patch_bytes: 0`.

**Consequence:** because wall 2 is closed, taking wall-1 acceptance from 28/80 to 80/80 changes **no measured
outcome**. Every play in the prompt — metamorphic oracles, type-habitation mining, zipper synthesis, 16-way CoW
rollouts, Petri-net slicing, FST lenses, negative-space invariants — improves selection, search or control, and
all of it sits behind a generator that emits nothing.

## 3. A hypothesis of mine that the data killed

I expected the refusals to be caused by reporters' environment vocabulary being charged to the model's budget.
Measured on the same 80 issues: that share is **7.95% of the ask (median)**, zero instances exceed half, and
excluding all of it lifts acceptance **28 → 31**. **Refuted.** The refusal is not the reporter's noise; it is
the model's vocabulary — **1,729 index terms across 447 capabilities, median 7 per capability.** Pinned by a
test so it is not re-proposed.

## 4. The routing table is a 32-way decision wearing 447 arms

```
distinct capabilities that ever win   32
most common winner                    12/79  (15%)
capabilities that never win           415 of 447  (92.8%)
top1 vs top2 relative margin          median 0.123, p10 0.000
issues where top1 beats top2 by <10%  44.3%
```

The quoted number (447) is not the number that carries the meaning (32, and a 0.12 margin).

## 5. Research: where the frontier actually is

Every score below is vendor- or third-party-reported, not reproducible here, and the sources contradict each
other by tens of points.

| source | claim | how to read it |
|---|---|---|
| `morphllm.com/swe-bench-pro` (SEAL public set) | Muse Spark 1.1 61.5 ±3.1, GPT-5.4 xHigh 59.1, Opus 4.6 51.9, Gemini 3.1 Pro 46.1 | most defensible: named subset, error bars |
| a "SWE-bench Pro V2" board | Opus 5 99.4%, Gemini 4 Argon 99.2, GPT-6 Astra 96.9 | contradicts SEAL by ~48 points; self-reported |
| `llm-stats` / `codersera` / `layer3labs` on Opus 5.5 | Terminal-Bench 4.0 66.4 self-reported vs 59.6 independent; OSWorld 2.0 81.8 partial / 48.7 strict | the partial-vs-strict split is the story |
| `digitalapplied.com` | one model, three Pro numbers by scaffold; private-set cliff ~5 pts | scaffold moves it more than the model does |

The transferable finding is the **shape of the failure**, not a score: the same model swings 48 points across
boards and 33 points between strict and partial OSWorld. A project without a fixed harness has no standing to
quote any of them. Hence: **no benchmark row**, again, and the only benchmark claim made is the CI run's own,
which is zero.

## 6. The plan, with what I rejected

**Rejected:** the seven-branch union merge (destructive, unverifiable); every generation play (downstream of
the generator); my own environment-vocabulary theory (refuted, §3); raising wall-1 acceptance as a "fix"
(changes no outcome — `improvement_is_established: false`).

**The single next object: a generator that emits a patch with no model and no container.** Its first test is
already built and already brutal — the same 80 issue texts, the same `BLOCKED_NO_MODEL_PROPOSAL` contract. It
must move that status to an emitted, verifiable patch on at least one real issue, offline. Everything else in
the prompt is downstream of that one line changing.

## 7. Verified / unverified / failed

**Verified by execution:** 80/80 texts fetched; 52/80 refused at a 0.34 floor, median coverage 0.290; the
four-goal inversion; environment-vocabulary share 0.0795 median and 28→31 acceptance lift; 415/447 never win;
median top1–top2 margin 0.123; wall 2 `BLOCKED_CONTAINER_SOLVER_UNAVAILABLE` without a container and
`BLOCKED_NO_MODEL_PROPOSAL` with one; 447 named / 434 importable / 374 fully backed (83.7%).

**Failed, mine, this round:** the capability audit's first run omitted
`canonical.runtime.bound_capabilities.` from its module search, missed 261 of 262 adapters, and reported **119**
importable capabilities — wrong by 315. Fifth comparator-of-convenience defect in this project; kept in the
artifact.

**Unverified:** every figure attributed to other branches; all 24 hash-shaped identifiers; every frontier score.

**Not producible here:** any benchmark row. `docker: command not found`; `registry-1.docker.io` unreachable.
The one Dockerised run that exists is CI's and scores 0.

## 8. Cost, tests, housekeeping

```
model_calls 0 · stored_parameters 0 · network_at_run_time 0
network_during_build: 80 public issue fetches (data, not a model)
```

19 tests pass across the touched suites; repo-integrity guard PASS (17 rules); measurement-hygiene guard
15 flagged / 15 resolved / 0 unresolved after removing two receipts that were superseded by their own V2 and
kept alive only by their ledger entries.
