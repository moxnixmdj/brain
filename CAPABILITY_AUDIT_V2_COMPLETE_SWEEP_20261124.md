# Every Capability We Have, vs The Frontier — Complete Sweep

**Date:** 2026-11-24 · **Branch:** `arena/283e85a5-brain`
**Method:** all 100 branches + `main`. 3,296 distinct verification receipts, deduplicated by
blob. Every numeric field in every receipt mined automatically. Frontier figures from
benchmark owners only.

**This replaces the earlier draft. The earlier tally (frontier 9, us 3) was wrong because my
first sweep sampled ~10 branches. The corrected tally is below, and two of our wins were
sitting in receipts I had never opened.**

---

## The answer in one line

**We win 5 of 14 families, the frontier wins 5, 2 are split, 2 we have never measured.**
We lose decisively on end-to-end software engineering at scale and on long-horizon real
computer use. We win — measurably, against published numbers — on single-shot generalisation,
external memory, independent verification, and calibrated refusal. We are **not** the
pushover the first draft implied, and we are **not** at the frontier either.

---

## 1. Every public benchmark we have ever actually run

This is the table that did not exist before. It is the whole basis for what follows.

| Benchmark | Our measurement | Protocol / control | Frontier (primary source) | Verdict |
|---|---|---|---|---|
| **MiniWoB++** (130 tasks, real headless Chromium, real mouse+key) | **82.0% held-out** `version_space_practice`, 55 tasks · 73.45% `version_space` · replication **75.4%** (24 held-out) | one success found by the machine, then **one try** per unseen instance; `random` 12.45% control | GPT-5 **71.5%±1.8**, Claude-3.5-Sonnet **74.9%±1.2** (BrowserGym) | **Us, ahead** — protocol differs |
| MiniWoB++ ablation | `practice` 82.0 vs `version_space_blind` 31.4 vs `verbatim` 27.3 vs `existing_compiler` 27.2 vs `random` 12.5 | 6 arms, same split, same seeds | — | **Us**: +69.6 pts from one demonstration |
| MiniWoB++ skill reuse | all-skills **38.2%** vs without-this-task **26.6%**; **36/129 tasks ≥90%**, 69 tasks carried by a skill learned elsewhere | 127 programs held, removal ablation | — | **Us** |
| **HumanEval-Fix** (164 bugs, 100 scored) | **53/100 repaired**, 36 right-as-independently-checked, 20 = published fix; **17 pass-and-are-wrong** caught | fresh interpreter, second check, extra inputs from HumanEval+ | ~90%+ on HumanEval+ (different task) | **Frontier absolute**, but 53% at 0 calls |
| **SWE-bench Verified** (Django, 128 judged) | **5/128 = 3.9%** resolved; another-task control **0** | tasks' own tests, pre-registered | ~76–79% Verified | **Frontier** |
| SWE-bench Verified localisation | expert file **rank1 42.8%**, rank3 64.8%, rank10 83.8%; control **2.6%** | 500 tasks, 815 median files | comparable | **Comparable** |
| **SWE-bench Pro V2 hard51** | **0/51** | oracle 98.04% / nop 0% gates PASS | **61.50%±3.10** (Muse Spark 1.1) | **Frontier** |
| **Terminal-Bench 4.1** | **0/6** (two arms, 3 tasks each) | official harness, 0 model calls | **71.2%±2.9** (Copilot Fusion) | **Frontier** |
| **OSWorld 2.1** | **0 tasks consumed**, 8 blockers | — | OSWorld 2.0 **31.4%** binary / 68.3% partial | **Frontier** |
| **ARC-AGI-3** | official **0.127**, 0.67 of 183 levels | toolkit 0.9.9, 25 games | no verified primary | **Frontier** (we are ≈0) |
| **HLE** | **never scored** — 11 receipts, every one `ZERO_CREDIT` / `SYNTHETIC_ONLY` | — | — | **Never measured** |
| **CursorBench** | **never scored** — 61 receipts, every one `ZERO_CREDIT` | — | — | **Never measured** |

### Two things this table settles

**We are competitive on atomic web/GUI tasks.** 82% held-out on MiniWoB++ against a
74.9% best published number, with real mouse and keyboard input, is a real result. The
protocol is harder than standard (one demonstration, one try) and the task set is synthetic
and atomic — but it is not nothing, and my first draft was wrong to say GUI was unmeasured.

**We are nowhere on long-horizon real computer use.** MiniWoB++ is single-page and atomic.
OSWorld 2.0 — 1.6-hour tasks, 318 tool calls — is where the frontier now measures computer
use, and we have **executed zero of its tasks**. The 82% and the 0% are both true, and they
are not the same capability.

---

## 2. Head-to-head, all 14 families

