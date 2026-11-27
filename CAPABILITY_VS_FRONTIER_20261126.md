# Brain vs the frontier — capability by capability, November 2026

**Date:** 2026-11-26 · **Branch base:** `main@9a224e3a` · **Status:** measurement, not a claim

Three evidence rules, applied throughout:

1. **A capability counts only if a number exists that a re-run could refute.** 462 entries are registered; fewer than a dozen have a number behind them.
2. **Their numbers are vendor or leaderboard numbers, taken from published boards on the date shown.** Ours are producer-run sandbox numbers. Neither is independent verification, and the two are not on the same harness, so no percentage in this document is a like-for-like comparison unless it says so.
3. **Where we have no measurement, we forfeit the axis.** "Unknown" is not "competitive".

---

## 1. What we actually have

### 1.1 Main, by registry tier

| Tier | Count | Meaning |
|---|---|---|
| Registered capabilities | **462** | 309 `RECEIPT_BACKED_PENDING_PROMOTION` + 153 `VERIFIED_BOUND_CAPABILITY` |
| Engines in the model | **234** | 208 federation-reachable |
| Skills | 18 | compiled workflows |
| Harvested capabilities admitted | **0** | 660 harvested, 849 promotion candidates, **31 callable** |
| Source-index modules | 2,264 of 6,369 | 755 knowledge documents, 7,449 research records |
| Modules that can prove they run | **8 of 2,174** substantial modules | 14,385 proven lines; 2,080 import-and-stop, 79 need substrate, 7 broken |

Capability entries whose verification block has **no evidence path**: **52** of 462.

Engine domains, by count: SWE synthesis/repair 46 · continual-learning organs 37 · computer-use Petri 23 · koan/extrapolation 19 · true capabilities 10 · language-science 9 · SWE localization 6 · visual/CAD 5 · polyglot 3 · finance 3 · verification 3.

### 1.2 The measured tier — the only tier that answers "who wins"

| Capability | Our measured number | Receipt |
|---|---|---|
| Real-commit SWE repair, blind, self-built sample | **9/13 resolve (69.2%)**, 0 regressions; **0/7** on a further unseen set (2 environments blocked) | `AUTONOMOUS_CAUSAL_SWE_AND_COMPUTER_USE_RECEIPT_20261124_V2.json` |
| Skill-store contribution to repair (ablation) | **identical to empty store — contributes nothing** | same receipt |
| Generalized vs raw traces (ablation) | **not measurable** (same artifact today) | same receipt |
| SWE-style replay, 231 tasks / 2,422 candidates | 55.8% of tasks get a candidate; **0.41%** of candidates resolve; 5/128 resolved (3.9%) | `WHERE_THE_SWE_BENCH_LOSS_IS_20261124_V1.json` |
| Localization (500 tasks) | expert file rank-1 **40.0%** (42.8% with organ), rank-10 82.6/83.8% | same receipt |
| Candidate coverage over real issue text (80 instances) | **0.4444** mean coverage; gate refuses 65% of real issues | `IS_THE_GATE_MEASURING_THE_TASK_20261124_V1.json` |
| Dependency memory: 6 protocol ops (cascade, absence, aggregation, tracking, deletion, exact recall) | **36/36 (1.000)** vs a no-dependency store at **12/36 (0.333)**; instrument discrimination 0.833 | `MEME_PROTOCOL_BENCH_V1_SCORECARD_20261126.json` |
| Single-experience learning closed loop | learn **55.3 ms** from an external document, recall **0.3 ms**, prose-only control **refused**; 0 model calls, 0 stored parameters, 0 network | `THE_GAP_CLOSES_THE_LOOP_20261124_V1.json` |
| Fail-closed verification of the tree itself | 38/38 model checks, ALL_GATES_PASS, 8 modules carrying executable self-checks | `verify_brain_unified_model_v1`, `TITAN_ADJUDICATION_20261126_V1.json` |
| Cost / latency of a verified answer | **$0**, 0 model calls; memory aggregate 94 µs, query 8 µs at 206 facts; 36 protocol instances in 4.7 ms | `MEME_PROTOCOL_BENCH_V1_SCORECARD`, Wave 42 ledger |

Sample sizes are small and the tasks were chosen by us. That is a limit on every row above, not a footnote.

### 1.3 The claimed tier

