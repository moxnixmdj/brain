# Our Capabilities vs The Frontier — Complete Inventory and Head-to-Head

**Date:** 2026-11-24 · **Branch:** `arena/283e85a5-brain` (base `316caa3e`)
**Method:** every `arena/*` branch audited, not just this one. 97 branches, 3,274 distinct
verification receipts, 2,820 distinct runtime modules read at the JSON/receipt level.
Frontier figures taken **only** from the benchmark owners' own leaderboards.

---

## 0. The one-sentence answer

**The frontier wins 9 of 14 capability families outright. We win 2 on narrow but genuinely
measured properties (external-store skill reuse; verification independence). 3 are unsettled
because we have no comparable score at all.** Our most advanced code is not on `main`, and
where we and the frontier both ran the *same public benchmark*, we score **0** and they score
**31–43 out of 51**.

---

## 1. What we actually have (complete inventory)

### 1.1 The inventory is bigger than `main`

| | On `main` | Union of all 97 branches |
|---|---|---|
| Runtime modules | 2,446 | **2,820** (+374) |
| Verification receipts | 3,162 | **3,274** (+112) |

**Our strongest engines do not exist on `main` at all:**

| Engine | Where it lives | On `main`? |
|---|---|---|
| `causal_angelic_swe_engine_v1.py` | `b81b2217-brain` | ❌ |
| `multilang_causal_swe_engine_v1.py` | `b81b2217-brain` | ❌ |
| `universal_epistemic_kernel_v1.py` | `b81b2217-brain` | ❌ |
| `backward_witness_synthesizer_v1.py` | `b81b2217-brain` | ❌ |
| `epistemic_issue_reproducer_v1.py` | `b81b2217-brain` | ❌ |

So "what we can do" must be read off the branches, not off `main`.

### 1.2 A warning about counting modules

`cdfc4713-brain` carries **203 modules absent from `main`** — the largest single block.
Its receipts say what they are worth:

> `INDEPENDENT_PASS__...__NO_TERMINAL_TASK_EXECUTION`
> `PASS__...__LOCAL_FIT_AND_CHARTOGRAPHY_PERFORMANCE_UNPROVED__ZERO_CREDIT`

**203 modules, zero credit.** Module count is not capability. I have not counted it as capability.

### 1.3 The branch-by-branch clusters that matter

| Branch | What it holds | Executed evidence? |
|---|---|---|
| `b81b2217` | SWE-Pro-V2 hard51 full run + 45-commit real-history sweep + held-out transfer suites | ✅ yes, and it destroys the self-selected claim (§2) |
| `6f8ac9ce` | SWE-Pro-V2 fresh-container regrade, TB4.1 CPU + raw-instruction, OSWorld 2.1 blocker probe | ✅ yes — 0 rewards |
| `e7a4ed58` | One-experience cross-family transfer, goal-directed sufficiency gate | ✅ yes — best measured learning artifact we have |
| `9026f2bc` | Real computer learning, composed lessons, store-knows-format | ✅ yes — cold→replay 9.5× |
| `69b87879` | GUI computer-use verification (ground/act/verify) | ⚠️ on a **3-element synthetic JSON file** |
| `0e27dc1b` | Capability self-model, derivation grammar, world forge, route-reach census | ⚠️ mostly ZERO_CREDIT |
| `086851e2` | Charthography extractor, zero-model runtime census | ✅ census executed, **7 model-dependent files remain, exit 2** |
| `98e3c624` | Claim ledger, oracle licence cross-project | ✅ 0.76 sites licensed, 0.75 mutants caught |
| `c889ffa2` | Harbor container transport | ⚠️ transport only |
| `cdfc4713` | 203 modules incl. browser/ARC | ❌ NO_TERMINAL_TASK_EXECUTION |

---

## 2. The finding that decides most of this: 0/51 on the real benchmark

`b81b2217-brain` ran **the full 51-task SWE-bench Pro V2 hard set** with all three controls
in the same job configuration. This is the most rigorous thing we have ever run:

| Arm | Resolved | Rate | Status breakdown |
|---|---|---|---|
| **oracle** (gold patch) | 50/51 | **98.04%** | — |
| **nop** (no agent) | 0/51 | **0.0%** | NO_AGENT_REPORT ×51 |
| **ours (causal)** | **0/51** | **0.0%** | **NO_EDITS ×44**, EDITS_UPLOADED ×3, HARNESS_ERROR ×4 |

