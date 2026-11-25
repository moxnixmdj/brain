# Our most advanced capabilities against the frontier's — one verdict per capability

**2026-11-25.** Scope: all five `arena/*-brain` branches plus `main`, and this branch's
own work. Frontier numbers read 2026-11-23/25 from public leaderboards and papers; the
disagreement between aggregators is recorded rather than smoothed (see §5).

This document exists to answer one question honestly: **at each capability, who wins?**
It is not a parity claim, and it deliberately counts our failures at the same resolution
as our successes.

> **CORRECTION APPENDED 2026-11-25.** The inventory above is **incomplete** and three of
> its entries are wrong. The real census is four levels — **19 families / 12 components /
> 11 measured specs / ~10 benchmark insertions** — not the 15 rows below. In particular:
> **15 of the 19 families route through an external model**, only 4 are model-free, and
> the system's own audit says **about 2,200 runtime modules have never been read**. Two
> measured capabilities were missing from the ledger and I ran both to 500/500 today
> (`FILE_CHANGE_REQUEST_COPY_RENAME_APPEND_V1`, `FILE_QUESTION_TAUGHT_WORDS_V1`), and
> "long-horizon autonomy: no measurement" below is **false** — there is a measured
> same-identity supervisor with checkpoint continuity. Read
> `THE_CAPABILITY_CENSUS_CORRECTED_20261125_V1.md` for the correction; the verdicts that
> survive are the externally-comparable ones (3.9%, 2.7%, 6/11), and 0 of our measurable
> capabilities are referee-signed, so the creditable ceiling is zero by our own law.

---

## 0. The thing that governs every verdict below

We have **two different systems** in this repository, and the ledger has been conflating
them:

| | **A. The deterministic engine** (this branch + `1412289d` + `06dc079e`) | **B. The model-backed system** (the frontier) |
|---|---|---|
| runtime model calls | **0** | thousands per task |
| what it can do | whatever a mechanism encodes | open-ended |
| where it wins | speed, cost, reproducibility, auditability | everything requiring generalisation |
| where it loses | anything the mechanism was not written for | nothing much left |

Every "we win" below is a win for **A**, and except in three cases it is a win on a
dimension the benchmark does not score. Every "they win" is usually a win on the one
dimension that matters — can it do the task at all.

There is also a **C** that we own but that is not a capability: this repository's
audit discipline, which has repeatedly falsified its own claims. It appears in §4
because it is the most defensible thing we have, and §5 because it cuts against us.

---

## 1. Verdict table

`WIN` / `LOSE` / `NO CONTEST` (never attempted) / `UNKNOWN` (no measurement either side).

| # | Capability | Our best **verified** number | Frontier | Verdict |
|---|---|---|---|---|
| 1 | Single-line defect repair (oracle supplied) | **25/41 = 61.0%**, 6 byte-identical, 0 model calls | n/a — nobody benchmarks this | **we win on cost, 0.0 tasks of interest** |
| 2 | SWE-bench Verified, one submission | **5/128 = 3.9%** | 76.8% (bash-only) – 96% (vendor) | **lose by ~20×** |
| 3 | SWE-bench Pro | never run | 61.5% standardised; 89.9–93% vendor | **NO CONTEST** |
| 4 | Terminal-Bench | **6/11 = 54.5%**, hand-picked, 0 model calls | 73–83% on 89 tasks | **lose** (and not comparable) |
| 5 | GUI / computer use | **1/37 MiniWoB pages = 2.7%**, 1,615 s, 50,154 actions | 86.1% OSWorld-Verified; 20.6% OSWorld 2.0; 44.3% OSWorld 2.0 now | **lose by ~30×** |
| 6 | Container/GUI harness | one end-to-end run, 0.0 on 4 tasks | routine | **lose** |
| 7 | Multi-file propagation | 4 real fixes zipped, 9 hops, 0 corpus rows | 4.1 files / 107.4 lines per Pro fix, at benchmark scale | **lose** |
| 8 | Long-horizon autonomy | no measurement; 2.7% on 37 short pages | 12–17.4 h at 50%, 1–3 h at 80% | **lose, unmeasured** |
| 9 | Tool/API discovery | 2 admitted parameterised skills | routine | **lose** |
| 10 | Research, web, data analysis | **no artifact of any kind** | GAIA-class ~50–52% | **NO CONTEST** |
| 11 | Ambiguity judgment | no measurement | n/a | **UNKNOWN** |
| 12 | Independent verification of own work | **4 independent nulls, 4 falsified claims** | weak | **we win — the only comparison a human ran** |
| 13 | Cost per solved task | **$0.00** (no model calls) | $0.50–$5+ | **we win** |
| 14 | Reproducibility / auditability | bit-exact, re-runnable, receipted | no | **we win** |
| 15 | Speed on encoded tasks | 6 TB tasks, 35–195 ms each | 7–9 min per task | **we win on 6 tasks** |