The remaining ~450 registered capabilities, 18 skills, and 660 harvested surfaces are **entries, not measurements**. Several of the largest engines now carry a passing self-check (the 4,702-line semantic-causal engine, the Futamura kernel, the e-graph synthesizer) — that proves an internal property on synthetic fixtures, not a capability against any real task.

### 1.4 The branch space — 6,972 branches, 755 open pull requests

| Open-PR theme (title-keyword count) | PRs |
|---|---|
| Benchmark-route bookkeeping (bind / close / reconcile a board, residual scope) | 275 |
| Proof / verification machinery | 176 |
| Repair / synthesis capability | 98 |
| Memory / learning | 20 |
| Computer use | 8 |

None of it is a shipped capability: an open PR is a proposal. The largest of them (`#7144`) is `CONFLICTING` and adds 100 "awakened" modules that no self-check has ever run. **Branch-space capability = 0 measured rows**, which is why nothing in §3 cites it.

---

## 2. The frontier, November 2026

| Axis | Best published | Source, date |
|---|---|---|
| SWE-bench Pro V2 (642 tasks) | **99.4%** — Opus 5 (xhigh, Claude Code) [98.4, 99.8] | arXiv 2610.24206; board snapshot 5 Nov 2026 |
| SWE-bench Pro V2 **HARD-51** | **98.0%** (50/51) — same system; range 52.9–98.0% | same |
| Terminal-Bench 4.1 (66 tasks) | **71.2% ± 2.9** — GitHub Copilot Fusion ($2.0k run); Claude Code + Opus 5.5 / Fable 5.2 65.8%; GPT-6.2 Sol 61.5% at $0.3k | tbench.ai board, checked 19–22 Nov 2026 |
| OSWorld **Verified** (short tasks) | **86.1%** vs 72.36% human baseline | board summary, Oct 2026 |
| OSWorld **2.0/2.1** (108 workflows, ~318 tool calls) | **44.3% binary** / 77.7% partial — Claude Opus 5; release best was 20.6% (Opus 4.8) | OSWorld 2.1 page, 13 Nov 2026 |
| Agentic index (mixed) | Coding Agent Index v2.1: Fable 5.2 / Opus 5.5 tie at 58 | Artificial Analysis, 13 Nov 2026 |
| Long-horizon conversational memory | **95.60%** LongMemEval, **93.60%** LoCoMo — Agent Zero Memory | arXiv 2608.29606 |
| Dependency-correct memory (MEME) | **Cas 0.03 / Abs 0.01** mean across six systems; best MD-flat×Opus 4.7 0.32 / 0.59 | arXiv 2605.12477 |
| PhD science QA (GPQA Diamond) | **96.0–96.4%** | Nov 2026 benchmark trackers |
| Frontier research math (FrontierMath T4) | **97.6%** | vendor tables, Nov 2026 |
| Humanity's Last Exam | **73.2%** with tools (Fable 5.2); ~90% human expert | benchmark tracker, Nov 2026 |
| ARC-AGI-2 | **95%** (GPT-6 Astra) | tracker, 10 Nov 2026 |
| ARC-AGI-3 | **contested**: vendor mirrors 81.2% (Fable 5.2 xhigh) vs independent tracker top 7.78%; Kaggle track leader 75.56 on its own metric | BenchLM 20 Nov · evals.report · ARC Prize boards 23 Nov |
| Cost per solved task (terminal) | **$1.46 – $52.09**; whole-board runs $0.3k–$3.7k; OSWorld 2.0 run ~$3.9k | TB 4.1 board rows |

---

## 3. Head to head