The oracle scores 98%. The no-op scores 0%. **The harness is valid and our engine scores
indistinguishable from doing nothing.** 44 of 51 times it did not produce an edit at all —
it never reached the point where its repair logic could matter.

Corroborating, independently, on other branches:

- `6f8ac9ce`: three SWE-bench Pro tasks, fresh container, official verifier → **0.0, 0.0, 0.0**
- `6f8ac9ce`: six Terminal-Bench 4.1 tasks → **0.0 × 6**
- `6f8ac9ce`: OSWorld 2.1 → **0 tasks consumed**, 8 blockers, 40-service compose never started
- Real-history sweep, 45 real commits, 1,649 s → **1 VERIFIED**, 29 NO_PROJECTION_REPAIRS,
  12 NO_FALSEY_GUARD, 2 NO_FAILING_TEST, 1 REFUSED (broken control)

### And the number sitting right next to it

The **same branch** also reports, on commits *we chose ourselves*:

> `combined_15repo_real_swe_verified: 54/54 runnable (100.0%), 52/54 strict exact human file`

**100% on self-selected commits. 0% on the public benchmark.** That is not a capability
curve — that is what overfitting to a chosen distribution looks like. Both numbers are true
and they are only meaningful together. I am not quoting the 54/54 without the 0/51.

---

## 3. Head-to-head, family by family

Frontier numbers are from the benchmark owners: swebench.com, scale.com, tbench.ai,
osworld-v2.xlang.ai. No third-party aggregator was used — they disagreed by 30+ points.

| # | Capability family | Us (measured) | Frontier (primary source) | **Winner** |
|---|---|---|---|---|
| 1 | **End-to-end autonomy** | 0/51 SWE-Pro; 0/6 TB4.1; 0/12 click commits | **71.2%±2.9** TB4.1 (Copilot Fusion) | **Frontier** |
| 2 | **Software engineering** | **0/51** (oracle 98.04 / nop 0 controls valid) | **61.50±3.10** SWE-Pro (Muse Spark 1.1) | **Frontier** |
| 3 | Research & knowledge acquisition | doc-compiler + live fetch/own parsing, **no scored instrument** | no verified public score | **Unsettled** |
| 4 | Science / math / technical reasoning | ARC-AGI-3 **0.127**, 0.67 of 183 levels | no primary ARC-AGI-3 figure verified | **Frontier** (we are ~0) |
| 5 | Unknown-domain adaptation | 4/29 verified, **0 false successes / 8 arms** | in-context adaptation, 31.4% OSWorld-2 | **Frontier** (breadth) |
| 6 | Dynamic tool discovery | 10/10 on **our own** 10-task instrument | no primary score | **Ours, unproven** |
| 7 | **Computer / browser / GUI** | OSWorld 2.1: **0 tasks run**; GUI "verified" on a 3-element JSON file | **31.4% binary / 68.3% partial** OSWorld 2.0 | **Frontier** |
| 8 | Data analysis & artifact production | SQLite→CLI→OpenAPI pipeline verified; no public benchmark | no verified public score | **Unsettled** |
| 9 | **Long-horizon continuity** | restart digest round-trip OK, but 86% of tasks produced no edit | 318 tool calls / 1.6 h median, then 31.4% | **Frontier** |
| 10 | Judgment, scope & ambiguity | **0 false successes**; explicit refusals; 29-case adversarial controls | authors: agents "**guess rather than ask**" | **Ours** (narrow) |
| 11 | Multi-capability composition | 4 morphisms → unseen 4-step pipeline ✅ | cross-source reasoning inside the 31.4% | **Frontier** (scale) |
| 12 | **Independent verification** | **5/5** failures reproduced by an independent runner; separate `python3 -I` verifier | authors: agents "**skip verification**" | **Ours** |
| 13 | **Memory / skill compilation** | cold **0.854 s** → replay **0.090 s** (9.5×), external store, weights_written **false**, removal refuses | no shipped external-store skill reuse | **Ours** |
| 14 | Efficiency | **0 model calls, $0** inference; 16-way CoW **0.377×** sequential | **$0.07–$16.5k** per TB4.1 run | **Split** |

**Tally: Frontier 9 · Ours 3 (one narrow, one split) · Unsettled 2.**

---

## 4. Where we genuinely win — and what it is worth

These are real, measured, and I will defend them. They are also narrow.