Three wins that a grader would count (1, 13, 14) are all wins **on tasks we chose and
measures we defined**. Two of those (13, 14) are real advantages that no frontier system
has. The rest are losses of one to two orders of magnitude.

---

## 2. The three numbers that actually decide it

### 2.1 SWE-bench Verified: 3.9% vs 76.8%+

`1412289d`'s `WHERE_THE_SWE_BENCH_LOSS_IS_20261124_V1` is the only receipt in this
repository from a real benchmark run under the benchmark's own tests:

```
one submission resolves   5 of 128 judged tasks = 3.9%
control (other task text) 0 tasks resolved  -> the 5 are not noise
in the run                231 tasks, 129 with a candidate (55.8%)
candidates                2422, of which 10 resolve (0.41%)
```

The frontier's **bash-only** SWE-bench Verified number — the strictest, most comparable
one — is **76.8%**. Vendor-reported numbers reach 93.9–96%, but those are provider runs
and several aggregators simply repeat each other; I use 76.8% as the defensible line.

**Verdict: we lose by ~20×.** And the loss is decomposed, which is worse for us:

- **44% of tasks never get a candidate at all.** That is not a selection problem, a
  ranking problem, or a precision problem. The system does not produce a patch.
- **Perfect selection is worth +2 tasks of 128 (<2%).** So the ranker — the component
  this repository spent the most effort on — is not the bottleneck, and four separate
  ablations already said so.
- **128/128 candidates sit in one file**, matching the corpus finding exactly. We are
  solving a 107× smaller problem than Pro.

### 2.2 Computer use: 2.7% vs 86.1%

`WHERE_THE_WALL_ACTUALLY_IS_20261116_V1` is a real Chromium/Puppeteer measurement on 37
MiniWoB pages, 1,500-action budget, zero model calls:

```
reached                     1 / 37
REACHED__FIRST_SUCCESS      1  (use-slider)
SEARCH_WORLD (unexplored)  32
STATE_WORLD (page behaves
             differently)    3  (hot-cold, hover-shape, simon-says)
UNKNOWN__PAGE_OR_BRIDGE     1  (stock-market)
NO_FIRST_SUCCESS_FOUND     72  task-attempt rows
```

The dominant failure is **`SEARCH_WORLD`: 32 of 37 pages were never explored**, not
"solved wrong". We ran out of budget. Frontier OSWorld-Verified is **86.1%** (Qwen3.8-Max)
against a **72.36%** human baseline — above human. Even the *unsolved* successor benchmark,
OSWorld 2.0, has 20.6% (44.3% now) on 108 long-horizon workflows, where a human needs
~1.6 h per task.

**Verdict: we lose by ~30×**, and the failure mode is the least impressive one: our system
did not finish looking.

### 2.3 Terminal-Bench: 6/11 vs 73–83%

`06dc079e`'s `terminal_bench_zero_llm_20261124_v1` is the best thing we have — 6 tasks
passed under official pytest, **zero model calls**, 35–195 ms per task:

```
PASS hello-world                   SPECULATIVE_COW_ARTIFACT_SYNTHESIS
PASS fix-permissions               SPECULATIVE_COW_SHELL_TOMOGRAPHY
PASS countdown-game                EXACT_RATIONAL_ARITHMETIC_SEARCH
PASS sqlite-db-truncate            SQLITE_BTREE_LEAF_FORENSICS
PASS blind-maze-explorer-5x5       INTERACTIVE_MEALY_BFS_DISCOVERY
PASS blind-maze-explorer-algorithm INTERACTIVE_MEALY_BFS_SKILL_RECALL
FAIL x5                            UNSOLVED_HONEST_LIMIT  (all five log/parse tasks)
```

Frontier: **82.7%** (GPT-5.5), 73.2% (Terminus harness), 39-model average 56.4%.

**Verdict: we lose.** Our 54.5% is below the 56.4% frontier *average*. And the 11 tasks
were chosen by us, not sampled from the 89; the five that failed are all the same family
(text/log aggregation), which is exactly where a mechanism library has nothing. The
receipt labels them `UNSOLVED_HONEST_LIMIT`, which is the right behaviour and does not
change the score.

---

## 3. Where we genuinely win, stated at the same resolution

### 3.1 Cost: $0.00 vs $0.50–$5 per task — **we win**