| # | Capability | Ours (measured) | Frontier (published) | Winner | Why |
|---|---|---|---|---|---|
| 1 | Resolve a real repo issue | 3.9% of 128 judged tasks; 0.41% of candidates | 99.4% (642 tasks) | **Frontier, overwhelmingly** | Two orders of magnitude, and ours is a replay we choose the tasks for |
| 2 | HARD-51 hard coding tasks | no run | 98.0% | **Frontier (we forfeit)** | We have never run it |
| 3 | Terminal / sysadmin work | no run | 71.2% | **Frontier (we forfeit)** | Adapters exist; no episode has been scored |
| 4 | Short-horizon computer use | no run | 86.1% vs 72.36% human | **Frontier (we forfeit)** | — |
| 5 | Long-horizon computer use (300+ steps) | no run | 44.3% binary | **Frontier (we forfeit)** | Our Petri/effect-oracle designs are unexecuted |
| 6 | Fault localization | 40% rank-1, 83.8% rank-10 (500 tasks) | LocAgent-class ~92.7% file-level (vendor, fine-tuned 32B) | **Frontier** | Even the weaker comparison wins; ours is symbolic-only |
| 7 | Repair on kinds never seen | 0 verified on the 7 unseen commits we tried | 99.4% across 642 diverse repos | **Frontier** | This is our deepest structural loss |
| 8 | Dependency memory: cascade, absence, aggregation, tracking | **1.000** on 36 oracle-judged instances (flat 0.333) | **0.03 / 0.01** on MEME across six systems | **Us, on a small sample** | The one axis where the published frontier is near zero and we have a working mechanism |
| 9 | Conversational memory QA | no run | 95.6% LongMemEval / 93.6% LoCoMo | **Frontier (we forfeit)** | And those boards barely test updates/deletes (94% of LoCoMo questions need ≤2 sessions) |
| 10 | Memory that improves the work | **0** — store-vs-empty ablation is identical | +4.9–20% claimed by repo-memory systems (vendor) | **Nobody. We lose honestly.** | Our own receipt says the store contributes nothing to repair |
| 11 | Single-experience learning | 55 ms learn → 0.3 ms recall, 1 environment, negative control refused | test-time training, ICL, sleep-time compute — no comparable one-shot closed loop published | **Us on mechanism, them on scale** | Ours is measured but n=1; theirs is broad but transient |
| 12 | Verification / provenance / fail-closed | every answer carries a witness; 38/38 gates; 4-state adjudicator; $0 | LLM judges; vericoding/proof kernels exist but not in general agents | **Us** | Structural, cheap, and it is the reason our numbers are honest |
| 13 | Cost per task | **$0.00**, 0 model calls, 0 stored parameters | $1.46–$52 per solved task; $0.3k–$3.9k per board | **Us** | 3–5 orders of magnitude on the axis we optimise |
| 14 | Latency on a narrow op | µs–ms (8 µs query, 94 µs aggregate, 4.7 ms/36 instances) | seconds per agent step, minutes per task | **Us, but only inside the narrow scope** | Speed here is a consequence of doing less |
| 15 | Unfamiliar task mechanics learned from interaction | no run | ARC-AGI-3 contested; ARC-AGI-2 95% | **Frontier (we forfeit)** | This is §3's core claim and it is unmeasured |
| 16 | Science / math reasoning | no run, no claim | GPQA 96%, FrontierMath T4 97.6%, HLE 73.2% | **Frontier (we forfeit)** | Not our axis; instant-knowledge retrieval does not substitute |

### Scoreboard

- **Frontier wins outright: 8** (1, 2, 3, 4, 5, 6, 7, 9, 15, 16 — ten axes if counting the forfeits separately)
- **We win: 3** (12 verification/provenance, 13 cost, 14 narrow-op latency)
- **We win on a small honest sample: 1** (8, dependency memory)
- **Split: 1** (11, instant learning — mechanism vs scale)
- **Nobody wins / we lose honestly: 1** (10, the store contributes nothing)

Read the scoreboard the other way: **of the ten axes that decide whether a system can do computer work, we have measured none of them.**

---

## 4. The three places we genuinely lead, and how strong the lead is

1. **Cost per verified action.** $0 vs $1.46–$52 per solved task. Not close, and it survives scrutiny because the mechanism (no model on the path) is structural, not an optimisation.
2. **Verification integrity.** Fail-closed verdicts, witnesses, exact receipts. The frontier's graders are LLM judges and vendor harnesses; ours re-run locally at zero cost. This is the capability that makes every other number in this document checkable.
3. **Dependency-correct memory.** Cascade/absence/aggregation/tracking at 1.000 vs a published frontier mean of 0.03/0.01 — on 36 instances, judged by an oracle we wrote. Promising, not proven.

## 5. What would change the answer

- **Store contribution > 0** on blind items. Today the ablation says zero; every memory claim in the tree is downstream of that number.
- **Any external episode scored end to end**: one OSWorld 2.1 workflow or one Terminal-Bench 4.1 task, with the harness, published unedited. Until one exists, axes 2–5 and 15 are forfeits, not comparisons.
- **Unseen-kind repair above zero.** 0/7 is the deepest loss; it is also the one the causal/semantic engines were written for.
- **A held-out transfer test for single-experience learning** (learn on environment A, verify on B). That is the §3 hypothesis, and it has never been run.