### 4.1 Memory / skill compilation (family 13) — a real win

`9026f2bc`, `REAL_COMPUTER_LEARNING_RECEIPT_20261124_V1`:

- Cold solve: **0.854 s** · replay from memory: **0.090 s** · replay on renamed goal: **0.103 s**
- Isolation probe: capabilities after drop = `0000000000000000`, verdict `ISOLATED`
- Store: `2` rules, external file, `weights_written: false`, removal refuses, restore available
- Runtime model calls: **0**

That is one experience → an inspectable external rule → a 9.5× speedup that survives a rename
and a restart, with a proven-empty control. **No frontier product ships this.** Their skill is
in weights and context, not in a removable store.

**Honest size:** 2 rules. 1 goal family. On toy goals (`compress → out.gz`).

### 4.2 Independent verification (family 12) — a real win

- 5/5 logged failures reproduced by an independent runner in fresh worktrees
- Independent verifier = a separate `python3 -I` doctest process, not the same code path
- **0 false successes across all 8 arms**, 29 cases in the controls
  (EMPTY 29/29 refused, WRONG_SOURCE 29/29, FOREIGN 29/29, SHUFFLED 29/29,
  EXACT_SOURCE_TRACE 29/29, CONTRADICTORY_GOAL 4/4, CHANGED_PRECONDITION 4/4)
- Oracle licence across 3 repos / 5 files: 50 sites, 38 licensed (0.76), 39/52 mutants caught (0.75)

Zero false successes under adversarial controls is the single strongest property we own.

**But it does not convert into repair:** the same engine scores 0/51. **We can prove we are
wrong. We cannot make ourselves right.**

### 4.3 Judgment & refusal (family 10) — a narrow win

The OSWorld 2.0 authors name the frontier's failure mode: agents *"guess rather than ask the
user, and skip verification."* Our system refuses and can prove the refusal was correct
(`REFUSED__NO_BINDING_REPRODUCED_THE_GUIDES_OUTPUT` ×15 etc.). On **calibrated refusal** we
beat them. On **completing an ambiguous task**, they beat us — they finish 31.4%, we finish 0.

---

## 5. Where the frontier wins — no spin

| Family | Their number | Our number | Ratio |
|---|---|---|---|
| Software engineering (SWE-Pro public) | 61.50% of 51 ≈ **31 tasks** | **0 tasks** | 0/31 |
| Terminal-Bench 4.1 | 71.2% of 6 ≈ **4.3 tasks** | **0 tasks** | 0/4.3 |
| OSWorld 2.0 (computer use) | **31.4%** binary / 68.3% partial | **0 tasks executed** | n/a |
| ARC-AGI-3 | (unverified) | **0.127** vs human 100.0 | self-admitted near-zero |

Two things I will not do: call 0/51 "early progress," or quote 54/54 without 0/51 beside it.

---

## 6. The three blockers that actually explain the gap

Not a mystery, and not a lack of modules. Three specific, checkable facts:

1. **The engine produces no edit on 44 of 51 real tasks** (`NO_EDITS`). Everything downstream
   is unreachable. This is a *localization/triggering* failure, not a *repair* failure.
2. **OSWorld was never run.** `hard_benchmark_tasks_consumed: 0`, 8 blockers, 40 services
   composed, 0 containers started. Family 7 and 9 are therefore not "weak" — they are **unmeasured**.
3. **The zero-model claim has a qualifier that is still open.** The census says
   *"7 PINNED MODEL-DEPENDENT FILES REMAIN, EXIT 2."* I checked all 7 against `main` today —
   **all 7 are still present**, including `astra_runtime.py` and four
   `harbor_science_planner_v*` modules. So "$0, zero model calls" is true for the measured
   runs and **not yet true for the repository as a whole**.

---

## 7. Bottom line

- Our **best** capability is external-store skill reuse with provable isolation — real, small.
- Our **best-verified** property is that we never claim a false success — real, and it does not
  yet make us correct.
- Our **most advanced code is on branches**, not `main`.
- On every public benchmark where we and the frontier ran the same tasks, we score **0** and
  the frontier scores **31–43 of 51**.
- Self-selected commits: 100%. Public benchmark: 0%. The distance between those two numbers
  *is* the remaining engineering problem.

The frontier wins the capability comparison. We hold two mechanisms they do not ship —
removable external memory and refusal you can audit — and neither one currently closes a
single benchmark task.