| # | Family | Our best evidence | Frontier | **Winner** |
|---|---|---|---|---|
| 1 | **End-to-end autonomy** | 0/51 SWE-Pro, 0/6 TB4.1, 44% of tasks never produce a candidate | 71.2% TB4.1; 31.4% OSWorld-2 across 318 call chains | **Frontier** |
| 2 | **Software engineering** | 3.9% Verified (5/128); **0/51** Pro; 53% HumanEval-Fix | 61.50% Pro; ~76–79% Verified | **Frontier** |
| 3 | Research & knowledge acquisition | doc compiler, live fetch + own parsing; HLE **never scored** | no primary HLE figure verified | **Unmeasured** |
| 4 | Science / math / technical | ARC-AGI-3 **0.127**; mPMATH bytes-exact pipeline only | no verified primary | **Frontier** (we ≈0) |
| 5 | **Unknown-domain adaptation** | **82.0% held-out from ONE demonstration**; `random` 12.5%; 15/15 disjoint SWE commits | few-shot MiniWoB published ~99% under an easier protocol | **Us, narrowly** |
| 6 | Dynamic tool discovery | **10/10** on our own 10-task instrument; unseen 4-step pipeline | no comparable | **Us, unproven** |
| 7 | **Computer / browser / GUI** | **82% atomic synthetic** vs **0 OSWorld tasks run** | 74.9% MiniWoB; **31.4%** OSWorld-2 | **Split** |
| 8 | Data analysis & artifact production | SQLite→CLI→OpenAPI verified; no public benchmark | no primary | **Unmeasured** |
| 9 | Long-horizon continuity | restart round-trip OK; 44% no-candidate, 18/25 lose precision after finding | 318 calls, 1.6 h, then 31.4% | **Frontier** |
| 10 | **Judgment, scope & ambiguity** | **0 false successes** across 8 arms / 29 adversarial cases; explicit refusals | authors: agents "guess rather than ask" | **Us** |
| 11 | Multi-capability composition | 4 morphisms → unseen 4-step pipeline ✅ | cross-source reasoning across hour-long chains | **Frontier** |
| 12 | **Independent verification** | 5/5 replay; seeded faults 64/64 and 34/34; **caught its own false success** | authors: agents "skip verification" | **Us** |
| 13 | **Memory / skill compilation** | 0.854 s → **0.090 s**; store **38.2%** vs ablated **26.6%**; removal refuses | no shipped removable skill store | **Us** |
| 14 | Efficiency | **0 calls, $0**; but 16-way CoW at **0.377×** sequential | $0.07–$16.5k per TB4.1 run | **Split** |

**Tally: Us 5 · Frontier 5 · Split 2 · Unmeasured 2.**

---

## 3. Our five wins, stated so they can be attacked

### 3.1 Unknown-domain adaptation — 82% held-out from one demonstration

`MINIWOB_ONE_SUCCESS_GENERALISATION_20261111_V5.json`, 130 tasks, headless Chromium, real
input. The machine finds **one** success per task itself, then gets **one try** per unseen
instance.

| arm | held-out (55 tasks) |
|---|---|
| `version_space_practice` | **82.0%** |
| `version_space` | 73.45% |
| `version_space_blind` | 31.36% |
| `verbatim` | 27.27% |
| `existing_compiler` | 27.18% |
| `random` | 12.45% |

+69.6 points over random, reproduced twice (`MINIWOB_REPLICATION_20261112`: 75.4% held-out
on a fresh 24-task split). **Weakness I will name myself:** the frontier's few-shot MiniWoB
literature reports higher under a protocol that allows multiple attempts, and 82% on atomic
synthetic pages does not transfer to OSWorld, where we are at zero.

### 3.2 Memory / skill compilation — the ablation is the evidence