Terminal-Bench frontier cost is **$0.76 per test**, ~242k tokens, ~7m43s. Ours is **$0.00**
and 35–195 ms. This is not a rounding difference; it is the entire thesis of the project.
It is also only true for tasks a mechanism was written for — 6 of 11.

### 3.2 Reproducibility: we win, and it is not close

Every claim we make is re-runnable: 5 zip tests in 120 s, byte-identical patches verified
by `diff` against `git show <commit>:<path>`, full suites run on parent and refined trees.
No frontier system can produce a bit-exact, model-free reproduction of a fix. This is the
capability I would defend hardest.

### 3.3 Self-falsification: we win, and a human did the comparison

Four independent engines produced four nulls on the same mechanism:

| source | measurement | result |
|---|---|---|
| `aab1b545` | surgical delete the learned law, re-run held-out task | **still solved** — the law was a recall hit |
| `1412289d` | store vs empty store, same task | **25 cand / 22.41 s vs 25 cand / 23.21 s** — slower, same outcome |
| `94363358` | ranker ceiling by construction | **+0 of 128** |
| `94363358` | originator ablation | **0/26** |

A frontier lab publishes an eval; this repository published an ablation that killed its
own favourite component **four times with four different builds**. That is the one place
where our discipline is ahead of the frontier's public practice.

### 3.4 The zip: a real, small, unreached advantage

The def-use zipper restores a property "given a move" — 4 real historical fixes, up to 9
monotone hops, baseline restored exactly, byte-identical to the human refactor in
`41597adffa`. No frontier system produces this *shape* of artifact (a minimal,
provably-correct propagation). But it has **zero corpus rows it could run on** (0/45
multi-file), so the capability is real and unmeasured at benchmark scale.

---

## 4. What we have that the frontier does not

Not benchmarks — properties. Each is verified in this repo:

1. **Zero-model-call task execution** with recorded, replayable receipts.
2. **Bit-exact patch reproduction** against the maintainer's own commit.
3. **Ablation of our own mechanisms**, published when negative (4 times).
4. **Signed honesty ledger** that has falsified 4 of its own headline numbers
   (`45/45`, `51.11%`, `84.6%`, "244 commits") where the real values are 19–25/45,
   76.9%, and unverified.
5. **Contamination flagging** (`more-itertools@c629214` excluded for having seen its diff).

The frontier's public record has none of these in this form. That is worth saying — and
it is worth exactly as much as the tasks we can complete, which is 5/128.

---

## 5. Four things I must say against my own table

1. **The frontier numbers disagree with each other by up to 19 points on the same
   benchmark.** SWE-bench Verified is reported at 76.8% (bash-only, Feb 2026),
   79.2%, 86%, 93.9%, and 96% by different aggregators; SWE-bench Pro at 61.5%
   (Scale standardised) vs 93% (vendor aggregate). I used the strictest comparable
   figure each time, which is the *most favourable* choice for me and should be read
   that way.
2. **All 25 corpus solves required an oracle the benchmark withholds**, and I selected
   all 25 by recognising their shape. That is a human routing decision, not a capability.
   Twenty-five is reachability, not generality.
3. **Our best-looking number (Terminal-Bench 54.5%) is on tasks we chose** — 11 of 89,
   and the six we pass are exactly the six our mechanism vocabulary covers.
4. **The one capability where we claim a decisive win — self-falsification — is the one
   that most looks like failure.** Four nulls is a great epistemic record and a poor
   capability record. If a frontier lab had our four nulls, it would ship nothing.

---

## 6. The answer, in one table

| question | answer |
|---|---|
| Do we beat the frontier at anything a user would ask for? | **No.** 3.9% vs 76.8% on SWE-bench Verified; 2.7% vs 86.1% on computer use. |
| Do we beat it at anything at all? | **Yes: cost ($0.00 vs ~$0.76/task), reproducibility, and honesty under ablation.** |
| Is our strongest domain closer than our weakest? | **No — our strongest (SWE, 3.9%) is 20× behind; our weakest (GUI, 2.7%) is 30× behind.** We are not "close in code and weak in GUI"; we are far behind in both. |
| What single number would change the verdict? | **Getting from 55.8% of tasks with a candidate to any candidate on 90%+**, then from 0.41% of candidates resolving to 10%. Neither is a ranking problem; both are generation problems. |
| What is the honest size of the gap? | **~20–30× on task completion, at ~1/1000th the cost.** |

The frontier wins every capability that requires meeting an unfamiliar task. We win every
capability that requires doing the same thing again, byte for byte, for free, and knowing
when we failed. Those are not the same market.