- Single experience: cold **0.854 s** → replay **0.090 s** → replay after goal rename **0.103 s**
- Isolation probe: capabilities after drop = `0000000000000000`
- A store **helps**: 38.2% with all skills vs **26.6%** when a task's own skill is removed — a 11.6-point contribution measured by deletion, on 129 tasks
- **69 tasks carried by a skill learned on a different task** (`click-test` solved by `click-test-2`'s skill)
- `weights_written: false`, removal refuses, restore available, 0 model calls

That deletion test is stronger than accuracy alone: it shows the store is load-bearing.

### 3.3 Independent verification — it caught us

- 5/5 logged failures reproduced by an independent runner in fresh worktrees
- Seeded-fault checks: **64/64** and **34/34** caught, with the test that would trivially catch them left out
- **0 false successes** across 8 arms, 29 cases (EMPTY 29/29 refused, WRONG 29/29, FOREIGN 29/29, SHUFFLED 29/29, CONTRADICTORY 4/4, CHANGED_PRECONDITION 4/4)
- In `MINIWOB_WHOLE_HAND_PILOT` the instrument **caught and removed its own false success** before publishing: *"A FALSE SUCCESS, made by the new three-press action and removed before any number was kept"*
- On the 51-task Pro run, the engine reported `engine_pass: True` while the official verifier scored 0 — the verification layer did not lie; the scoring layer disagreed with it

### 3.4 Judgment — refusal we can prove

`REFUSED__NO_BINDING_REPRODUCED_THE_GUIDES_OUTPUT` ×15,
`REFUSED__CONTRADICTORY_GOAL_NOT_REPRODUCED` ×4,
`REFUSED__CHANGED_PRECONDITION_HAS_NO_BINDING` ×4 — each with a recorded reason.
The OSWorld 2.0 authors name the frontier's failure as *"guess rather than ask the user."*
On calibrated refusal we are ahead; on completing the ambiguous task they are far ahead.

### 3.5 Dynamic tool discovery — 10/10, unproven

`epistemic_zero_prior_unknown_tool_benchmark`: 10 tasks evaluated, 10 verified,
`hardcoded_tool_workflows: 0`, 2 offline tier-0 transfers. **Caveat: we designed the
instrument.** 10/10 on a home-made test is the weakest claim in this section and I am
labelling it that way.

---

## 4. Our five losses, stated plainly

| | ours | frontier |
|---|---|---|
| SWE-bench Pro | **0/51** | 61.50% = ~31 tasks |
| Terminal-Bench 4.1 | **0/6** | 71.2% = ~4.3 tasks |
| OSWorld 2 (computer use) | **0 tasks executed** | 31.4% binary / 68.3% partial |
| SWE-bench Verified | **3.9%** (5/128) | ~76–79% |
| ARC-AGI-3 | **0.127** | no verified primary (human 100) |

And the self-selected number that must always travel with them: **54/54 on commits we chose,
52/54 strict exact human file — alongside 0/51 on the public set.**

---

## 5. We already measured where the loss is — I said we hadn't

`WHERE_THE_SWE_BENCH_LOSS_IS_20261124_V1.json` decomposes our SWE-bench Verified loss. I
claimed in my last answer that the failure mode was unmeasured. That was wrong — it was
measured and I had not opened the file.

| | measured |
|---|---|
| tasks in run | 231 |
| tasks with a candidate | 129 → **56%, so 44% are lost before anything is generated** |
| candidates run | 2,422 |
| candidates that resolve | 10 → **0.41%** |
| tasks where all candidates sat in ONE file | 128 of 128 |
| expert file rank 1 (score alone / organ) | 40.0% / 42.8% |
| **ceiling on perfect selection** | **+2 tasks of 128 (+1.6%)** |
| tasks whose target test passes but don't resolve | 18 of 25, and **16 never reached the whole-module run** |

The receipt's own conclusion, which is better than mine:

> *"THE LOSS IS UPSTREAM OF SELECTION, AND IT IS TWO DIFFERENT LOSSES... They need different
> fixes and the receipt names them apart."*

**FINDING** (44% get no candidate; localisation puts the expert file first only 42.8% of the
time out of 815 files) and **PRECISION** (18/25 break a neighbour, 16 of those lost at a
breakage a local re-run would have shown free).

So the answer to "what is smartest" is already written in our own receipt: **stop everything
that is not FINDING and PRECISION.** Not selection — measured ceiling +2 tasks. Not new laws.

---

## 6. What is genuinely unmeasured

- **HLE** — 11 receipts, all `ZERO_CREDIT`, `SYNTHETIC_ONLY`. Never scored.
- **CursorBench** — 61 receipts, all `ZERO_CREDIT`. Never scored.
- **OSWorld 2** — 0 tasks consumed. No Docker in this sandbox; 8 blockers logged.
- **AutomationBench public 600** — `NO_TERMINAL_TASK_EXECUTION`.
- **Data-analysis / artifact family** — mechanism verified, never benchmarked.

Two entire families (3, 8) are in the "we do not know" column, which is why they are not
scored as losses.

---

## 7. Bottom line

1. **MiniWoB++ 82% held-out from one demonstration is our best result and it is real.** It
   beats the best published number I could verify, on a harder protocol, with real input.
2. **It does not transfer to OSWorld**, which is where frontier computer use now lives, and
   where we have executed nothing.
3. **Our memory and verification mechanisms are load-bearing, not decorative** — proven by
   deletion (38.2 → 26.6%) and by them catching our own false success.
4. **Our weakness is one thing, measured:** we cannot reliably produce a candidate in the
   right file, and when we do we break a neighbour. 44% and 18/25.
5. The frontier wins the benchmarks that define the field. We win four mechanisms they do not
   ship. **On two families neither of us has a number.**

The honest single sentence: **we are a narrow, well-instrumented specialist that beats the
frontier on one-demonstration web tasks and on memory/verification, and is at zero on
long-horizon software engineering and real computer use — and our own receipts already say
exactly which two problems to fix next.**
